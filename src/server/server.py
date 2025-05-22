"""
'Silent net' project server implementation

This module contains the server-side implementation for the Silent net project.
It handles client connections, manages communication, and interfaces with the database.

Omer Kfir (C)
"""

import sys
import threading
import os
import json
from time import sleep
from random import uniform
from keyboard import on_press_key
from socket import timeout
import traceback

# Append parent directory to be able to import protocol
path = os.path.dirname(__file__)
sys.path.append(os.path.abspath(os.path.join(path, '../shared')))

from protocol import *
from DB import *
from filter import process_limit

__author__ = "Omer Kfir"


class SilentNetServer:
    """
    Main server class that handles all server operations including:
    - Client connections
    - Manager connections
    - Database operations
    - Server configuration
    """

    def __init__(self):
        """Initialize server with default configuration"""
        self.max_clients : int = 5
        self.safety : int = 5
        self.password : str = "itzik"
        self.proj_run : bool = True
        self.manager_connected : bool = False
        self.clients_connected : list[threading.Thread, client] = []  # List of (thread object, client object)
        self.ids_connected : list[int] = []  # List of ids of connected clients
        self.ids_lock : threading.Lock = threading.Lock()
        self.clients_recv_event : threading.Event = threading.Event()
        self.clients_recv_lock : threading.Lock = threading.Lock()
        self.log_data_base : UserLogsORM = None
        self.uid_data_base : UserId = None
        self.server_comm : server = None

    def start(self):
        """Start the server with configured settings"""
        self._load_configuration()
        self._initialize_databases()
        self._setup_keyboard_shortcuts()
        self._run_server()

        print("Server shutting down...")

    def _load_configuration(self):
        """Load server configuration from command line or use defaults"""
        if len(sys.argv) == 4:
            if sys.argv[1].isnumeric() and sys.argv[2].isnumeric():
                if 1 <= int(sys.argv[1]) <= 40:
                    self.max_clients = int(sys.argv[1])
                else:
                    print("Warning: Max clients must be between 1 and 40")
                    print("Using default value instead")

                if 1 <= int(sys.argv[2]) <= 5:
                    self.safety = int(sys.argv[2])
                else:
                    print("Warning: Safety parameter must be between 1 and 5")
                    print("Using default value instead")

                self.password = sys.argv[3]
            else:
                print("Warning: Client max and safety params must be numerical")
                print("Using default values instead")
        else:
            print("Using default configuration values")
            print("Usage: python server.py <max_clients:int> <safety:int> <password:str>\n\n")

        print(f"Server running with configuration:\nMax clients: {self.max_clients}\n"
              f"Safety: {self.safety}\nPassword: {self.password}\n\n"
              "Press 'q' to quit server\nPress 'e' to erase all logs\n")

    def _initialize_databases(self):
        """Initialize database connections"""
        db_path = os.path.join(os.path.dirname(__file__), UserId.DB_NAME)
        conn1, cursor1 = DBHandler.connect_DB(db_path)
        conn2, cursor2 = DBHandler.connect_DB(db_path)

        self.log_data_base = UserLogsORM(conn1, cursor1, UserLogsORM.USER_LOGS_NAME)
        self.uid_data_base = UserId(conn2, cursor2, UserId.USER_ID_NAME)

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for server control"""
        on_press_key('q', lambda _: self.quit_server())
        on_press_key('e', lambda _: self.erase_all_logs())

    def _run_server(self):
        """Main server loop to accept and handle client connections"""
        try:
            self.server_comm = server(self.safety)
            self.server_comm.set_timeout(1)
            self._accept_clients()
        finally:
            self._cleanup()

    def _accept_clients(self):
        """Accept and manage incoming client connections"""
        while self.proj_run:
            try:
                if len(self.clients_connected) < self.max_clients or not self.manager_connected:
                    client = self.server_comm.recv_client()
                    client_thread = threading.Thread(target=self._handle_client_connection, args=(client,))
                    
                    with self.clients_recv_lock:
                        self.clients_connected.append((client_thread, client))
                    
                    client_thread.start()
                    
                    with self.clients_recv_lock:
                        if len(self.clients_connected) >= self.max_clients:
                            self.clients_recv_event.clear()
                else:
                    self.clients_recv_event.wait()
            except timeout:
                pass
            except OSError:
                print("\nServer socket closed")
                break
            except Exception as e:
                print(f"Error accepting client: {e}")
                print(traceback.format_exc())
            

    def _handle_client_connection(self, client : client):
        """Determine client type and route to appropriate handler"""
        data = client.protocol_recv(MessageParser.PROTOCOL_DATA_INDEX, decrypt=False, decompress=False)
        if data == b'' or (isinstance(data, list) and data[0].decode() == MessageParser.MANAGER_CHECK_CONNECTION):
            self._remove_disconnected_client(client)
            return

        msg_type = data[0].decode()
        if len(self.clients_connected) >= self.max_clients and msg_type == MessageParser.CLIENT_MSG_AUTH:
            self._remove_disconnected_client(client)
            return

        if msg_type == MessageParser.MANAGER_MSG_PASSWORD and self.manager_connected:
            client.protocol_send(MessageParser.MANAGER_ALREADY_CONNECTED, encrypt=False)
            self._remove_disconnected_client(client)
            return

        if self._determine_client_type(client, msg_type, data[1] if len(data) > 1 else b''):
            self.manager_connected = False

        if self.proj_run:
            self._remove_disconnected_client(client)

    def _determine_client_type(self, client, msg_type, msg):
        """Determine if client is manager or employee and handle accordingly"""
        if msg_type == MessageParser.MANAGER_MSG_PASSWORD:
            return self._handle_manager_connection(client, msg)
        elif msg_type == MessageParser.CLIENT_MSG_AUTH:
            self._handle_employee_connection(client, msg)
        return False

    def _handle_manager_connection(self, client, msg):
        """Handle manager authentication and connection"""
        ret_msg_type = MessageParser.MANAGER_INVALID_CONN
        client.exchange_keys()
        msg = client.protocol_recv(MessageParser.PROTOCOL_DATA_INDEX)

        if msg != b'':
            msg = msg[MessageParser.PROTOCOL_DATA_INDEX - 1].decode()

        if msg == self.password:
            ret_msg_type = MessageParser.MANAGER_VALID_CONN
            self.manager_connected = True

        sleep(uniform(0, 1))  # Prevent timing attack
        client.protocol_send(ret_msg_type)

        if ret_msg_type == MessageParser.MANAGER_VALID_CONN:
            ManagerHandler(self, client).process_requests()
        
        return True

    def _handle_employee_connection(self, client, msg):
        """Handle employee authentication and connection"""
        id = -1
        
        try:
            mac, hostname = MessageParser.protocol_message_deconstruct(msg)
            mac, hostname = mac.decode(), hostname.decode()
            logged, id = self.uid_data_base.insert_data(mac, hostname)

            with self.ids_lock:
                self.ids_connected.append(id)
            
            client.set_address(mac)
            if not logged:
                self.log_data_base.client_setup_db(id)
            
            ClientHandler(self, client, id).process_data()

        except Exception:
            print(f"Rejecting client {client.get_ip()} due to invalid authentication")
            client.close()

            if id in self.ids_connected:
                with self.ids_lock:
                    self.ids_connected.remove(id)

    def _remove_disconnected_client(self, client):
        """Remove disconnected client from connected clients list"""
        if not client:
            return
        
        with self.clients_recv_lock:
            for index in range(len(self.clients_connected)):
                _, client_object = self.clients_connected[index]
                
                if client_object == client:
                    del self.clients_connected[index]
                    break

        client.close()
        client = None

        with self.clients_recv_lock:
            if len(self.clients_connected) < self.max_clients:
                self.clients_recv_event.set()
        

    def erase_all_logs(self):
        """Erase all logs from the database"""
        with DBHandler._lock:
            self.log_data_base.delete_all_records_DB()
            clients = self.uid_data_base.get_clients()

            for id, _ in clients:
                self.log_data_base.client_setup_db(id)
        
        print("\nErased all logs")

    def quit_server(self):
        """Shut down the server gracefully"""
        self.server_comm.close()
        self.proj_run = False

    def _cleanup(self):
        """Clean up server resources before shutdown"""

        with self.clients_recv_lock:
            for client_thread, _ in self.clients_connected:
                client_thread.join()

        DBHandler.close_DB(self.log_data_base.cursor, self.log_data_base.conn)
        DBHandler.close_DB(self.uid_data_base.cursor, self.uid_data_base.conn)
        
        self.log_data_base.conn, self.log_data_base.cursor = None, None
        self.uid_data_base.conn, self.uid_data_base.cursor = None, None


class ClientHandler:
    """Handles communication with employee clients"""

    def __init__(self, server : SilentNetServer, client : client , id : int):
        self.server : SilentNetServer = server
        self.client = client
        self.id : int = id

        # Dictionary for repeated processes
        self.processManager : process_limit.ProcessDebouncer = process_limit.ProcessDebouncer()

    def process_data(self):
        """Process data received from employee client"""
        print(f"\nEmployee connected: {self.client.get_ip()}")
        
        while self.server.proj_run:
            try:
                data = self.client.protocol_recv(MessageParser.PROTOCOL_DATA_INDEX, decrypt=False, decompress=False)
                
                if data == b'ERR':
                    continue
                
                if data == b'' or len(data) != 2:
                    break

                log_type, log_params = data[0], data[1]
                log_type = log_type.decode()

                # Ignore process which are usually not used by the user
                if log_type == MessageParser.CLIENT_PROCESS_OPEN:
                    log_params = log_params.decode()

                    if log_params in process_filter.ignored_processes:
                        continue

                    if not self.processManager.should_log(log_params):
                        continue

                if log_type in MessageParser.CLIENT_ALL_MSG:
                    self.server.log_data_base.insert_data(self.id, log_type, log_params)
                else:
                    self._handle_unsafe_message()
            
            except Exception as e:
                print(f"Error from client {self.client.get_address()}: {e}")
                print(traceback.format_exc())
                self._handle_unsafe_message()

        self._cleanup_disconnection()

    def _handle_unsafe_message(self):
        """Handle unsafe/invalid messages from client"""
        disconnect = self.client.unsafe_msg_cnt_inc(self.server.safety)

        if disconnect:
            with DBHandler._lock:
                self.server.log_data_base.delete_id_records_DB(self.id)
                self.server.uid_data_base.delete_user(self.id)
            print("Disconnecting employee due to unsafe message count")
            return True
        return False

    def _cleanup_disconnection(self):
        """Clean up when client disconnects"""
        self.client.close()

        # Remove from list of currently connected macs
        # In order to sign to manager that the client is not connected anymore
        if self.server.proj_run and self.id in self.server.ids_connected:
            with self.server.ids_lock:
                self.server.ids_connected.remove(self.id)
        
        print(f"\nEmployee disconnected: {self.client.get_ip()}")


class ManagerHandler:
    """Handles communication with manager clients"""

    def __init__(self, server : SilentNetServer, client : str):
        self.server = server
        self.client = client

    def process_requests(self):
        """Process manager requests"""
        print(f"\nManager connected: {self.client.get_ip()}")
        
        while self.server.proj_run:
            try:
                ret_msg = []
                ret_msg_type = ""
                manager_disconnect = False

                data = self.client.protocol_recv(MessageParser.PROTOCOL_DATA_INDEX)
                if data == b'ERR':
                    continue
                
                if data == b'':
                    break

                msg_type = data[0].decode()
                msg_params = data[1] if len(data) > 1 else ""

                if msg_type == MessageParser.MANAGER_SND_SETTINGS:
                    self._handle_settings_update(msg_params)
                elif msg_type == MessageParser.MANAGER_GET_CLIENTS:
                    ret_msg, ret_msg_type = self._get_client_list()
                elif msg_type == MessageParser.MANAGER_GET_CLIENT_DATA:
                    ret_msg, ret_msg_type = self._get_client_data(msg_params)
                elif msg_type == MessageParser.MANAGER_CHG_CLIENT_NAME:
                    ret_msg_type = self._handle_name_change(msg_params)
                elif msg_type == MessageParser.MANAGER_DELETE_CLIENT:
                    self._delete_client(msg_params)
                elif msg_type == MessageParser.MANAGER_MSG_EXIT:
                    manager_disconnect = True
                else:
                    manager_disconnect = self._handle_unsafe_message()

                if ret_msg_type:
                    self.client.protocol_send(ret_msg_type, *ret_msg)
                
                if manager_disconnect:
                    break
            
            except Exception as e:
                print(f"Error from manager {self.client.get_ip()}: {e}")
                print(traceback.format_exc())
                if self._handle_unsafe_message():
                    return

        # Return to default settings
        self.server.max_clients = 5
        self.server.safety = 5
        
        print(f"\nManager disconnected: {self.client.get_ip()}")

    def _handle_settings_update(self, msg_params):
        """Handle server settings update from manager"""
        new_max_clients, new_safety = MessageParser.protocol_message_deconstruct(msg_params)
        self.server.max_clients, self.server.safety = int(new_max_clients), int(new_safety)

        with self.server.clients_recv_lock:
            if len(self.server.clients_connected) >= self.server.max_clients:
                self.server.clients_recv_event.clear()
            else:
                self.server.clients_recv_event.set()

    def _get_client_list(self):
        """Get list of all clients for manager"""
        clients = self.server.uid_data_base.get_clients()
        ret_msg = []

        for id, hostname in clients:
            active_percent = self.server.log_data_base.get_active_precentage(id)
            is_connected = 1 if id in self.server.ids_connected else 0
            ret_msg.append(f"{hostname},{active_percent},{is_connected}")

        return ret_msg, MessageParser.MANAGER_GET_CLIENTS

    def _get_client_data(self, msg_params):
        """Get detailed stats for a specific client"""
        client_name = msg_params.decode()
        if not self.server.uid_data_base.check_user_existence(client_name):
            return [], MessageParser.MANAGER_CLIENT_NOT_FOUND

        return [self._get_employee_stats(client_name)], MessageParser.MANAGER_GET_CLIENTS

    def _get_employee_stats(self, client_name):
        """Generate statistics for a specific employee"""
        id = self.server.uid_data_base.get_id_by_hostname(client_name)
        
        process_cnt = self.server.log_data_base.get_process_count(id)
        inactive_times, inactive_after_last = self.server.log_data_base.get_inactive_times(id)
        words_per_min = int(self.server.log_data_base.get_wpm(id, inactive_times, inactive_after_last))

        core_usage, cpu_usage = self.server.log_data_base.get_cpu_usage(id)
        ip_cnt = self.server.log_data_base.get_reached_out_ips(id)

        data = {
            "processes": {
                "labels": [i[0] for i in process_cnt],
                "data": [i[1] for i in process_cnt]
            },
            "inactivity": {
                "labels": [i[0] for i in inactive_times],
                "data": [int(i[1]) for i in inactive_times if len(i) == 2]
            },
            "wpm": words_per_min,
            "cpu_usage": {
                "labels": cpu_usage,
                "data": {
                    "cores": sorted(list(core_usage.keys())),
                    "usage": [core_usage[core] for core in sorted(core_usage.keys())]
                }
            },
            "ips": {
                "labels": [i[0].decode() for i in ip_cnt],
                "data": [i[1] for i in ip_cnt]
            }
        }
        
        return json.dumps(data)

    def _handle_name_change(self, msg_params):
        """Handle client name change request"""
        prev_name, new_name = MessageParser.protocol_message_deconstruct(msg_params)
        prev_name, new_name = prev_name.decode(), new_name.decode()

        if not self.server.uid_data_base.check_user_existence(new_name):
            self.server.uid_data_base.update_name(prev_name, new_name)
            return MessageParser.MANAGER_VALID_CHG
        else:
            return MessageParser.MANAGER_INVALID_CHG

    def _delete_client(self, msg_params):
        """Handle client deletion request"""
        client_name = msg_params.decode()

        id = self.server.uid_data_base.get_id_by_hostname(client_name)
        mac = self.server.uid_data_base.get_mac_by_id(id)

        with DBHandler._lock:
        
            # Delete client stats
            self.server.log_data_base.delete_id_records_DB(id)

            # If client is currently connected we need to keep his default
            # Logs in the logging table
            if id in self.server.ids_connected:
                self.server.log_data_base.client_setup_db(id)
            
            # If the client is not connected during its deletion then we completely
            # Earase his data from all the tables
            else:
                self.server.uid_data_base.delete_user(id)

    def _handle_unsafe_message(self):
        """Handle unsafe/invalid messages from manager"""
        disconnect = self.client.unsafe_msg_cnt_inc(self.server.safety)
        if disconnect:
            print("Disconnecting manager due to unsafe message count")
            return True
        return False


def main():
    """Main entry point for the server"""
    server = SilentNetServer()
    server.start()


if __name__ == "__main__":
    main()