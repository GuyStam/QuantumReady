from pathlib import Path
import csv
import io
import shutil

from flask import (
    Blueprint,
    Response,
    render_template,
    request,
    redirect,
    url_for
)

from app.database import get_db_connection

import prepare_inventory
import risk_engine


main = Blueprint('main', __name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "quantumready.db"


EXPECTED_HEADERS = {
    "systems": {
        "system_id",
        "system_name",
        "system_type",
        "environment",
        "criticality",
        "owner_id",
        "owner_name",
        "team",
        "email"
    },

    "crypto": {
        "asset_id",
        "system_id",
        "asset_name",
        "asset_type",
        "protocol",
        "location",
        "data_sensitivity",
        "exposure",
        "migration_status",
        "target_date",
        "algorithm_id",
        "algorithm_name",
        "algorithm_type",
        "quantum_status",
        "usage_type",
        "key_size"
    },

    "certificates": {
        "certificate_id",
        "asset_id",
        "common_name",
        "issuer",
        "serial_number",
        "valid_from",
        "expiry_date"
    }
}


def validate_csv_file(path, required_columns):
    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        columns = set(
            reader.fieldnames or []
        )

        missing = required_columns - columns

        if missing:
            raise ValueError(
                f"{path.name} is missing columns: "
                f"{', '.join(sorted(missing))}"
            )

        first_row = next(reader, None)

        if first_row is None:
            raise ValueError(
                f"{path.name} contains no data."
            )


def determine_migration_status(algorithm_rows):
    statuses = {
        str(row["quantum_status"]).strip().lower()
        for row in algorithm_rows
        if row["quantum_status"]
    }

    has_vulnerable = "vulnerable" in statuses
    has_post_quantum = "post-quantum" in statuses

    if has_vulnerable and has_post_quantum:
        return "Hybrid"

    if has_post_quantum and not has_vulnerable:
        return "Post-Quantum"

    return "Classical"


@main.route('/')
def index():
    return render_template(
        'index.html'
    )


@main.route('/user/<name>')
def user(name):
    return render_template(
        'user.html',
        name=name
    )


@main.route('/assets')
def assets():
    connection = get_db_connection()

    risk_results = risk_engine.refresh_all_risks(
        connection
    )

    explanations = {
        result["asset_id"]: result["reasons"]
        for result in risk_results
    }

    rows = connection.execute("""
        SELECT
            ca.asset_id,
            ca.asset_name,
            ca.asset_type,
            ca.protocol,
            ca.exposure,
            ca.migration_status,
            ca.target_date,
            ca.risk_score,
            ca.urgency,
            ca.recommendation,
            ca.input_method,
            s.system_name,
            o.owner_name,

            CASE
                WHEN ca.risk_score >= 70
                    THEN 'High'
                WHEN ca.risk_score >= 40
                    THEN 'Medium'
                ELSE 'Low'
            END AS risk_level,

            CASE
                WHEN ca.input_method = 'Manual Entry'
                    THEN 'User Input'

                WHEN EXISTS (
                    SELECT 1
                    FROM Certificates c
                    WHERE c.asset_id = ca.asset_id
                )
                    THEN 'IT / CMDB + Crypto Inventory + PKI'

                ELSE
                    'IT / CMDB + Crypto Inventory'
            END AS data_sources

        FROM CryptoAssets ca

        JOIN Systems s
            ON ca.system_id = s.system_id

        JOIN Owners o
            ON ca.owner_id = o.owner_id

        ORDER BY ca.risk_score DESC
    """).fetchall()

    asset_list = []

    for row in rows:
        asset = dict(row)

        asset["risk_reasons"] = explanations.get(
            asset["asset_id"],
            []
        )

        asset_list.append(asset)

    connection.close()

    return render_template(
        'assets.html',
        assets=asset_list
    )


@main.route('/dashboard')
def dashboard():
    connection = get_db_connection()

    risk_engine.refresh_all_risks(
        connection
    )

    total_assets = connection.execute("""
        SELECT COUNT(*)
        FROM CryptoAssets
    """).fetchone()[0]

    high_risk = connection.execute("""
        SELECT COUNT(*)
        FROM CryptoAssets
        WHERE risk_score >= 70
    """).fetchone()[0]

    high_urgency = connection.execute("""
        SELECT COUNT(*)
        FROM CryptoAssets
        WHERE urgency = 'High'
    """).fetchone()[0]

    classical_assets = connection.execute("""
        SELECT COUNT(*)
        FROM CryptoAssets
        WHERE migration_status = 'Classical'
    """).fetchone()[0]

    hybrid_assets = connection.execute("""
        SELECT COUNT(*)
        FROM CryptoAssets
        WHERE migration_status = 'Hybrid'
    """).fetchone()[0]

    pqc_assets = connection.execute("""
        SELECT COUNT(*)
        FROM CryptoAssets
        WHERE migration_status = 'Post-Quantum'
    """).fetchone()[0]

    average_risk = connection.execute("""
        SELECT ROUND(AVG(risk_score), 1)
        FROM CryptoAssets
    """).fetchone()[0]

    expiring_certificates = connection.execute("""
        SELECT COUNT(*)
        FROM Certificates
        WHERE date(expiry_date)
            BETWEEN date('now')
            AND date('now', '+90 day')
    """).fetchone()[0]

    priority_assets = connection.execute("""
        SELECT
            asset_id,
            asset_name,
            risk_score,
            urgency,
            migration_status,
            target_date

        FROM CryptoAssets

        ORDER BY risk_score DESC

        LIMIT 5
    """).fetchall()

    connection.close()

    return render_template(
        'dashboard.html',
        total_assets=total_assets,
        high_risk=high_risk,
        high_urgency=high_urgency,
        classical_assets=classical_assets,
        hybrid_assets=hybrid_assets,
        pqc_assets=pqc_assets,
        average_risk=average_risk,
        expiring_certificates=expiring_certificates,
        priority_assets=priority_assets
    )


@main.route('/sources')
def sources():
    return render_template(
        'sources.html'
    )


@main.route('/alerts')
def alerts():
    connection = get_db_connection()

    risk_engine.refresh_all_risks(
        connection
    )

    urgent_assets = connection.execute("""
        SELECT
            asset_id,
            asset_name,
            risk_score,
            urgency,
            migration_status,
            target_date

        FROM CryptoAssets

        WHERE urgency = 'High'

        ORDER BY risk_score DESC
    """).fetchall()

    vulnerable_assets = connection.execute("""
        SELECT DISTINCT
            ca.asset_id,
            ca.asset_name,
            ca.risk_score,
            ca.migration_status,
            ca.target_date,
            a.algorithm_name,
            a.algorithm_type

        FROM CryptoAssets ca

        JOIN AssetAlgorithms aa
            ON aa.asset_id = ca.asset_id

        JOIN Algorithms a
            ON a.algorithm_id = aa.algorithm_id

        WHERE LOWER(a.quantum_status) = 'vulnerable'

        ORDER BY
            ca.risk_score DESC,
            ca.asset_name,
            a.algorithm_name
    """).fetchall()

    expiring_certificates = connection.execute("""
        SELECT
            c.certificate_id,
            c.common_name,
            c.issuer,
            c.expiry_date,
            ca.asset_name

        FROM Certificates c

        JOIN CryptoAssets ca
            ON ca.asset_id = c.asset_id

        WHERE date(c.expiry_date)
            BETWEEN date('now')
            AND date('now', '+90 day')

        ORDER BY date(c.expiry_date)
    """).fetchall()

    connection.close()

    return render_template(
        'alerts.html',
        urgent_assets=urgent_assets,
        vulnerable_assets=vulnerable_assets,
        expiring_certificates=expiring_certificates
    )


@main.route('/export-report')
def export_report():
    connection = get_db_connection()

    risk_engine.refresh_all_risks(
        connection
    )

    rows = connection.execute("""
        SELECT
            ca.asset_id,
            ca.asset_name,
            s.system_name,
            o.owner_name,
            ca.asset_type,
            ca.protocol,

            GROUP_CONCAT(
                a.algorithm_name,
                ' + '
            ) AS algorithms,

            ca.migration_status,
            ca.target_date,
            ca.risk_score,

            CASE
                WHEN ca.risk_score >= 70
                    THEN 'High'
                WHEN ca.risk_score >= 40
                    THEN 'Medium'
                ELSE 'Low'
            END AS risk_level,

            ca.urgency,
            ca.recommendation,
            ca.input_method

        FROM CryptoAssets ca

        JOIN Systems s
            ON s.system_id = ca.system_id

        JOIN Owners o
            ON o.owner_id = ca.owner_id

        LEFT JOIN AssetAlgorithms aa
            ON aa.asset_id = ca.asset_id

        LEFT JOIN Algorithms a
            ON a.algorithm_id = aa.algorithm_id

        GROUP BY
            ca.asset_id,
            ca.asset_name,
            s.system_name,
            o.owner_name,
            ca.asset_type,
            ca.protocol,
            ca.migration_status,
            ca.target_date,
            ca.risk_score,
            ca.urgency,
            ca.recommendation,
            ca.input_method

        ORDER BY ca.risk_score DESC
    """).fetchall()

    output = io.StringIO(
        newline=""
    )

    writer = csv.writer(
        output
    )

    writer.writerow([
        "Asset ID",
        "Asset",
        "System",
        "Owner",
        "Asset Type",
        "Protocol",
        "Algorithms",
        "Migration Status",
        "Target Date",
        "Risk Score",
        "Risk Level",
        "Urgency",
        "Recommendation",
        "Input Method"
    ])

    for row in rows:
        writer.writerow([
            row["asset_id"],
            row["asset_name"],
            row["system_name"],
            row["owner_name"],
            row["asset_type"],
            row["protocol"],
            row["algorithms"],
            row["migration_status"],
            row["target_date"],
            row["risk_score"],
            row["risk_level"],
            row["urgency"],
            row["recommendation"],
            row["input_method"]
        ])

    connection.close()

    csv_content = (
        "\ufeff" +
        output.getvalue()
    )

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; "
                "filename=QuantumReady_Risk_Report.csv"
        }
    )

@main.route(
    '/edit-asset/<int:asset_id>',
    methods=['GET', 'POST']
)
def edit_asset(asset_id):

    connection = get_db_connection()

    systems = connection.execute("""
        SELECT
            system_id,
            system_name
        FROM Systems
        ORDER BY system_name
    """).fetchall()

    owners = connection.execute("""
        SELECT
            owner_id,
            owner_name
        FROM Owners
        ORDER BY owner_name
    """).fetchall()

    algorithms = connection.execute("""
        SELECT
            algorithm_id,
            algorithm_name,
            quantum_status
        FROM Algorithms
        ORDER BY algorithm_name
    """).fetchall()

    asset = connection.execute("""
        SELECT
            asset_id,
            system_id,
            owner_id,
            asset_name,
            asset_type,
            protocol,
            location,
            data_sensitivity,
            exposure,
            migration_status,
            target_date,
            input_method
        FROM CryptoAssets
        WHERE asset_id = ?
    """, (
        asset_id,
    )).fetchone()

    if asset is None:
        connection.close()
        return "Asset not found", 404

    current_algorithms = connection.execute("""
        SELECT
            aa.algorithm_id,
            aa.usage_type,
            aa.key_size,
            a.algorithm_name,
            a.quantum_status

        FROM AssetAlgorithms aa

        JOIN Algorithms a
            ON a.algorithm_id = aa.algorithm_id

        WHERE aa.asset_id = ?

        ORDER BY aa.algorithm_id
    """, (
        asset_id,
    )).fetchall()

    if request.method == 'POST':

        try:
            system_id = int(
                request.form['system_id']
            )

            owner_id = int(
                request.form['owner_id']
            )

            primary_algorithm_id = int(
                request.form['primary_algorithm_id']
            )

            secondary_value = request.form.get(
                'secondary_algorithm_id',
                ''
            ).strip()

            secondary_algorithm_id = None

            if secondary_value:
                secondary_algorithm_id = int(
                    secondary_value
                )

            if (
                secondary_algorithm_id is not None
                and secondary_algorithm_id
                == primary_algorithm_id
            ):
                raise ValueError(
                    'Primary and secondary algorithms '
                    'must be different.'
                )

            primary_algorithm = connection.execute("""
                SELECT
                    algorithm_id,
                    quantum_status
                FROM Algorithms
                WHERE algorithm_id = ?
            """, (
                primary_algorithm_id,
            )).fetchone()

            if primary_algorithm is None:
                raise ValueError(
                    'Primary algorithm was not found.'
                )

            selected_algorithms = [
                primary_algorithm
            ]

            if secondary_algorithm_id is not None:

                secondary_algorithm = connection.execute("""
                    SELECT
                        algorithm_id,
                        quantum_status
                    FROM Algorithms
                    WHERE algorithm_id = ?
                """, (
                    secondary_algorithm_id,
                )).fetchone()

                if secondary_algorithm is None:
                    raise ValueError(
                        'Secondary algorithm was not found.'
                    )

                selected_algorithms.append(
                    secondary_algorithm
                )

            migration_status = determine_migration_status(
                selected_algorithms
            )

            connection.execute("""
                UPDATE CryptoAssets

                SET
                    system_id = ?,
                    owner_id = ?,
                    asset_name = ?,
                    asset_type = ?,
                    protocol = ?,
                    location = ?,
                    data_sensitivity = ?,
                    exposure = ?,
                    migration_status = ?,
                    target_date = ?

                WHERE asset_id = ?
            """, (
                system_id,
                owner_id,
                request.form['asset_name'],
                request.form['asset_type'],
                request.form['protocol'],
                request.form['location'],
                request.form['data_sensitivity'],
                request.form['exposure'],
                migration_status,
                request.form.get(
                    'target_date',
                    ''
                ),
                asset_id
            ))

            connection.execute("""
                DELETE FROM AssetAlgorithms
                WHERE asset_id = ?
            """, (
                asset_id,
            ))

            connection.execute("""
                INSERT INTO AssetAlgorithms (
                    asset_id,
                    algorithm_id,
                    usage_type,
                    key_size
                )
                VALUES (?, ?, ?, ?)
            """, (
                asset_id,
                primary_algorithm_id,
                request.form['primary_usage_type'],
                request.form['primary_key_size']
            ))

            if secondary_algorithm_id is not None:

                connection.execute("""
                    INSERT INTO AssetAlgorithms (
                        asset_id,
                        algorithm_id,
                        usage_type,
                        key_size
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    asset_id,
                    secondary_algorithm_id,
                    request.form.get(
                        'secondary_usage_type',
                        ''
                    ),
                    request.form.get(
                        'secondary_key_size',
                        ''
                    )
                ))

            risk_engine.refresh_all_risks(
                connection
            )

            connection.close()

            return redirect(
                url_for('main.assets')
            )

        except Exception as error:

            connection.rollback()

            current_algorithms = connection.execute("""
                SELECT
                    aa.algorithm_id,
                    aa.usage_type,
                    aa.key_size,
                    a.algorithm_name,
                    a.quantum_status

                FROM AssetAlgorithms aa

                JOIN Algorithms a
                    ON a.algorithm_id = aa.algorithm_id

                WHERE aa.asset_id = ?

                ORDER BY aa.algorithm_id
            """, (
                asset_id,
            )).fetchall()

            response = render_template(
                'edit_asset.html',
                asset=asset,
                systems=systems,
                owners=owners,
                algorithms=algorithms,
                current_algorithms=current_algorithms,
                error=f'Could not update asset: {error}'
            )

            connection.close()
            return response

    connection.close()

    return render_template(
        'edit_asset.html',
        asset=asset,
        systems=systems,
        owners=owners,
        algorithms=algorithms,
        current_algorithms=current_algorithms
    )

@main.route(
    '/import',
    methods=['GET', 'POST']
)
def import_data():

    if request.method == 'POST':

        systems_file = request.files.get(
            'systems_file'
        )

        crypto_file = request.files.get(
            'crypto_file'
        )

        certificates_file = request.files.get(
            'certificates_file'
        )

        uploaded_files = [
            systems_file,
            crypto_file,
            certificates_file
        ]

        if any(
            file is None or file.filename == ''
            for file in uploaded_files
        ):
            return render_template(
                'import.html',
                error=(
                    'Please select all three CSV files.'
                )
            )

        if any(
            not file.filename.lower().endswith('.csv')
            for file in uploaded_files
        ):
            return render_template(
                'import.html',
                error='Only CSV files are allowed.'
            )

        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        staged_files = {
            "systems":
                DATA_DIR / "_systems_upload.csv",

            "crypto":
                DATA_DIR / "_crypto_upload.csv",

            "certificates":
                DATA_DIR / "_certificates_upload.csv"
        }

        try:
            systems_file.save(
                staged_files["systems"]
            )

            crypto_file.save(
                staged_files["crypto"]
            )

            certificates_file.save(
                staged_files["certificates"]
            )

            validate_csv_file(
                staged_files["systems"],
                EXPECTED_HEADERS["systems"]
            )

            validate_csv_file(
                staged_files["crypto"],
                EXPECTED_HEADERS["crypto"]
            )

            validate_csv_file(
                staged_files["certificates"],
                EXPECTED_HEADERS["certificates"]
            )

        except Exception as error:

            for path in staged_files.values():
                if path.exists():
                    path.unlink()

            return render_template(
                'import.html',
                error=f'Validation failed: {error}'
            )

        targets = {
            "systems":
                DATA_DIR / "systems_inventory.csv",

            "crypto":
                DATA_DIR / "crypto_inventory.csv",

            "certificates":
                DATA_DIR / "certificates_inventory.csv"
        }

        backups = {}

        files_to_backup = list(
            targets.values()
        ) + [DB_PATH]

        for target in files_to_backup:

            if target.exists():

                backup = target.with_name(
                    target.name + ".backup"
                )

                shutil.copy2(
                    target,
                    backup
                )

                backups[target] = backup

            else:
                backups[target] = None

        try:

            for name, staged_path in staged_files.items():

                shutil.copy2(
                    staged_path,
                    targets[name]
                )

            prepare_inventory.main()

            risk_engine.main()

        except Exception as error:

            for target, backup in backups.items():

                if backup is not None and backup.exists():

                    shutil.copy2(
                        backup,
                        target
                    )

                elif target.exists():

                    target.unlink()

            return render_template(
                'import.html',
                error=f'Import failed: {error}'
            )

        finally:

            for path in staged_files.values():

                if path.exists():
                    path.unlink()

            for backup in backups.values():

                if backup is not None and backup.exists():
                    backup.unlink()

        return render_template(
            'import.html',
            success=(
                'Data imported successfully. '
                'The database and Risk Scores were updated.'
            )
        )

    return render_template(
        'import.html'
    )


@main.route(
    '/add-asset',
    methods=['GET', 'POST']
)
def add_asset():

    connection = get_db_connection()

    systems = connection.execute("""
        SELECT
            system_id,
            system_name

        FROM Systems

        ORDER BY system_name
    """).fetchall()

    owners = connection.execute("""
        SELECT
            owner_id,
            owner_name

        FROM Owners

        ORDER BY owner_name
    """).fetchall()

    algorithms = connection.execute("""
        SELECT
            algorithm_id,
            algorithm_name,
            quantum_status

        FROM Algorithms

        ORDER BY algorithm_name
    """).fetchall()

    if request.method == 'POST':

        try:
            next_asset_id = connection.execute("""
                SELECT
                    COALESCE(MAX(asset_id), 100) + 1

                FROM CryptoAssets
            """).fetchone()[0]

            system_id = int(
                request.form['system_id']
            )

            owner_id = int(
                request.form['owner_id']
            )

            primary_algorithm_id = int(
                request.form['primary_algorithm_id']
            )

            secondary_algorithm_value = (
                request.form.get(
                    'secondary_algorithm_id',
                    ''
                ).strip()
            )

            secondary_algorithm_id = None

            if secondary_algorithm_value:
                secondary_algorithm_id = int(
                    secondary_algorithm_value
                )

            if (
                secondary_algorithm_id is not None
                and
                secondary_algorithm_id
                == primary_algorithm_id
            ):
                raise ValueError(
                    'Primary and secondary algorithms '
                    'must be different.'
                )

            primary_algorithm = connection.execute("""
                SELECT
                    algorithm_id,
                    quantum_status

                FROM Algorithms

                WHERE algorithm_id = ?
            """, (
                primary_algorithm_id,
            )).fetchone()

            if primary_algorithm is None:
                raise ValueError(
                    'Primary algorithm was not found.'
                )

            selected_algorithms = [
                primary_algorithm
            ]

            if secondary_algorithm_id is not None:

                secondary_algorithm = connection.execute("""
                    SELECT
                        algorithm_id,
                        quantum_status

                    FROM Algorithms

                    WHERE algorithm_id = ?
                """, (
                    secondary_algorithm_id,
                )).fetchone()

                if secondary_algorithm is None:
                    raise ValueError(
                        'Secondary algorithm was not found.'
                    )

                selected_algorithms.append(
                    secondary_algorithm
                )

            migration_status = determine_migration_status(
                selected_algorithms
            )

            connection.execute("""
                INSERT INTO CryptoAssets (
                    asset_id,
                    system_id,
                    owner_id,
                    asset_name,
                    asset_type,
                    protocol,
                    location,
                    data_sensitivity,
                    exposure,
                    migration_status,
                    target_date,
                    risk_score,
                    urgency,
                    recommendation,
                    input_method
                )

                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    NULL, NULL, NULL, ?
                )
            """, (
                next_asset_id,
                system_id,
                owner_id,
                request.form['asset_name'],
                request.form['asset_type'],
                request.form['protocol'],
                request.form['location'],
                request.form['data_sensitivity'],
                request.form['exposure'],
                migration_status,
                request.form.get(
                    'target_date',
                    ''
                ),
                "Manual Entry"
            ))

            connection.execute("""
                INSERT INTO AssetAlgorithms (
                    asset_id,
                    algorithm_id,
                    usage_type,
                    key_size
                )

                VALUES (?, ?, ?, ?)
            """, (
                next_asset_id,
                primary_algorithm_id,
                request.form['primary_usage_type'],
                request.form['primary_key_size']
            ))

            if secondary_algorithm_id is not None:

                connection.execute("""
                    INSERT INTO AssetAlgorithms (
                        asset_id,
                        algorithm_id,
                        usage_type,
                        key_size
                    )

                    VALUES (?, ?, ?, ?)
                """, (
                    next_asset_id,
                    secondary_algorithm_id,
                    request.form.get(
                        'secondary_usage_type',
                        ''
                    ),
                    request.form.get(
                        'secondary_key_size',
                        ''
                    )
                ))

            risk_engine.refresh_all_risks(
                connection
            )

            connection.close()

            return redirect(
                url_for('main.assets')
            )

        except Exception as error:

            connection.rollback()
            connection.close()

            return render_template(
                'add_asset.html',
                systems=systems,
                owners=owners,
                algorithms=algorithms,
                error=f'Could not add asset: {error}'
            )

    connection.close()

    return render_template(
        'add_asset.html',
        systems=systems,
        owners=owners,
        algorithms=algorithms
    )