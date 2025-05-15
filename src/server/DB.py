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
                id INTEGER NOT NULL,
                type TEXT NOT NULL,
                data BLOB NOT NULL,
                count NUMERIC NOT NULL DEFAULT 1
            );
            ''')
            self.commit('CREATE INDEX IF NOT EXISTS idx_logs_uid_type ON logs(id, type);')
        elif table_name.endswith("uid"):
            self.commit('''
            CREATE TABLE IF NOT EXISTS uid (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac TEXT NOT NULL,
                hostname TEXT NOT NULL UNIQUE,
                original_hostname TEXT
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
            print(f"Error closing database connection: {e}")

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
    
    def client_setup_db(self, id : int) -> None:
        """
            Writes basic logs that need to be for every client when connected
            Writes when client first logged in (Also writes last client input event with the same time)
            Writes an empty record of inactive times
            Writes an empty record of cpu usages

            INPUT: id
            OUTPUT: None

            @id: Id of client
        """

        cur_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # First log of client
        command = f"INSERT INTO {self.table_name} (id, type, data) VALUES (?,?,?);"
        self.commit(command, id, MessageParser.CLIENT_FIRST_INPUT_EVENT, cur_time)

        # "Last" log of client (it's not really the last time, it's just a record for next when client logs again)
        command = f"INSERT INTO {self.table_name} (id, type, data) VALUES (?,?,?);"
        self.commit(command, id, MessageParser.CLIENT_LAST_INPUT_EVENT, cur_time)

        # Empty record of inactive times
        command = f"INSERT INTO {self.table_name} (id, type, data) VALUES (?,?,'');"
        self.commit(command, id, MessageParser.CLIENT_INACTIVE_EVENT)

        # Empty record of cpu usage
        command = f"INSERT INTO {self.table_name} (id, type, data) VALUES (?,?,'');"
        self.commit(command, id, MessageParser.CLIENT_CPU_USAGE)

    def delete_id_records_DB(self, id : int):
        """
            Deletes all records from the table for a specific client ID

            INPUT: id
            OUTPUT: None

            @id: Id of client
        """
        command = f"DELETE FROM {self.table_name} WHERE id = ?"
        self.commit(command, id)

        self.clean_deleted_records_DB()

    def __check_inactive(self, id : int) -> tuple[str, int]:
        """
            Checks if client is currently inactive

            INPUT: int
            OUTPUT: Tuple conists of last datetime in string format client was active and the amount of minutes currently inactive

            @id: Id of client
        """

        cur_time = datetime.now()

        command = f"SELECT data FROM {self.table_name} WHERE id = ? AND type = ?;"
        date_str = self.commit(command, id, MessageParser.CLIENT_LAST_INPUT_EVENT)[0][0]
        
        date = datetime.strptime(date_str , "%Y-%m-%d %H:%M:%S")
        inactive_time = int((cur_time - date).total_seconds() // 60)

        # Inactive time is considered above five minutes
        if inactive_time > 5:
            return date_str, inactive_time
        
        return None, None

    def __update_last_input(self, id : int) -> None:
        """
            Updates last time user logged input event

            INPUT: id
            OUTPUT: None

            @id: Id of client
        """

        # Check if client is inactive until now, if so log it
        date, inactive_time = self.__check_inactive(id)
        if date:

            # Get string of inactive times
            # String format -> datetime of inactive, inactive minutes
            # Example: 2025-10-10 20:20:20,10~2025-10-10 20:20:30,7~
            command = f"SELECT data FROM {self.table_name} WHERE id = ? AND type = ?;"
            data = self.commit(command, id, MessageParser.CLIENT_INACTIVE_EVENT)[0][0]

            data += f"{date},{inactive_time}~"
            command = f"UPDATE {self.table_name} SET data = ? WHERE id = ? AND type = ?;"

            self.commit(command, data, id, MessageParser.CLIENT_INACTIVE_EVENT)

        command = f"UPDATE {self.table_name} SET data = ? WHERE id = ? AND type = ?;"

        cur_time = datetime.now()
        cur_time = cur_time.strftime("%Y-%m-%d %H:%M:%S")
        
        self.commit(command, cur_time, id, MessageParser.CLIENT_LAST_INPUT_EVENT)

    def __get_total_active_time(self, id : int) -> int:
        """
            Calculates total active time of user

            INPUT: int
            OUTPUT: Integer - minutes amount of active time

            @id: Id of client
        """

        command = f"SELECT data FROM {self.table_name} WHERE id = ? AND type = ?;"
        first_input = datetime.strptime(self.commit(command, id, MessageParser.CLIENT_FIRST_INPUT_EVENT)[0][0], "%Y-%m-%d %H:%M:%S")
        last_input = datetime.strptime(self.commit(command, id, MessageParser.CLIENT_LAST_INPUT_EVENT)[0][0], "%Y-%m-%d %H:%M:%S")

        return (last_input - first_input).total_seconds() // 60
    
    def __update_cpu_usage(self, id: int, data : bytes) -> None:
        """
            Updates cpu usage queuery

            INPUT: id, data
            OUTPUT: None

            @id: Id of client
            @data: Bytes of data
        """

        command = f"SELECT data FROM {self.table_name} WHERE id = ? AND type = ?;"
        cpu_logs = self.commit(command, id, MessageParser.CLIENT_CPU_USAGE)[0][0]
        
        if isinstance(cpu_logs, str):
            cpu_logs = cpu_logs.encode()

        cpu_logs += data + b"|"

        command = f"UPDATE {self.table_name} SET data = ? WHERE id = ? AND type = ?;"
        self.commit(command, cpu_logs, id, MessageParser.CLIENT_CPU_USAGE)

    def insert_data(self, id: int, data_type: str, data: bytes) -> None:
        """
            Insert data to SQL table, if record already exists incement its counter

            INPUT: id, data_type, data
            OUTPUT: None

            @id: Id of client
            @data_type: Type of data to be inserted
            @data: Bytes of data
        """

        if data_type == MessageParser.CLIENT_CPU_USAGE:
            self.__update_cpu_usage(id, data)
            return
        
        # Ignore process which are usually not used by the user
        if data_type == MessageParser.CLIENT_PROCESS_OPEN:
            data = data.decode()
            if data in process_filter.ignored_processes:
                return

        command = f"SELECT count FROM {self.table_name} WHERE id = ? AND type = ? AND data = ?;"
        count = self.commit(command, id, data_type, data)

        # If got count -> count exists -> row exists
        if count:
            count = count[0][0] + 1
            command = f"UPDATE {self.table_name} SET count = ? WHERE id = ? AND type = ? AND data = ?;"
        
            self.commit(command, count, id, data_type, data)
        else:
            command = f"INSERT INTO {self.table_name} (id, type, data) VALUES (?,?,?);"
        
            self.commit(command, id, data_type, data)
        
        # Check if it is an input event
        if data_type == MessageParser.CLIENT_INPUT_EVENT:
            self.__update_last_input(id)

    # Statistics done with DB
    def get_process_count(self, id : int) -> list[tuple[str, int]]:
        """
            Gets the amount of times each process was opened for a certain client

            INPUT: id
            OUTPUT: List of tuples of the name of the process and amount of times was opened

            @id: Id of client
        """

        command = f"SELECT data, count FROM {self.table_name} WHERE type = ? AND id = ?;"
        return self.commit(command, MessageParser.CLIENT_PROCESS_OPEN, id)
    
    def get_inactive_times(self, id : int) -> list[tuple[datetime, str]]:
        """
            Calculates idle times of user

            INPUT: id
            OUTPUT: List of Tuples of the datetime the user went idle and the time of idleness

            @id: Id of client
        """

        # Check if currently inactive
        date, inactive_time = self.__check_inactive(id)

        command = f"SELECT data FROM {self.table_name} WHERE type = ? AND id = ?;"
        dates = self.commit(command, MessageParser.CLIENT_INACTIVE_EVENT, id)[0][0]

        if date:
            dates += f"{date},{inactive_time}"

        dates = dates.split("~")
        return [i.split(",") for i in dates], True if date else False
    
    def get_wpm(self, id : int, inactive_times : list[tuple[datetime, int]], inactive_after_last : bool) -> int:
        """
            Calculates the average wpm the user does while excluding inactive times

            INPUT: id, inactive
            OUTPUT: Integer

            @id: Id of client
            @inactive_times: Pre calculated inactive times of user
            @inactive_after_last: Boolean to indicate if inactive times include time after last logged input event
        """

        # Calculate total inactive time in minutes
        if inactive_after_last:
            inactive_times = inactive_times[:-1]
        
        total_inactive = sum(int(i[1]) for i in inactive_times if i != '' and len(i) > 1)

        # Get word count, 57 is the translation for space char in input_event in linux
        # Checks for data which has space char in it
        command = f"SELECT count FROM {self.table_name} WHERE type = ? AND data LIKE '%57%' AND id = ?;"
        words_cnt = self.commit(command, MessageParser.CLIENT_INPUT_EVENT, id)
        words_cnt = words_cnt[0][0] if words_cnt else 0  # Extract value safely

        # Get first input timestamp
        command = f"SELECT data FROM {self.table_name} WHERE type = ? AND id = ?;"
        first_input = datetime.strptime(self.commit(command, MessageParser.CLIENT_FIRST_INPUT_EVENT, id)[0][0], "%Y-%m-%d %H:%M:%S")
        last_input = datetime.strptime(self.commit(command, MessageParser.CLIENT_LAST_INPUT_EVENT, id)[0][0], "%Y-%m-%d %H:%M:%S")

        # Calculate active time in minutes
        active_time = ((last_input - first_input).total_seconds() - total_inactive * 60) / 60
        active_time = max(active_time, 1)  # Prevent division by zero

        return words_cnt // active_time
    
    def get_cpu_usage(self, id: int):
        """
            Gets all logs of cpu usage

            INPUT: id
            OUTPUT: Tuple of Dictionary of cpu cores and their usages and list of times of logs

            @id: Id of client
        """

        command = f"SELECT data FROM {self.table_name} WHERE id = ? AND type = ?;"
        cores_logs = self.commit(command, id, MessageParser.CLIENT_CPU_USAGE)[0][0]

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

    def get_active_precentage(self, id: int) -> int:
        """
            Calculates the percentage of time user was active

            INPUT: id
            OUTPUT: Integer
        """

        inactive_time, inactive_after_last = self.get_inactive_times(id)

        if inactive_after_last:
            inactive_time = inactive_time[:-1]
        
        total_inactive = sum(int(i[1]) for i in inactive_time if i != '' and len(i) > 1)
        total_active = self.__get_total_active_time(id)

        if total_active + total_inactive == 0:
            return 100

        return int((total_active / (total_active + total_inactive)) * 100)
    
    def get_reached_out_ips(self, id : int) -> list[str]:
        """
            Gets all the reached out IP addresses of a certain client

            INPUT: id
            OUTPUT: List of strings of IP addresses

            @id: Id of client
        """

        command = f"SELECT data, count FROM {self.table_name} WHERE id = ? AND type = ?;"
        return self.commit(command, id, MessageParser.CLIENT_IP_INTERACTION)

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
    
    def delete_user(self, id : int) -> None:
        """
            Deletes a certain id address from the table

            INPUT: id
            OUTPUT: None

            @id: Id of client
        """

        command = f"DELETE FROM {self.table_name} WHERE id = ?;"
        self.commit(command, id)

        self.clean_deleted_records_DB()

    def insert_data(self, mac: str, hostname : str, id : int = -1) -> tuple[bool, int]:
        """
            Insert data to SQL table, checks if mac already in use or hostname
            If mac already in use then do not insert
            If hostname then change the hostname and insert

            INPUT: mac, hostname
            OUTPUT: Boolean indicating if already in use and the id of the client

            @mac: MAC address of user's computer
            @hostname: User's computer hostname
            @id: Id of client
        """
        id_command = f"SELECT id FROM {self.table_name} WHERE mac = ? AND hostname = ?;"

        command = f"SELECT hostname FROM {self.table_name} WHERE mac = ? AND hostname = ?;"
        output = self.commit(command, mac, hostname)

        if output:
            print(f"\n{mac}, hostname: {hostname} -> Have already logged in before")
            return True, self.commit(id_command, mac, hostname)[0][0]
        else:
            command = f"SELECT hostname FROM {self.table_name} WHERE mac = ? AND original_hostname = ?;"
            output = self.commit(command, mac, hostname)

            if output:
                print(f"\n{mac}, hostname: {hostname} -> Have already logged in before")
                id_command = f"SELECT id FROM {self.table_name} WHERE mac = ? AND original_hostname = ?;"

                return True, self.commit(id_command, mac, hostname)[0][0]

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

        if id == -1:
            command = f"INSERT OR IGNORE INTO {self.table_name} (mac, hostname, original_hostname) VALUES (?, ?, ?);"
            self.commit(command, mac, new_hostname, new_hostname)

            return False, self.commit(id_command, mac, new_hostname)[0][0]

        command = f"INSERT OR IGNORE INTO {self.table_name} (id, mac, hostname, original_hostname) VALUES (?, ?, ?, ?);"
        self.commit(command, id, mac, new_hostname, new_hostname)
        return False, id
    
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
    
    def get_clients(self) -> list[tuple[int, str]]:
        """
            Gets all data on clients int and hostname
            
            INPUT: None
            OUTPUT: list[tuple[int, str]]
        """

        command = f"SELECT id, hostname FROM {self.table_name}"
        clients = self.commit(command)

        return clients
    
    def get_mac_by_id(self, id : int) -> str:
        """
            Gets the according MAC address of a computer by id
            
            INPUT: id
            OUTPUT: str
            
            @id: Id of wanted computer
        """

        command = f"SELECT mac FROM {self.table_name} WHERE id = ?;"
        return self.commit(command, id)[0][0]
    
    def get_id_by_hostname(self, hostname : str) -> str:
        """
            Gets the according MAC address of a computer by hostname
            
            INPUT: hostname
            OUTPUT: str
            
            @hostname: Hostname of wanted computer
        """

        command = f"SELECT id FROM {self.table_name} WHERE hostname = ?;"
        return self.commit(command, hostname)[0][0]