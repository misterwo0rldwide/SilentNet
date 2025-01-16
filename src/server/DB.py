#   'Silent net' project data base handling
#   
#
#   Omer Kfir (C)
import sqlite3
__author__ = "Omer Kfir"


class DB:
    def __init__(self, db_name):
        """
            Initialize connection to database

            INPUT: db_name
            OUTPUT: None

            @db_name: Name of data base
        """

        self.conn   = sqlite3.connect(db_name)  # Connection to DB 
        self.cursor = self.conn.cursor()  # DB cursor
    
    def __del__(self):
        """
            Called when object deleted, closes db

            INPUT: None
            OUTPUT: None
        """
        
        self.close_DB()

    def close_DB(self):
        self.conn.close()
    