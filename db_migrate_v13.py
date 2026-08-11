"""One-time migration that adds the broad_category column to the papers table."""

from db_config import get_connection


def migrate():
    conn   = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            ALTER TABLE papers
            ADD COLUMN broad_category VARCHAR(255) DEFAULT NULL
        """)
        conn.commit()
        print("Column 'broad_category' added to papers table.")

    except Exception as e:
        if "Duplicate column" in str(e) or "1060" in str(e):
            print("Column 'broad_category' already exists, skipping migration.")
        else:
            raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    migrate()
