"""Opens the MySQL connection, reading credentials from the .env file."""

import os
import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    print("Attempting DB connection...")

    conn = pymysql.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "research_papers"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor
    )

    print("DB connection created")
    return conn
