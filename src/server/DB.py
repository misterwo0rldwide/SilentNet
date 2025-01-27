#   'Silent net' project data base handling
#   
#
#   Omer Kfir (C)
import sqlite3, threading
from datetime import datetime

__author__ = "Omer Kfir"


class DBHandler():
    """
        Base class for database handling
    """
    
    def __init__(self, db_name: str, table_name: str):
        """
            Initialize database connection
        
            INPUT: db_name, table_name
            OUTPUT: None

            @db_name: Name of the database
            @table_name: Name of the primary table
        """

        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.table_name = table_name

        self._lock = threading.Lock()
    
    def close_DB(self):
        """
            Closes connection to database

            INPUT: None
            OUTPUT: None
        """
        self.cursor.close()
        self.conn.close()
    
    def delete_records_DB(self):
        """
            Deletes all records from the table

            INPUT: None
            OUTPUT: None
        """
        command = f"DELETE FROM {self.table_name}"
        self.commit(command)
    
    def commit(self, command: str, *command_args) -> None:
        """
            Commits a command to database

            INPUT: command, command_args
            OUTPUT: None
        
            @command: SQL command to execute
            @command_args: Arguments for the command
        """

        with self._lock:
            try:
                self.cursor.execute(command, command_args)
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                print(f"Commit DB exception {e}")


class UserLogsORM (DBHandler):
    """
        Singleton implementation of UserLogsORM inheriting from DBHandler
    """

    DB_NAME = "client_logs.db"
    USER_LOGS_NAME = "logs"
    
    _lock = threading.Lock()
    _instance = None
    
    def __new__(cls, db_name: str, table_name: str):
        """
            Ensure singleton instance

            INPUT: None
            OUTPUT: None
        """
        
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(UserLogsORM, cls).__new__(cls)
                cls._instance.__init__(db_name, table_name)
            return cls._instance
    
    def insert_data(self, mac: str, data_type: str, data: bytes) -> None:
        """
            Insert data to SQL table
        

            INPUT: mac, data_type, data
            OUTPUT: None

            @mac: MAC address of user's computer
            @data_type: Type of data to be inserted
            @data: Bytes of data
        """

        date = datetime.now().strftime("%H:%M:%S %Y-%m-%d")
        command = f"INSERT INTO {self.table_name} (mac, type, data, date) VALUES (?,?,?,?);"
        self.commit(command, mac, data_type, data, date)

class UserId (DBHandler):

    DB_NAME = "client_logs.db"
    USER_ID_NAME = "uid"

    _lock = threading.Lock()
    _instance = None
    
    def __new__(cls, db_name: str, table_name: str):
        """
            Ensure singleton instance

            INPUT: None
            OUTPUT: None
        """
        
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(UserLogsORM, cls).__new__(cls)
                cls._instance.__init__(db_name, table_name)
            return cls._instance
    
    def insert_data(self, mac: str, hostname : str) -> None:
        """
            Insert data to SQL table

            INPUT: mac, hostname
            OUTPUT: None

            @mac: MAC address of user's computer
            @hostname: User's computer hostname
        """

        command = f"INSERT INTO {self.table_name} (mac, hostname) VALUES (?,?);"
        self.commit(command, mac, hostname)
    
    def update_name(self, mac: str, name : str) -> None:
        """
            Manager changes a name for a client
            
            INPUT: mac, name
            OUTPUT: None
            
            @mac: MAC address of user's computer
            @name: User's new changed name
        """
        
        command = f"UPDATE {self.table_name} hostname = {name} WHERE mac = {mac};"
        self.commit(command, mac, name)