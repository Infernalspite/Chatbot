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
#   - Otherwise fall back to PostgreSQL via DATABASE_URL
DB_TYPE = "mysql" if os.getenv("DB_HOST") else "postgres"


def _postgres_url() -> str | None:
    """
    Return a psycopg2-compatible connection string.
    Render (and Heroku) emit  postgres://…  but psycopg2 requires  postgresql://…
    """
    url = os.getenv("DATABASE_URL")
    if url and url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


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
            database_url = _postgres_url()
            if database_url:
                # Render requires SSL; sslmode=require is safe for all managed PG.
                return psycopg2.connect(
                    database_url,
                    sslmode="require",
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
        raise Exception(f"Error connecting to database ({DB_TYPE}): {e}") from e
