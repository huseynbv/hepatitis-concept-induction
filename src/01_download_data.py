"""Step 1 - Download the Hepatitis_std database from the CTU Relational Learning Repository.

The data lives on CTU's public, read-only MariaDB server, so we only need a client
(pymysql) - no local database server. Every table is dumped to data/raw/<table>.csv
so that all later steps work offline and are reproducible.
"""
from pathlib import Path

import pandas as pd
import pymysql

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

conn = pymysql.connect(
    host="relational.fel.cvut.cz",
    port=3306,
    user="guest",
    password="ctu-relational",  # public credentials published on the repository page
    database="Hepatitis_std",
)

with conn.cursor() as cur:
    cur.execute("SHOW TABLES")
    tables = [row[0] for row in cur.fetchall()]

    # Foreign keys tell us which tables link to which -> these become object properties later.
    cur.execute(
        """SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
           FROM information_schema.KEY_COLUMN_USAGE
           WHERE TABLE_SCHEMA = 'Hepatitis_std' AND REFERENCED_TABLE_NAME IS NOT NULL"""
    )
    fks = cur.fetchall()

for t in tables:
    df = pd.read_sql(f"SELECT * FROM `{t}`", conn)
    df.to_csv(OUT / f"{t}.csv", index=False)
    print(f"{t:10s} {df.shape[0]:6d} rows  columns={list(df.columns)}")

pd.DataFrame(fks, columns=["table", "column", "ref_table", "ref_column"]).to_csv(
    OUT / "_foreign_keys.csv", index=False
)
print("\nForeign keys:")
for fk in fks:
    print(f"  {fk[0]}.{fk[1]} -> {fk[2]}.{fk[3]}")

conn.close()
