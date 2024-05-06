import os
import sqlite3
from sqlite3 import Error

class DBManager():
    def __init__(self) -> None:
        self.connection = None

    def create_connection(self, file_path):
        if self.connected():
            print(f'Attempt to create a connection when a connection is already open.')
            return None

        try:
            self.connection = sqlite3.connect(file_path)
            print("Connection to SQLite DB successful")
        except Error as e:
            print(f"The error '{e}' occurred")

        return self.connection

    def connected(self):
        try:
            self.connection.cursor()
            return True
        except Exception as e:
            return False

    def close_connection(self):
        self.connection.close()
        self.connection = None