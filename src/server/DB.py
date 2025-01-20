#   'Silent net' project data base handling
#   
#
#   Omer Kfir (C)
import sqlite3, threading
from datetime import datetime
__author__ = "Omer Kfir"


class DB:
    def __init__(self, db_name : str, table_name : str):
        """
            Initialize connection to database

            INPUT: db_name
            OUTPUT: None

            @db_name: Name of data base
        """

        self.conn       = sqlite3.connect(db_name)  # Connection to DB 
        self.cursor     = self.conn.cursor()  # DB cursor
        self.table_name = table_name # Main table name
        
        self.lock = threading.Lock() # Lock for race condition
    

    def close_DB(self):
        """
            Closes connection to DB

            INPUT: None
            OUTPUT: None
        """
        
        self.cursor.close()
        self.conn.close()
    
    def commit(self, command : str, *command_args) -> None:
        """
            Commits a command to DB

            INPUT: command, *command_args
            OUTPUT: None
            
            @command -> String of the command to be executed
            @command_args -> Arguments of command
        """
        
        with self.lock:
        
            try:
                self.cursor.execute(command, (*command_args))
                self.conn.commit()
            
            except Exception as e:
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
        command = f"INSERT INTO {self.table_name} (ip, data_type, data, date) VALUES (?,?,?,?)"
        
        self.commit(command, ip, data_type, data, date)