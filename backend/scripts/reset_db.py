from sqlalchemy import text
from app.db import engine
from app.config import SCHEMA_PATH


def reset_database():
    sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with engine.begin() as conn:
        conn.execute(text(sql))

    print("Database reset complete.")


if __name__ == "__main__":
    reset_database()