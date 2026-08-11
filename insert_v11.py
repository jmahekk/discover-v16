"""Loads the extracted papers into MySQL, skipping titles already in the DB."""

import os
import sys
import pandas as pd
from db_config import get_connection

FILE_PATH = "output/combined/all_papers.xlsx"


def insert_data():
    if not os.path.exists(FILE_PATH):
        print(f"ERROR: {FILE_PATH} not found. Run merge_outputs.py first.")
        sys.exit(1)

    print(f"Loading: {FILE_PATH}")
    df = pd.read_excel(FILE_PATH)
    df.columns = df.columns.str.strip()
    df = df.fillna("")
    print(f"Rows in file: {len(df)}")

    conn   = get_connection()
    cursor = conn.cursor()

    # Load existing titles so we can skip duplicates
    cursor.execute("SELECT title FROM papers")
    existing = {row[0] for row in cursor.fetchall()}
    print(f"Papers already in DB: {len(existing)}")

    inserted = 0
    skipped  = 0

    for i, row in df.iterrows():
        title = str(row.get("title", "")).strip()

        if title in existing:
            skipped += 1
            continue

        query = """
        INSERT INTO papers (
            title, authors, abstract, introduction,
            limitations, conclusion, publication,
            refs, keywords, novelty, category
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            title,
            str(row.get("authors",      "")),
            str(row.get("abstract",     "")),
            str(row.get("introduction", "")),
            str(row.get("limitations",  "")),
            str(row.get("conclusion",   "")),
            str(row.get("publication",  "")),
            str(row.get("references",   "")),
            str(row.get("keywords",     "")),
            str(row.get("novelty",      "")),
            str(row.get("category",     "")),
        )

        try:
            cursor.execute(query, values)
            existing.add(title)
            inserted += 1

            # Commit every 100 rows
            if inserted % 100 == 0:
                conn.commit()
                print(f"  {inserted} rows inserted so far...")

        except Exception as e:
            print(f"  Row {i} failed: {e}")

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\nDone.")
    print(f"  Inserted : {inserted}")
    print(f"  Skipped  : {skipped} (already in DB)")


if __name__ == "__main__":
    insert_data()
