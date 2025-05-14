#   'Silent net' project data base handling
#   
#
#   Omer Kfir (C)
import sqlite3, threading, os, sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../shared')))
from protocol import MessageParser
from filter import process_filter

__author__ = "Omer Kfir"

class DBHandler():
    """
        Base class for database handling
    """

    DB_NAME = "server_db.db"
    
    _lock : threading.Lock = threading.RLock()
    
    def __init__(self, conn, cursor, table_name: str):
        """
        Initialize database connection using an existing connection and cursor.

        INPUT: conn, cursor, table_name
        OUTPUT: None

        @conn: Existing SQLite connection object
        @cursor: Existing SQLite cursor object
        @table_name: Name of the primary table
        """
        self.conn = conn
        self.cursor = cursor
        self.table_name : str = table_name

        # Create tables if they do not exist
        if table_name.endswith("logs"):
            self.commit('''
            CREATE TABLE IF NOT EXISTS logs (
                uid_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                data BLOB NOT NULL,
                count NUMERIC NOT NULL DEFAULT 1,
            );
            ''')
            self.commit('CREATE INDEX IF NOT EXISTS idx_logs_uid_type ON logs(uid_id, type);')
        elif table_name.endswith("uid"):
            self.commit('''
            CREATE TABLE IF NOT EXISTS uid (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac TEXT NOT NULL UNIQUE,
                hostname TEXT NOT NULL UNIQUE
            );
            ''')
            self.commit('CREATE INDEX IF NOT EXISTS idx_uid_hostname ON uid(hostname)')

    @staticmethod
    def connect_DB(db_name : str) -> tuple:
        """
            Establish connection with DB

            INPUT: Str
            OUTPUT: tuple
        """

        conn = sqlite3.connect(db_name, check_same_thread=False)
        return conn, conn.cursor()

    @staticmethod
    def close_DB(cursor, conn):
        """
        Closes connection to database

        INPUT: cursor, conn
        OUTPUT: None
        """
        try:
            if conn:  # Check if the connection is still open
                cursor.close()
                conn.close()
        except Exception as e:
            pass

    def clean_deleted_records_DB(self):
        """
            Cleans all deleted records from the table

            INPUT: None
            OUTPUT: None
        """
        command = "VACUUM"
        self.commit(command)
    
    def delete_all_records_DB(self):
        """
            Deletes all records from the table

            INPUT: None
            OUTPUT: None
        """
        command = f"DELETE FROM {self.table_name}"
        self.commit(command)

        self.clean_deleted_records_DB()
    
    def commit(self, command: str, *command_args):
        """
            Commits a command to database

            INPUT: command, command_args
            OUTPUT: Return value of sql commit
        
            @command: SQL command to execute
            @command_args: Arguments for the command
        """
        
        ret_data = ""
        
        with DBHandler._lock:
        
            if not self.conn or not self.cursor:
                raise ValueError("Database connection not established")

            try:
                self.cursor.execute(command, command_args)
                ret_data = self.cursor.fetchall()
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                # Reset cursor
                self.cursor = self.conn.cursor()
                print(f"Commit DB exception {e}")
        
        return ret_data


class UserLogsORM (DBHandler):
    """
        Singleton implementation of UserLogsORM inheriting from DBHandler
    """

    USER_LOGS_NAME = "logs"
    
    _lock = threading.Lock()
    _instance = None
    
    def __new__(cls, conn, cursor, table_name: str):
        """
            Ensure singleton instance and initialize with existing connection and cursor.

            INPUT: cls
            OUTPUT: None
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(UserLogsORM, cls).__new__(cls)
            return cls._instance
    
    def __init__(self, conn, cursor, table_name: str):
        """
        Initialize the instance, but only once.
        """
        if not hasattr(self, 'conn') or self.conn is None:
            super().__init__(conn, cursor, table_name)
    
    def client_setup_db(self, mac : str) -> None:
        """
            Writes basic logs that need to be for every client when connected
            Writes when client first logged in (Also writes last client input event with the same time)
            Writes an empty record of inactive times
            Writes an empty record of cpu usages

            INPUT: mac
            OUTPUT: None

            @mac: MAC address of user's computer
        """

        cur_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # First log of client
        command = f"INSERT INTO {self.table_name} (mac, type, data) VALUES (?,?,?);"
        self.commit(command, mac, MessageParser.CLIENT_FIRST_INPUT_EVENT, cur_time)

        # "Last" log of client (it's not really the last time, it's just a record for next when client logs again)
        command = f"INSERT INTO {self.table_name} (mac, type, data) VALUES (?,?,?);"
        self.commit(command, mac, MessageParser.CLIENT_LAST_INPUT_EVENT, cur_time)

        # Empty record of inactive times
        command = f"INSERT INTO {self.table_name} (mac, type, data) VALUES (?,?,'');"
        self.commit(command, mac, MessageParser.CLIENT_INACTIVE_EVENT)

        # Empty record of cpu usage
        command = f"INSERT INTO {self.table_name} (mac, type, data) VALUES (?,?,'');"
        self.commit(command, mac, MessageParser.CLIENT_CPU_USAGE)

    def delete_mac_records_DB(self, mac : str):
        """
            Deletes all records from the table of a certain MAC address

            INPUT: mac
            OUTPUT: None

            @mac: MAC address of user's computer
        """
        command = f"DELETE FROM {self.table_name} WHERE mac = ?"
        self.commit(command, mac)

        self.clean_deleted_records_DB()

    def __check_inactive(self, mac : str) -> tuple[str, int]:
        """
            Checks if client is currently inactive

            INPUT: mac
            OUTPUT: Tuple conists of last datetime in string format client was active and the amount of minutes currently inactive

            @mac: MAC address of user's computer
        """

        cur_time = datetime.now()

        command = f"SELECT data FROM {self.table_name} WHERE mac = ? AND type = ?;"
        date_str = self.commit(command, mac, MessageParser.CLIENT_LAST_INPUT_EVENT)[0][0]
        
        date = datetime.strptime(date_str , "%Y-%m-%d %H:%M:%S")
        inactive_time = int((cur_time - date).total_seconds() // 60)

        # Inactive time is considered above five minutes
        if inactive_time > 5:
            return date_str, inactive_time
        
        return None, None

    def __update_last_input(self, mac : str) -> None:
        """
            Updates last time user logged input event

            INPUT: mac
            OUTPUT: None

            @mac: MAC address of user's computer
        """

        # Check if client is inactive until now, if so log it
        date, inactive_time = self.__check_inactive(mac)
        if date:

            # Get string of inactive times
            # String format -> datetime of inactive, inactive minutes
            # Example: 2025-10-10 20:20:20,10~2025-10-10 20:20:30,7~
            command = f"SELECT data FROM {self.table_name} WHERE mac = ? AND type = ?;"
            data = self.commit(command, mac, MessageParser.CLIENT_INACTIVE_EVENT)[0][0]

            data += f"{date},{inactive_time}~"
            command = f"UPDATE {self.table_name} SET data = ? WHERE mac = ? AND type = ?;"

            self.commit(command, data, mac, MessageParser.CLIENT_INACTIVE_EVENT)

        command = f"UPDATE {self.table_name} SET data = ? WHERE mac = ? AND type = ?;"

        cur_time = datetime.now()
        cur_time = cur_time.strftime("%Y-%m-%d %H:%M:%S")
        
        self.commit(command, cur_time, mac, MessageParser.CLIENT_LAST_INPUT_EVENT)

    def __get_total_active_time(self, mac : str) -> int:
        """
            Calculates total active time of user

            INPUT: mac
            OUTPUT: Integer - minutes amount of active time

            @mac: MAC address of user's computer
        """

        command = f"SELECT data FROM {self.table_name} WHERE mac = ? AND type = ?;"
        first_input = datetime.strptime(self.commit(command, mac, MessageParser.CLIENT_FIRST_INPUT_EVENT)[0][0], "%Y-%m-%d %H:%M:%S")
        last_input = datetime.strptime(self.commit(command, mac, MessageParser.CLIENT_LAST_INPUT_EVENT)[0][0], "%Y-%m-%d %H:%M:%S")

        return (last_input - first_input).total_seconds() // 60
    
    def __update_cpu_usage(self, mac: str, data : bytes) -> None:
        """
            Updates cpu usage queuery

            INPUT: mac, data
            OUTPUT: None

            @mac: MAC address of user's computer
            @data: Bytes of data
        """
        print(data)
        command = f"SELECT data FROM {self.table_name} WHERE mac = ? AND type = ?;"
        cpu_logs = self.commit(command, mac, MessageParser.CLIENT_CPU_USAGE)[0][0]
        
        if isinstance(cpu_logs, str):
            cpu_logs = cpu_logs.encode()

        cpu_logs += data + b"|"

        command = f"UPDATE {self.table_name} SET data = ? WHERE mac = ? AND type = ?;"
        self.commit(command, cpu_logs, mac, MessageParser.CLIENT_CPU_USAGE)

    def insert_data(self, mac: str, data_type: str, data: bytes) -> None:
        """
            Insert data to SQL table, if record already exists incement its counter

            INPUT: mac, data_type, data
            OUTPUT: None

            @mac: MAC address of user's computer
            @data_type: Type of data to be inserted
            @data: Bytes of data
        """

        if data_type == MessageParser.CLIENT_CPU_USAGE:
            self.__update_cpu_usage(mac, data)
            return
        
        # Ignore process which are usually not used by the user
        if data_type == MessageParser.CLIENT_PROCESS_OPEN:
            data = data.decode()
            if data in process_filter.ignored_processes:
                return

        command = f"SELECT count FROM {self.table_name} WHERE mac = ? AND type = ? AND data = ?;"
        count = self.commit(command, mac, data_type, data)

        # If got count -> count exists -> row exists
        if count:
            count = count[0][0] + 1
            command = f"UPDATE {self.table_name} SET count = ? WHERE mac = ? AND type = ? AND data = ?;"
        
            self.commit(command, count, mac, data_type, data)
        else:
            command = f"INSERT INTO {self.table_name} (mac, type, data) VALUES (?,?,?);"
        
            self.commit(command, mac, data_type, data)
        
        # Check if it is an input event
        if data_type == MessageParser.CLIENT_INPUT_EVENT:
            self.__update_last_input(mac)

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
            OUTPUT: List of Tuples of the datetime the user went idle and the time of idleness

            @mac: MAC address of user's computer
        """

        # Check if currently inactive
        date, inactive_time = self.__check_inactive(mac)

        command = f"SELECT data FROM {self.table_name} WHERE type = ? AND mac = ?;"
        dates = self.commit(command, MessageParser.CLIENT_INACTIVE_EVENT, mac)[0][0]

        if date:
            dates += f"{date},{inactive_time}"

        dates = dates.split("~")
        return [i.split(",") for i in dates], True if date else False
    
    def get_wpm(self, mac : str, inactive_times : list[tuple[datetime, int]], inactive_after_last : bool) -> int:
        """
            Calculates the average wpm the user does while excluding inactive times

            INPUT: mac, inactive
            OUTPUT: Integer

            @mac: MAC address of user's computer
            @inactive_times: Pre calculated inactive times of user
            @inactive_after_last: Boolean to indicate if inactive times include time after last logged input event
        """

        # Calculate total inactive time in minutes
        if inactive_after_last:
            inactive_times = inactive_times[:-1]
        
        total_inactive = sum(int(i[1]) for i in inactive_times if i != '' and len(i) > 1)

        # Get word count, 57 is the translation for space char in input_event in linux
        # Checks for data which has space char in it
        command = f"SELECT count FROM {self.table_name} WHERE type = ? AND data LIKE '%57%' AND mac = ?;"
        words_cnt = self.commit(command, MessageParser.CLIENT_INPUT_EVENT, mac)
        words_cnt = words_cnt[0][0] if words_cnt else 0  # Extract value safely

        # Get first input timestamp
        command = f"SELECT data FROM {self.table_name} WHERE type = ? AND mac = ?;"
        first_input = datetime.strptime(self.commit(command, MessageParser.CLIENT_FIRST_INPUT_EVENT, mac)[0][0], "%Y-%m-%d %H:%M:%S")
        last_input = datetime.strptime(self.commit(command, MessageParser.CLIENT_LAST_INPUT_EVENT, mac)[0][0], "%Y-%m-%d %H:%M:%S")

        # Calculate active time in minutes
        active_time = ((last_input - first_input).total_seconds() - total_inactive * 60) / 60
        active_time = max(active_time, 1)  # Prevent division by zero

        return words_cnt // active_time
    
    def get_cpu_usage(self, mac : str):
        """
            Gets all logs of cpu usage

            INPUT: mac
            OUTPUT: Tuple of Dictionary of cpu cores and their usages and list of times of logs

            @mac: MAC address of user's computer
        """

        command = f"SELECT data FROM {self.table_name} WHERE mac = ? AND type = ?;"
        cores_logs = self.commit(command, mac, MessageParser.CLIENT_CPU_USAGE)[0][0]
        if isinstance(cores_logs, str):
            cores_logs = cores_logs.encode()
        cores_logs = cores_logs.split(b"|")

        logs = [log for i in cores_logs if len(i) > 1 for log in i.split(MessageParser.PROTOCOL_SEPARATOR)]
        cpu_usage_logs = []
        
        core_usage = {}
        for log in logs:
            log = log.decode().split(",")
            core, usage = log[:2]

            if core not in core_usage:
                core_usage[core] = []
            core_usage[core].append(int(usage))
            
            if len(log) == 3:
                cpu_usage_logs.append(log[2])
        
        return core_usage, cpu_usage_logs

    def get_active_precentage(self, mac : str) -> int:
        """
            Calculates the percentage of time user was active

            INPUT: mac
            OUTPUT: Integer
        """

        inactive_time, inactive_after_last = self.get_inactive_times(mac)

        if inactive_after_last:
            inactive_time = inactive_time[:-1]
        
        total_inactive = sum(int(i[1]) for i in inactive_time if i != '' and len(i) > 1)
        total_active = self.__get_total_active_time(mac)

        if total_active + total_inactive == 0:
            return 100

        return int((total_active / (total_active + total_inactive)) * 100)
    
    def get_reached_out_ips(self, mac : str) -> list[str]:
        """
            Gets all the reached out IP addresses of a certain client

            INPUT: mac
            OUTPUT: List of strings of IP addresses

            @mac: MAC address of user's computer
        """

        command = f"SELECT data, count FROM {self.table_name} WHERE mac = ? AND type = ?;"
        return self.commit(command, mac, MessageParser.CLIENT_IP_INTERACTION)

class UserId (DBHandler):

    USER_ID_NAME = "uid"

    _lock = threading.Lock()
    _instance = None
    
    def __new__(cls, conn, cursor, table_name: str):
        """
            Ensure singleton instance and initialize with existing connection and cursor.

            INPUT: conn, cursor, table_name
            OUTPUT: None
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(UserId, cls).__new__(cls)
            return cls._instance
    
    def __init__(self, conn, cursor, table_name: str):
        """
        Initialize the instance, but only once.
        """
        if not hasattr(self, 'conn') or self.conn is None:
            super().__init__(conn, cursor, table_name)
    
    def delete_mac(self, mac : str) -> None:
        """
            Deletes a certain MAC address from the table

            INPUT: mac
            OUTPUT: None

            @mac: MAC address of user's computer
        """

        command = f"DELETE FROM {self.table_name} WHERE mac = ?;"
        self.commit(command, mac)

        self.clean_deleted_records_DB()

    def insert_data(self, mac: str, hostname : str) -> bool:
        """
            Insert data to SQL table, checks if mac already in use or hostname
            If mac already in use then do not insert
            If hostname then change the hostname and insert

            INPUT: mac, hostname
            OUTPUT: Boolean value to indicate if user already logged in

            @mac: MAC address of user's computer
            @hostname: User's computer hostname
        """

        command = f"SELECT hostname FROM {self.table_name} WHERE mac = ? AND hostname = ?;"
        output = self.commit(command, mac, hostname)

        if output:
            print(f"\n{mac}, hostname: {hostname} -> Have already logged in before")
            return True

        # Fetch all hostnames starting with the given hostname
        command = f"SELECT hostname FROM {self.table_name} WHERE hostname LIKE ? || '%';"
        results = self.commit(command, hostname)
        hostnames = {row[0] for row in results}

        new_hostname = hostname
        if new_hostname in hostnames:
            i = 1
            while f"{hostname}{i}" in hostnames:
                i += 1
            new_hostname = f"{hostname}{i}"

        command = f"INSERT INTO {self.table_name} (mac, hostname) VALUES (?, ?);"
        self.commit(command, mac, new_hostname)

        return False
    
    def update_name(self, prev_name : str, new_name : str):
        """
            Manager changes a name for a client
            
            INPUT: prev_name, new_name
            OUTPUT: None
            
            @prev_name: Previous name of client
            @new_name: New name of client changed by manager
        """
        
        command = f"UPDATE {self.table_name} SET hostname = ? WHERE hostname = ?;"
        self.commit(command, new_name, prev_name)
    
    def check_user_existence(self, hostname : str) -> int:
        """
            Checking for a certain client to see if already connected
            
            INPUT: hostname
            OUTPUT: int
            
            @hostname: hostname of user's computer
        """

        command = f"SELECT COUNT(*) FROM {self.table_name} WHERE hostname = ?;"
        return self.commit(command, hostname)[0][0] > 0
    
    def get_clients(self) -> list[tuple[int,str]]:
        """
            Gets all data on clients mac and hostname
            
            INPUT: None
            OUTPUT: list[tuple[str, str]]
        """

        command = f"SELECT mac, hostname FROM {self.table_name}"
        clients = self.commit(command)

        return clients
    
    def get_mac_by_hostname(self, hostname : str) -> str:
        """
            Gets the according MAC address of a computer by hostname
            
            INPUT: hostname
            OUTPUT: str
            
            @hostname: Hostname of wanted computer
        """

        command = f"SELECT mac FROM {self.table_name} WHERE hostname = ?;"
        return self.commit(command, hostname)[0][0]