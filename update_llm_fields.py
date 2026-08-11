"""Updates keywords, novelty and category in MySQL for rows still empty."""

import os
import pandas as pd
from db_config import get_connection

CONF = "emnlp"  # change if needed

def main():
    path = os.path.join("output", CONF, "extracted_papers.xlsx")
    df = pd.read_excel(path).fillna("")

    conn = get_connection()
    cursor = conn.cursor()

    updated = 0
    skipped = 0

    for _, row in df.iterrows():
        title    = str(row.get("title", "")).strip()
        keywords = str(row.get("groq_keywords", "")).strip()
        novelty  = str(row.get("groq_novelty", "")).strip()
        category = str(row.get("groq_category", "")).strip()

        # Only update rows that now have LLM data
        if not keywords and not novelty and not category:
            skipped += 1
            continue

        cursor.execute("""
            UPDATE papers
            SET keywords = %s, novelty = %s, category = %s
            WHERE title = %s
              AND (keywords = '' OR keywords IS NULL)
        """, (keywords, novelty, category, title))

        if cursor.rowcount > 0:
            updated += 1

        if updated % 100 == 0 and updated > 0:
            conn.commit()
            print(f"  {updated} rows updated...")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"\nDone. Updated: {updated} | Skipped (still empty): {skipped}")

if __name__ == "__main__":
    main()