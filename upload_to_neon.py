import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
from psycopg2.extras import execute_batch

# Load .env from the project folder
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path, override=True)

# Check the database host
print("HOST:", os.getenv("PGHOST"))
print("DATABASE:", os.getenv("PGDATABASE"))

DATABASE_URL = {
    "host": os.getenv("PGHOST"),
    "database": os.getenv("PGDATABASE"),
    "user": os.getenv("PGUSER"),
    "password": os.getenv("PGPASSWORD"),
    "port": os.getenv("PGPORT"),
    "sslmode": "require"
}

try:
    # 2. Connect to Neon
    conn = psycopg2.connect(**DATABASE_URL)
    cur = conn.cursor()

    print("Connected to Neon successfully!")

    # 3. Create schema
    cur.execute("""
        CREATE SCHEMA IF NOT EXISTS titanic_project;
    """)

    # 4. Create passengers table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS titanic_project.passengers (
            passengerid INTEGER PRIMARY KEY,
            survived INTEGER,
            pclass INTEGER,
            name TEXT NOT NULL,
            sex VARCHAR(10),
            age DOUBLE PRECISION,
            sibsp INTEGER,
            parch INTEGER,
            ticket TEXT,
            fare DOUBLE PRECISION,
            cabin TEXT,
            embarked VARCHAR(5)
        );
    """)

    conn.commit()

    # 5. Read Titanic CSV
    df = pd.read_csv("Titanic-Dataset.csv")
    df.columns = df.columns.str.lower()

    columns = [
        "passengerid", "survived", "pclass", "name",
        "sex", "age", "sibsp", "parch",
        "ticket", "fare", "cabin", "embarked"
    ]

    df = df[columns]
    df = df.astype(object).where(pd.notna(df), None)

    # 6. Insert passenger records
    insert_query = """
        INSERT INTO titanic_project.passengers (
            passengerid, survived, pclass, name,
            sex, age, sibsp, parch, ticket, fare,
            cabin, embarked
        )
        VALUES (%s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s)
        ON CONFLICT (passengerid) DO NOTHING;
    """

    records = list(df.itertuples(index=False, name=None))
    execute_batch(cur, insert_query, records, page_size=100)
    conn.commit()

    # 7. Verify records
    cur.execute("""
        SELECT COUNT(*)
        FROM titanic_project.passengers;
    """)

    total = cur.fetchone()[0]
    print("Total passengers uploaded:", total)

    cur.close()
    conn.close()

except Exception as e:
    print("Error:", e)