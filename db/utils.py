import duckdb
import pandas as pd


DATA_COLUMNS = ["fund_name", "date_from", "date_to", "amount", "metadata"]


def create_db(db_path: str = "charity_reports.duckdb"):
    con = duckdb.connect(db_path)

    # Create the table if it doesn't exist
    con.execute("""
    CREATE SEQUENCE IF NOT EXISTS reports_id_seq;
    
    CREATE TABLE IF NOT EXISTS charity_reports (
        id INTEGER PRIMARY KEY DEFAULT nextval('reports_id_seq'),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        fund_name TEXT NOT NULL,
        date_from DATE NOT NULL,
        date_to DATE NOT NULL,
        amount REAL NOT NULL,
        metadata JSON DEFAULT '{}'
    );
    """)
    con.close()
    print("Database and table created successfully.")


def insert_data(con: duckdb.DuckDBPyConnection, data: pd.DataFrame):
    for col in DATA_COLUMNS:
        if col not in data.columns:
            raise ValueError(f"Data is missing required column: {col}. Required columns are: {DATA_COLUMNS}")

    data = data[DATA_COLUMNS]
    # Insert data into the table
    con.execute("INSERT INTO charity_reports (fund_name, date_from, date_to, amount, metadata) SELECT * FROM data;")


def get_monthly_report(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    query = """
    SELECT 
        fund_name, 
        date_trunc('month', date_from) AS month, 
        SUM(amount) AS total_amount
    FROM charity_reports
    GROUP BY fund_name, month
    ORDER BY month;
    """
    result = con.execute(query).fetchdf()
    return result
