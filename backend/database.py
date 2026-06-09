import os
import pymysql
import pymysql.cursors
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
load_dotenv(Path(__file__).with_name(".env.txt"))

# Detect which database to use:
#   - If DB_HOST / DB_USER / DB_PASS are set in .env  →  MySQL  (local / MySQL Workbench)
#   - Otherwise fall back to Replit's PostgreSQL via DATABASE_URL
DB_TYPE = "mysql" if os.getenv("DB_HOST") else "postgres"


def DB_connection():
    try:
        if DB_TYPE == "mysql":
            return pymysql.connect(
                host=os.getenv("DB_HOST", "localhost"),
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASS", ""),
                database=os.getenv("DB_NAME", "fakedb"),
                port=int(os.getenv("DB_PORT", "3306")),
                cursorclass=pymysql.cursors.DictCursor,
            )
        else:
            database_url = os.getenv("DATABASE_URL")
            if database_url:
                return psycopg2.connect(
                    database_url,
                    cursor_factory=psycopg2.extras.RealDictCursor,
                )
            return psycopg2.connect(
                host=os.getenv("PGHOST", "localhost"),
                user=os.getenv("PGUSER", "postgres"),
                password=os.getenv("PGPASSWORD", ""),
                dbname=os.getenv("PGDATABASE", "postgres"),
                port=int(os.getenv("PGPORT", "5432")),
                cursor_factory=psycopg2.extras.RealDictCursor,
            )
    except Exception as e:
        raise Exception(f"Error connecting to database ({DB_TYPE})") from e
