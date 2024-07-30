from datetime import datetime
from os import getenv

import pymysql
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Token(BaseModel):
    token: str
    account_id: str
    expires_at: datetime


class SqlClient:
    def __init__(self):  # noqa: D107
        self.db = pymysql.connect(
            host=getenv("DATABASE_HOST"),
            user=getenv("DATABASE_USER"),
            password=getenv("DATABASE_PASSWORD"),
            database=getenv("DATABASE_NAME"),
        )

    def __fetch_all(self, query: str):
        cursor = self.db.cursor(dictionary=True)
        cursor.execute(query)
        return cursor.fetchall()

    def add_user_usage(self, account_id: str, query: str, response: str, model: str, provider: str, endpoint: str):  # noqa: D102
        # Escape single quotes in query and response strings
        query = query.replace("'", "''")
        response = response.replace("'", "''")

        query = f"INSERT INTO completions (account_id, query, response, model, provider, endpoint) VALUES ('{account_id}', '{query}', '{response}', '{model}', '{provider}', '{endpoint}')"  # noqa: E501
        self.db.cursor().execute(query)
        self.db.commit()

    def get_user_usage(self, account_id: str):  # noqa: D102
        query = f"SELECT * FROM completions WHERE account_id = '{account_id}'"
        return self.__fetch_all(query)
