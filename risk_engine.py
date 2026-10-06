from pathlib import Path
from datetime import date, datetime
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "quantumready.db"


SENSITIVITY_POINTS = {
    "High": 25,
    "Medium": 10,
    "Low": 0,
}

CRITICALITY_POINTS = {
    "High": 20,
    "Medium": 10,
    "Low": 0,
}

EXPOSURE_POINTS = {
    "Internet-Facing": 15,
    "Internal": 5,
    "Isolated": 0,
}


def derive_crypto_points(statuses):
    normalized = {
        str(status).strip().lower()
        for status in statuses
        if status
    }

    has_vulnerable = "vulnerable" in normalized
    has_post_quantum = "post-quantum" in normalized

    if has_vulnerable and has_post_quantum:
        return (
            15,
            "Hybrid cryptography includes classical and post-quantum components"
        )

    if has_vulnerable:
        return (
            40,
            "Quantum-vulnerable cryptography is still in use"
        )

    if has_post_quantum:
        return (
            0,
            "Post-quantum cryptography is in use"
        )

    return (
        20,
        "Cryptographic quantum status is unknown"
    )


def risk_level_from_score(score):
    if score >= 70:
        return "High"

    if score >= 40:
        return "Medium"

    return "Low"


def escalate(level):
    if level == "Low":
        return "Medium"

    if level == "Medium":
        return "High"

    return "High"


def days_until(date_text):
    if not date_text:
        return None

    try:
        target = datetime.strptime(
            date_text,
            "%Y-%m-%d"
        ).date()

        return (target - date.today()).days

    except ValueError:
        return None


def get_assets(connection):
    return connection.execute("""
        SELECT
            ca.asset_id,
            ca.asset_name,
            ca.data_sensitivity,
            ca.exposure,
            ca.migration_status,
            s.criticality
        FROM CryptoAssets ca
        JOIN Systems s
            ON s.system_id = ca.system_id
        ORDER BY ca.asset_id
    """).fetchall()


def get_algorithm_statuses(connection, asset_id):
    rows = connection.execute("""
        SELECT
            a.quantum_status
        FROM AssetAlgorithms aa
        JOIN Algorithms a
            ON a.algorithm_id = aa.algorithm_id
        WHERE aa.asset_id = ?
    """, (asset_id,)).fetchall()

    return [row[0] for row in rows]


def get_nearest_certificate_expiry(connection, asset_id):
    row = connection.execute("""
        SELECT MIN(expiry_date)
        FROM Certificates
        WHERE asset_id = ?
    """, (asset_id,)).fetchone()

    if row and row[0]:
        return row[0]

    return None


def calculate_asset_risk(
    asset,
    algorithm_statuses,
    certificate_expiry
):
    (
        asset_id,
        asset_name,
        sensitivity,
        exposure,
        migration_status,
        criticality
    ) = asset

    crypto_points, crypto_reason = derive_crypto_points(
        algorithm_statuses
    )

    sensitivity_points = SENSITIVITY_POINTS.get(
        sensitivity,
        10
    )

    criticality_points = CRITICALITY_POINTS.get(
        criticality,
        10
    )

    exposure_points = EXPOSURE_POINTS.get(
        exposure,
        5
    )

    score = min(
        100,
        crypto_points
        + sensitivity_points
        + criticality_points
        + exposure_points
    )

    reasons = [
        f"Cryptography: {crypto_points} points - {crypto_reason}",
        f"Data sensitivity ({sensitivity}): {sensitivity_points} points",
        f"Business criticality ({criticality}): {criticality_points} points",
        f"Exposure ({exposure}): {exposure_points} points",
    ]

    risk_level = risk_level_from_score(score)

    urgency = risk_level

    if migration_status == "Classical" and score >= 60:
        urgency = escalate(urgency)

        reasons.append(
            "Urgency increased because migration status is still Classical"
        )

    expiry_days = days_until(certificate_expiry)

    if expiry_days is not None:

        if expiry_days < 0:
            urgency = "High"

            reasons.append(
                "Urgency increased because a certificate has expired"
            )

        elif expiry_days <= 90:
            urgency = escalate(urgency)

            reasons.append(
                "Urgency increased because a certificate "
                "is within the 90-day expiration window"
            )

    if migration_status == "Post-Quantum":
        recommendation = (
            "Maintain monitoring and crypto-agility. "
            "Continue validating standards, compatibility "
            "and certificate lifecycle."
        )

    elif migration_status == "Hybrid":
        recommendation = (
            "Continue the phased migration toward full PQC "
            "and validate compatibility, performance "
            "and certificate readiness."
        )

    elif score >= 70:
        recommendation = (
            "Prioritize migration to a hybrid/PQC configuration. "
            "Review the vulnerable algorithm and plan remediation first."
        )

    else:
        recommendation = (
            "Plan migration to hybrid/PQC and track remediation "
            "according to the asset's business priority."
        )

    if expiry_days is not None:

        if expiry_days < 0:
            recommendation += (
                " The certificate has expired and requires attention."
            )

        elif expiry_days <= 90:
            recommendation += (
                " A certificate is approaching expiration, "
                "so renewal should be coordinated with migration."
            )

    return {
        "asset_id": asset_id,
        "asset_name": asset_name,
        "risk_score": score,
        "risk_level": risk_level,
        "urgency": urgency,
        "recommendation": recommendation,
        "reasons": reasons,
    }


def calculate_asset_by_id(connection, asset_id):
    asset = connection.execute("""
        SELECT
            ca.asset_id,
            ca.asset_name,
            ca.data_sensitivity,
            ca.exposure,
            ca.migration_status,
            s.criticality
        FROM CryptoAssets ca
        JOIN Systems s
            ON s.system_id = ca.system_id
        WHERE ca.asset_id = ?
    """, (asset_id,)).fetchone()

    if asset is None:
        raise ValueError(
            f"Asset {asset_id} was not found."
        )

    statuses = get_algorithm_statuses(
        connection,
        asset_id
    )

    expiry = get_nearest_certificate_expiry(
        connection,
        asset_id
    )

    return calculate_asset_risk(
        asset,
        statuses,
        expiry
    )


def update_database(connection, result):
    connection.execute("""
        UPDATE CryptoAssets
        SET
            risk_score = ?,
            urgency = ?,
            recommendation = ?
        WHERE asset_id = ?
    """, (
        result["risk_score"],
        result["urgency"],
        result["recommendation"],
        result["asset_id"]
    ))


def refresh_all_risks(connection):
    results = []

    for asset in get_assets(connection):
        result = calculate_asset_by_id(
            connection,
            asset[0]
        )

        update_database(
            connection,
            result
        )

        results.append(result)

    connection.commit()

    return results


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        results = refresh_all_risks(connection)

        print("\nQuantumReady Risk Engine")
        print("=" * 60)

        for result in results:
            print(
                f"\n[{result['asset_id']}] "
                f"{result['asset_name']}"
            )

            print(
                f"Risk Score: "
                f"{result['risk_score']}/100"
            )

            print(
                f"Risk Level: "
                f"{result['risk_level']}"
            )

            print(
                f"Urgency: "
                f"{result['urgency']}"
            )

        print("\nRisk calculation completed successfully.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()