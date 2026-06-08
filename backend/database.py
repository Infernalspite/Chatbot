import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def DB_connection():
    try:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            conn = psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            conn = psycopg2.connect(
                host=os.getenv("PGHOST", "localhost"),
                user=os.getenv("PGUSER", "postgres"),
                password=os.getenv("PGPASSWORD", ""),
                dbname=os.getenv("PGDATABASE", "postgres"),
                port=int(os.getenv("PGPORT", "5432")),
                cursor_factory=psycopg2.extras.RealDictCursor,
            )
        return conn
    except psycopg2.Error as e:
        raise Exception("Error connecting to database") from e
