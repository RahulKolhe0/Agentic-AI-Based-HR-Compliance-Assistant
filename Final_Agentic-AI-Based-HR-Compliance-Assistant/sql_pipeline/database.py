import duckdb
import pandas as pd
import os

# -------------------------------
# DuckDB Connection
# -------------------------------
con = duckdb.connect()

# -------------------------------
# Data Folder Path
# -------------------------------
DATA_DIR = "./data"

SUPPORTED_FILES = (".csv", ".xlsx", ".xls")

# -------------------------------
# Global Metadata
# -------------------------------
TABLES = []
TABLE_COLUMNS = {}


# -------------------------------
# Load All Files into DuckDB
# -------------------------------
def load_datasets():
    """
    Loads all CSV + Excel files from ./data folder
    and registers them dynamically into DuckDB.
    """

    if not os.path.exists(DATA_DIR):
        raise FileNotFoundError(f"❌ Data folder not found: {DATA_DIR}")

    files = [
        f for f in os.listdir(DATA_DIR)
        if f.lower().endswith(SUPPORTED_FILES)
    ]

    if not files:
        raise FileNotFoundError("❌ No dataset files found inside ./data")

    print(f"\n✅ Found {len(files)} dataset file(s): {files}\n")

    for file in files:
        file_path = os.path.join(DATA_DIR, file)

        # Table name = filename without extension
        table_name = os.path.splitext(file)[0].lower()

        print(f"📌 Loading {file} → Table: {table_name}")

        # -------------------------------
        # Read File
        # -------------------------------
        if file.lower().endswith(".csv"):
            df = pd.read_csv(file_path)

        elif file.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)

        else:
            continue

        # Normalize columns
        df.columns = df.columns.str.lower().str.replace(" ", "_")

        # Register table
        con.register(table_name, df)

        # Save metadata
        TABLES.append(table_name)
        TABLE_COLUMNS[table_name] = df.columns.tolist()

        print(f"✅ Registered table: {table_name} ({len(df)} rows)\n")

    print("🎉 All datasets loaded successfully!\n")


# -------------------------------
# Load at Startup
# -------------------------------
load_datasets()
