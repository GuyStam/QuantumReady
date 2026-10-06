from pathlib import Path
import csv
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "quantumready.db"

FILES = {
    "systems": DATA_DIR / "systems_inventory.csv",
    "crypto": DATA_DIR / "crypto_inventory.csv",
    "certificates": DATA_DIR / "certificates_inventory.csv",
}

REQUIRED_COLUMNS = {
    "systems": {
        "system_id", "system_name", "system_type", "environment", "criticality",
        "owner_id", "owner_name", "team", "email"
    },
    "crypto": {
        "asset_id", "system_id", "asset_name", "asset_type", "protocol",
        "location", "data_sensitivity", "exposure", "migration_status",
        "target_date", "algorithm_id", "algorithm_name", "algorithm_type",
        "quantum_status", "usage_type", "key_size"
    },
    "certificates": {
        "certificate_id", "asset_id", "common_name", "issuer",
        "serial_number", "valid_from", "expiry_date"
    },
}


def read_csv(name):
    path = FILES[name]

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS[name] - columns

        if missing:
            raise ValueError(
                f"{path.name} is missing columns: "
                f"{', '.join(sorted(missing))}"
            )

        return list(reader)


def create_tables(connection):
    connection.executescript("""
    DROP TABLE IF EXISTS Certificates;
    DROP TABLE IF EXISTS AssetAlgorithms;
    DROP TABLE IF EXISTS Algorithms;
    DROP TABLE IF EXISTS CryptoAssets;
    DROP TABLE IF EXISTS Owners;
    DROP TABLE IF EXISTS Systems;

    CREATE TABLE Systems (
        system_id INTEGER PRIMARY KEY,
        system_name TEXT NOT NULL,
        system_type TEXT,
        environment TEXT,
        criticality TEXT
    );

    CREATE TABLE Owners (
        owner_id INTEGER PRIMARY KEY,
        owner_name TEXT NOT NULL,
        team TEXT,
        email TEXT
    );

    CREATE TABLE CryptoAssets (
        asset_id INTEGER PRIMARY KEY,
        system_id INTEGER NOT NULL,
        owner_id INTEGER NOT NULL,
        asset_name TEXT NOT NULL,
        asset_type TEXT,
        protocol TEXT,
        location TEXT,
        data_sensitivity TEXT,
        exposure TEXT,
        migration_status TEXT,
        target_date DATE,
        risk_score INTEGER,
        urgency TEXT,
        recommendation TEXT,
        input_method TEXT NOT NULL DEFAULT 'Organizational Import',

        FOREIGN KEY (system_id) REFERENCES Systems(system_id),
        FOREIGN KEY (owner_id) REFERENCES Owners(owner_id)
    );

    CREATE TABLE Algorithms (
        algorithm_id INTEGER PRIMARY KEY,
        algorithm_name TEXT NOT NULL,
        algorithm_type TEXT,
        quantum_status TEXT
    );

    CREATE TABLE AssetAlgorithms (
        asset_id INTEGER NOT NULL,
        algorithm_id INTEGER NOT NULL,
        usage_type TEXT,
        key_size TEXT,

        PRIMARY KEY (asset_id, algorithm_id),

        FOREIGN KEY (asset_id) REFERENCES CryptoAssets(asset_id),
        FOREIGN KEY (algorithm_id) REFERENCES Algorithms(algorithm_id)
    );

    CREATE TABLE Certificates (
        certificate_id INTEGER PRIMARY KEY,
        asset_id INTEGER NOT NULL,
        common_name TEXT,
        issuer TEXT,
        serial_number TEXT,
        valid_from DATE,
        expiry_date DATE,

        FOREIGN KEY (asset_id) REFERENCES CryptoAssets(asset_id)
    );
    """)


def load_data(connection):
    systems = read_csv("systems")
    crypto = read_csv("crypto")
    certificates = read_csv("certificates")

    owner_by_system = {}

    for row in systems:
        owner_id = int(row["owner_id"])
        system_id = int(row["system_id"])

        owner_by_system[system_id] = owner_id

        connection.execute("""
            INSERT OR IGNORE INTO Owners
            (owner_id, owner_name, team, email)
            VALUES (?, ?, ?, ?)
        """, (
            owner_id,
            row["owner_name"],
            row["team"],
            row["email"]
        ))

        connection.execute("""
            INSERT INTO Systems
            (system_id, system_name, system_type, environment, criticality)
            VALUES (?, ?, ?, ?, ?)
        """, (
            system_id,
            row["system_name"],
            row["system_type"],
            row["environment"],
            row["criticality"]
        ))

    inserted_assets = set()
    inserted_algorithms = set()

    for row in crypto:
        asset_id = int(row["asset_id"])
        system_id = int(row["system_id"])
        algorithm_id = int(row["algorithm_id"])

        if system_id not in owner_by_system:
            raise ValueError(
                f"Asset {asset_id} refers to unknown system_id {system_id}"
            )

        if algorithm_id not in inserted_algorithms:
            connection.execute("""
                INSERT INTO Algorithms
                (algorithm_id, algorithm_name, algorithm_type, quantum_status)
                VALUES (?, ?, ?, ?)
            """, (
                algorithm_id,
                row["algorithm_name"],
                row["algorithm_type"],
                row["quantum_status"]
            ))

            inserted_algorithms.add(algorithm_id)

        if asset_id not in inserted_assets:
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?)
            """, (
                asset_id,
                system_id,
                owner_by_system[system_id],
                row["asset_name"],
                row["asset_type"],
                row["protocol"],
                row["location"],
                row["data_sensitivity"],
                row["exposure"],
                row["migration_status"],
                row["target_date"],
                "Organizational Import"
            ))

            inserted_assets.add(asset_id)

        connection.execute("""
            INSERT INTO AssetAlgorithms
            (asset_id, algorithm_id, usage_type, key_size)
            VALUES (?, ?, ?, ?)
        """, (
            asset_id,
            algorithm_id,
            row["usage_type"],
            row["key_size"]
        ))

    for row in certificates:
        connection.execute("""
            INSERT INTO Certificates (
                certificate_id,
                asset_id,
                common_name,
                issuer,
                serial_number,
                valid_from,
                expiry_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            int(row["certificate_id"]),
            int(row["asset_id"]),
            row["common_name"],
            row["issuer"],
            row["serial_number"],
            row["valid_from"],
            row["expiry_date"]
        ))


def print_summary(connection):
    tables = [
        "Systems",
        "Owners",
        "CryptoAssets",
        "Algorithms",
        "AssetAlgorithms",
        "Certificates"
    ]

    print("\nQuantumReady inventory prepared successfully.")
    print(f"Database: {DB_PATH}\n")

    for table in tables:
        count = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(f"{table}: {count}")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        create_tables(connection)
        load_data(connection)
        connection.commit()
        print_summary(connection)

    finally:
        connection.close()


if __name__ == "__main__":
    main()