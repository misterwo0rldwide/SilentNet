#   'Silent net' project data base handling
#   
#
#   Omer Kfir (C)
import sqlite3, threading
from datetime import datetime

__author__ = "Omer Kfir"

class UserLogsORM:

    DB_NAME = "client_logs.db"
    USER_LOGS_NAME = "logs"

    _lock = threading.Lock() # Lock for race condition
    _instance = None

    def __new__(cls, db_name : str, table_name : str):
        """
            Called before __init__ to ensure db is singleton object

            INPUT: db_name
            OUTPUT: None

            @db_name -> Name of data base
            @table_name -> Name of table inside db
        """

        with cls._lock:

            # Check if initialized before in order to not create duplicates
            if cls._instance is None:
                cls._instance = super(UserLogsORM, cls).__new__(cls)
                cls._instance.__init__(db_name, table_name)
            
            return cls._instance


    def __init__(self, db_name : str, table_name : str):
        """
            Initialize connection to database

            INPUT: db_name, table_name
            OUTPUT: None

            @db_name -> Name of data base
            @table_name -> Name of table inside db
        """

        # Ensure not to get called twice after __new__
        if not hasattr(self, 'conn'):
            self.conn       = sqlite3.connect(db_name, check_same_thread=False)  # Connection to DB 
            self.cursor     = self.conn.cursor()  # DB cursor
            self.table_name = table_name # Main table name

    def close_DB(self):
        """
            Closes connection to DB

            INPUT: None
            OUTPUT: None
        """
        
        self.cursor.close()
        self.conn.close()
    
    def delete_records_DB(self):
        """
            Deletes all logs from data base

            INPUT: None
            OUTPUT: None
        """

        command = f"DELETE FROM {self.table_name}"
        self.commit(command)
    
    def commit(self, command : str, *command_args) -> None:
        """
            Commits a command to DB

            INPUT: command, *command_args
            OUTPUT: None
            
            @command -> String of the command to be executed
            @command_args -> Arguments of command
        """
        
        with self._lock:
        
            try:
                self.cursor.execute(command, command_args)
                self.conn.commit()
            
            except Exception as e:
                self.conn.rollback() # Rollback to previous state to not change DB
                print(f"Commit DB exception {e}")
    
    def insert_data(self, ip : str, data_type : str, data : bytes) -> None:
        """
            Insert data to sql table

            INPUT: ip, data_type, data
            OUTPUT: None
            
            @ip -> String of ip of a user
            @data_type -> String of type of data to be inserted
            @data -> Bytes of data
        """
        
        date = datetime.now().strftime("%H:%M:%S %Y-%m-%d")
        command = f"INSERT INTO {self.table_name} (ip, type, data, date) VALUES (?,?,?,?);"
        
        self.commit(command, ip, data_type, data, date)