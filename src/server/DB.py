#   'Silent net' project data base handling
#   
#
#   Omer Kfir (C)
import sqlite3, threading, os, sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../shared')))
from protocol import MessageParser

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
        self.db_name = db_name

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
    
    def commit(self, command: str, *command_args):
        """
            Commits a command to database

            INPUT: command, command_args
            OUTPUT: Return value of sql commit
        
            @command: SQL command to execute
            @command_args: Arguments for the command
        """
        ret_data = ""

        with self._lock:
            try:
                ret_data = self.cursor.execute(command, command_args).fetchall()
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                print(f"Commit DB exception {e}")
        
        return ret_data


class UserLogsORM (DBHandler):
    """
        Singleton implementation of UserLogsORM inheriting from DBHandler
    """

    DB_NAME = "server_db.db"
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

        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        command = f"INSERT INTO {self.table_name} (mac, type, data, date) VALUES (?,?,?,?);"
        self.commit(command, mac, data_type, data, date)
    
    # Statistics done with DB
    def get_process_count(self, mac : str) -> list[tuple[str, int]]:
        """
            Gets the amount of times each process was opened for a certain client

            INPUT: mac
            OUTPUT: List of tuples of the name of the process and amount of times was opened

            @mac: MAC address of user's computer
        """

        command = f"SELECT data, count FROM {self.table_name} WHERE type = ? AND mac = ?;"
        return self.commit(command, MessageParser.CLIENT_PROCESS_OPEN, mac)
    
    def get_inactive_times(self, mac : str) -> list[tuple[datetime, int]]:
        """
            Calculates idle times of user

            INPUT: mac
            OUTPUT: List of tuples of the datetime the user went idle and the time of idleness

            @mac: MAC address of user's computer
        """

        command = f"SELECT data, count FROM {self.table_name} WHERE type = ? AND mac = ?;"
        return self.commit(command, MessageParser.CLIENT_LAST_INPUT_EVENT, mac)
    
    def get_wpm(self, mac : str) -> int:
        """
            Calculates the average wpm the user does while excluding inactive times

            INPUT: mac, inactive
            OUTPUT: Integer

            @mac: MAC address of user's computer
        """

        # Calculate total inactive time
        total_inactive = sum(i[1] for i in self.get_inactive_times(mac))

        # Get word count
        command = f"SELECT count FROM {self.table_name} WHERE type = ? AND data LIKE '%57' AND mac = ?;"
        words_cnt = self.commit(command, MessageParser.CLIENT_INPUT_EVENT, mac)
        words_cnt = words_cnt[0][0] if words_cnt else 0  # Extract value safely

        # Get first input timestamp
        command = f"SELECT data FROM {self.table_name} WHERE type = ? AND mac = ? LIMIT 1;"
        first_input = self.commit(command, MessageParser.CLIENT_FIRST_INPUT_EVENT, mac)
        first_input = first_input[0][0] if first_input else None

        if not first_input:
            return 0  # No input data, return 0 WPM

        # Calculate active time in minutes
        active_time = ((datetime.now() - datetime.strptime(first_input, "%Y-%m-%d %H:%M:%S")).total_seconds() - total_inactive) / 60
        active_time = max(active_time, 1)  # Prevent division by zero

        return words_cnt // active_time

class UserId (DBHandler):

    DB_NAME = "server_db.db"
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
                cls._instance = super(UserId, cls).__new__(cls)
                cls._instance.__init__(db_name, table_name)
            return cls._instance
    
    def insert_data(self, mac: str, hostname : str):
        """
            Insert data to SQL table

            INPUT: mac, hostname
            OUTPUT: None

            @mac: MAC address of user's computer
            @hostname: User's computer hostname
        """

        command = f"INSERT INTO {self.table_name} (mac, hostname) VALUES (?,?);"
        self.commit(command, mac, hostname)
    
    def update_name(self, mac: str, name : str):
        """
            Manager changes a name for a client
            
            INPUT: mac, name
            OUTPUT: None
            
            @mac: MAC address of user's computer
            @name: User's new changed name
        """
        
        command = f"UPDATE {self.table_name} SET hostname = ? WHERE mac = ?;"
        self.commit(command, mac, name)
    
    def check_user_existence(self, mac : str) -> int:
        """
            Checking for a certain client to see if already connected
            
            INPUT: mac
            OUTPUT: int
            
            @mac: MAC address of user's computer
        """

        command = f"SELECT COUNT(*) FROM {self.table_name} WHERE mac = ?;"
        return self.commit(command, mac)[0][0] > 0
    
    def get_clients(self) -> list[str]:
        """
            Gets all data on clients which connect to system
            
            INPUT: None
            OUTPUT: list[str]
        """

        command = f"SELECT hostname FROM {self.table_name}"
        return [result[0] for result in self.commit(command)]
    
    def get_mac_by_hostname(self, hostname : str) -> str:
        """
            Gets the according MAC address of a computer by hostname
            
            INPUT: hostname
            OUTPUT: str
            
            @hostname: Hostname of wanted computer
        """

        command = f"SELECT mac FROM {self.table_name} WHERE hostname = ?;"
        return self.commit(command, hostname)[0][0]