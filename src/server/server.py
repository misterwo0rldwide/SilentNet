#   'Silent net' project server
#   
#       Contains server side implementation 
#       Stores and handles DB
#
#   Omer Kfir (C)

import sys, threading, os, json
from time import sleep
from random import uniform
from keyboard import on_press_key
from socket import timeout

# Append parent directory to be able to append protocol
path = os.path.dirname(__file__)
sys.path.append(os.path.abspath(os.path.join(path, '../shared')))

from encryption import *
from protocol import *
from DB import *

__author__ = "Omer Kfir"

# Project currently running
proj_run = True

# Clients globals
clients_connected = [] # List of (thread object, client object)
macs_connected = [] # List of all names of employees wihch are connected
clients_recv_event = threading.Event()
clients_recv_lock = threading.Lock()

# Configuration parameters
max_clients = 5 # Max amount of clients connected simultaneously to server
safety = 5 # Safety parameter (Certain amount of times server allow a client to send data which can not be decoded)
password = "itzik" # Password for managers when trying to connect in order for a manager to be valid
manager_connected = False # Flag for if manager is connected or not

# Data base object
log_data_base = ...
uid_data_base = ...

def determine_client_type(client : client, msg_type : str, msg : bytes) -> None:
    """
        Determines client type based on first message sent
        
        INPUT: client, msg_type, msg
        OUTPUT: None
        
        @client -> Protocol client object
        @msg_type -> Message type
        @msg -> Message parameters
    """
    global manager_connected, macs_connected

    # Check if client is a manager
    if msg_type == MessageParser.MANAGER_MSG_PASSWORD:
        ret_msg_type = MessageParser.MANAGER_INVALID_CONN

        # Only encrypt for manager, so then only exchange keys
        # After manager is connected
        client.exchange_keys()
        msg = client.protocol_recv(MessageParser.PROTOCOL_DATA_INDEX)

        if msg != b'':
            msg = msg[MessageParser.PROTOCOL_DATA_INDEX - 1].decode()

        if msg == password:
            ret_msg_type = MessageParser.MANAGER_VALID_CONN
            manager_connected = True

        # Prevent timing attack
        sleep(uniform(0, 0.05))
        client.protocol_send(ret_msg_type)

        if ret_msg_type == MessageParser.MANAGER_VALID_CONN:
            process_manager_request(client)
        
        return True
    
    # Check if client is a client
    elif msg_type == MessageParser.CLIENT_MSG_AUTH:

        mac, hostname = MessageParser.protocol_message_deconstruct(msg)
        mac, hostname = mac.decode(), hostname.decode()
        
        with clients_recv_lock:
            macs_connected.append(mac)
        
        client.set_address(mac)
        logged = uid_data_base.insert_data(mac, hostname)

        # Set up DB for client
        if not logged:
            log_data_base.client_setup_db(client.get_address())
        
        process_employee_data(client, mac)
    
    return False

def process_employee_data(client : client, mac : str) -> None:
    """
        Processes employee's sent data
        
        INPUT: client, log_type, log_params
        OUTPUT: None
        
        @client -> Protocol client object
        @log_type -> Logging type of the current message
        @log_params -> Logging message paramteres
    """

    print(f"\nEmployee connected: {client.get_ip()}")
    while proj_run:

        try:
            data = client.protocol_recv(MessageParser.PROTOCOL_DATA_INDEX, decrypt=False)
            
            # Timeout exception
            if data == b'ERR':
                continue
            
            if data == b'' or len(data) != 2:
                break

            log_type, log_params = data[0], data[1]
            log_type = log_type.decode()

            # Logging data
            if log_type in MessageParser.CLIENT_ALL_MSG:
                log_data_base.insert_data(client.get_address(), log_type, log_params)
            else:
                disconnect = client.unsafe_msg_cnt_inc(safety)

                if disconnect:
                    print("Disconnecting employee due to unsafe message count")
                    break
        
        except Exception as e:
            print(f"---\nError -> {e}\nfrom client: {client.get_address()}\n---")
            disconnect = client.unsafe_msg_cnt_inc(safety)

            if disconnect:
                print("Disconnecting employee due to unsafe message count")
                return
    
    if mac in macs_connected:
        with clients_recv_lock:
            macs_connected.remove(mac)
        
    print(f"\nEmployee disconnected: {client.get_ip()}")

def get_employee_stats(client_name : str) -> str:
    """
        Gets all avaliable stats on a client
        
        INPUT: client_name
        OUTPUT: String of all stats
        
        @client_name -> Json dumps of all the data
    """
    mac_addr = uid_data_base.get_mac_by_hostname(client_name)
    
    process_cnt = log_data_base.get_process_count(mac_addr)
    inactive_times, inactive_after_last = log_data_base.get_inactive_times(mac_addr)
    words_per_min = int(log_data_base.get_wpm(mac_addr, inactive_times, inactive_after_last))

    core_usage, cpu_usage = log_data_base.get_cpu_usage(mac_addr)
    ip_cnt = log_data_base.get_reached_out_ips(mac_addr)

    # Insert data into json format for manager
    data = {
        "processes": {
            "labels": [i[0].decode() for i in process_cnt],
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

def process_manager_request(client : client) -> None:
    """
        Processes client's sent data
        
        INPUT: client, msg_type, msg_params
        OUTPUT: None
        
        @client -> Protocol client object
        @msg_type -> Message type
        @msg_params -> Message paramteres
    """
    global max_clients, safety

    print(f"\nManager connnected: {client.get_ip()}")
    while proj_run:

        try:
            ret_msg = []
            ret_msg_type = ""
            manager_disconnect = False

            data = client.protocol_recv(MessageParser.PROTOCOL_DATA_INDEX)
            # Timeout exception
            if data == b'ERR':
                continue
            
            if data == b'':
                break

            msg_type = data[0].decode()
            msg_params = data[1] if len(data) > 1 else ""

            # Handle different manager request types
            if msg_type == MessageParser.MANAGER_SND_SETTINGS:
                # Update server settings
                max_clients, safety = MessageParser.protocol_message_deconstruct(msg_params)
                max_clients, safety = int(max_clients), int(safety)
                
            elif msg_type == MessageParser.MANAGER_GET_CLIENTS:
                # Get list of all clients
                clients = uid_data_base.get_clients()
                ret_msg = []

                for mac, hostname in clients:
                    ret_msg.append(f"{hostname},{log_data_base.get_active_precentage(mac)}")

                ret_msg_type = MessageParser.MANAGER_GET_CLIENTS
            
            elif msg_type == MessageParser.MANAGER_GET_CLIENT_DATA:
                # Get detailed stats for a specific client
                ret_msg = [get_employee_stats(msg_params.decode())]  # Due to asterisk when sending 
                ret_msg_type = MessageParser.MANAGER_GET_CLIENTS
            
            elif msg_type == MessageParser.MANAGER_CHG_CLIENT_NAME:
                # Change client hostname
                prev_name, new_name = MessageParser.protocol_message_deconstruct(msg_params)
                prev_name, new_name = prev_name.decode(), new_name.decode()

                ret_msg = []
                
                # If new_name does not exist
                if not uid_data_base.check_user_existence(new_name):
                    uid_data_base.update_name(prev_name, new_name)
                    ret_msg_type = MessageParser.MANAGER_VALID_CHG
                else:
                    ret_msg_type = MessageParser.MANAGER_INVALID_CHG
            
            elif msg_type == MessageParser.MANAGER_DELETE_CLIENT:
                # Delete client from DB
                client_name = msg_params.decode()
                mac = uid_data_base.get_mac_by_hostname(client_name)
                
                log_data_base.delete_mac_records_DB(mac)
                # If client is connected then do not erase it's name from overall clients
                if mac not in macs_connected:                
                    uid_data_base.delete_mac(mac)
                else:
                    # If client is connected then erase it from clients list
                    # But keep the default data in DB
                    log_data_base.client_setup_db(mac)

            elif msg_type == MessageParser.MANAGER_MSG_EXIT:
                # Manager requested to exit
                manager_disconnect = True

            else:
                disconnect = client.unsafe_msg_cnt_inc(safety)

                if disconnect:
                    print("Disconnecting manager due to unsafe message count")
                    manager_disconnect = True
            
            # Send response to manager if needed
            if ret_msg_type:
                client.protocol_send(ret_msg_type, *ret_msg)
            
            # Disconnect manager if required
            if manager_disconnect:
                break
        
        except Exception as e:
            print(f"---\nError -> {e}\nfrom client: {client.get_address()}\n---")
            disconnect = client.unsafe_msg_cnt_inc(safety)

            if disconnect:
                print("Disconnecting manager due to unsafe message count")
                return
    
    print(f"\nManager disconnected: {client.get_ip()}")

def remove_disconnected_client(client : client) -> None:
    """
        Removes a client from global list of clients that are connected
        
        INPUT: client
        OUTPUT: None
        
        @client -> Protocol client object
    """
    
    # If client even exists
    if not client:
        return
    
    # Search for client thread in list
    # Lock even when searching since list can change by the time finished
    # Searching and going to remove
    
    with clients_recv_lock:
        
        # Search for client in clients list
        for index in range(len(clients_connected)):
            _, client_object = clients_connected[index]
            
            if client_object == client:
                del clients_connected[index]
                break

    client.close()
    client = None

    # If removed client brings us below max_clients, notify main thread to resume accepting
    if len(clients_connected) + 1 == max_clients:
        clients_recv_event.set()

def manage_comm(client : client) -> None:
    """
        Manages communication 
        
        INPUT: client
        OUTPUT: None
        
        @client -> Protocol client object
    """
    global clients_connected, manager_connected

    for _ in range(3):
        data = client.protocol_recv(MessageParser.PROTOCOL_DATA_INDEX, decrypt=False)
        # Check if valid msg
        if data == b'' or (data is list and data[0].decode() == MessageParser.MANAGER_CHECK_CONNECTION):
            remove_disconnected_client(client)
            return
        
        if data != b'ERR':
            break
    
    msg_type = data[0].decode()
    if len(clients_connected) >= max_clients and msg_type == MessageParser.CLIENT_MSG_AUTH:
        # If client is not manager and max_clients reached, disconnect
        remove_disconnected_client(client)
        return

    if msg_type == MessageParser.MANAGER_MSG_PASSWORD and manager_connected:
        # If manager is already connected, disconnect new manager
        client.protocol_send(MessageParser.MANAGER_ALREADY_CONNECTED, encrypt=False)
        remove_disconnected_client(client)
        return

    # Check if manager or client
    if determine_client_type(client, msg_type, data[1] if len(data) > 1 else b''):
        manager_connected = False # Function finishes when communication ends so if manager is not connected, set to false

    # Always clean up disconnected client
    remove_disconnected_client(client)

def get_clients(server_comm : server) -> None:
    """
        Connect clients to server
        
        INPUT: server_comm, max_clients
        OUTPUT: None
        
        @server_comm -> Protocol server object
        @max_clients -> Maximum amount of clients chosen by the manager
    """
    global clients_connected
    
    # Main loop for receiving clients
    while proj_run:
        try:
            # Check if we can accept more clients
            if len(clients_connected) < max_clients or not manager_connected:
                # Accept new client
                client = server_comm.recv_client()
                clients_thread = threading.Thread(target=manage_comm, args=(client,))
                
                # Add client to connected list with proper locking
                with clients_recv_lock:
                    clients_connected.append((clients_thread, client))
                
                clients_thread.start()
                
                # If reached maximum, wait for a slot to open
                if len(clients_connected) >= max_clients:
                    clients_recv_event.clear()
            else:
                # Efficiently wait for a client slot to open
                clients_recv_event.wait()
        
        except timeout:
            pass

        except Exception as e:
            print(f"Error -> accepting client: {e}")
    
    print('Server shutting down')

def erase_all_logs() -> None:
    log_data_base.delete_all_records_DB()
    clients = uid_data_base.get_clients()

    for mac, _ in clients:
        log_data_base.client_setup_db(mac)
    
    print("\nErased all logs")

def quit_server() -> None:
    global proj_run
    proj_run = False

def server_settings() -> None:
    global max_clients, safety, password
    
    # Proper command-line argument handling (commented out in original)
    if len(sys.argv) == 4:
        if sys.argv[1].isnumeric() and sys.argv[2].isnumeric():
            if int(sys.argv[1]) > 40 or int(sys.argv[1]) < 1:
                print("Warning: Max clients must be between 1 and 40")
                print("Using default value instead")
            else:
                max_clients = int(sys.argv[1])

            if int(sys.argv[2]) > 5 or int(sys.argv[2]) < 1:
                print("Warning: Safety parameter must be between 1 and 5")
                print("Using default value instead")

            else:
                safety = int(sys.argv[2])
            password = sys.argv[3]
        else:
            print("Warning: Client max and safety params must be numerical")
            print("Using default values instead")
    else:
        print("Using default configuration values")
        print("Usage: python server.py <max_clients : int> <safety : int> <password : str>\n\n")
        # Default values already set in global variables
    
    print(f"Server running with the following configuration:\n" + \
          f"Max clients: {max_clients}\nSafety: {safety}\nPassword: {password}" + \
            "\n\nFor changing configuration, please restart server" + \
            "\n\nPress 'q' to quit server\nPress 'e' to erase all logs\n")
    
    on_press_key('q', lambda _: quit_server())
    on_press_key('e', lambda _: erase_all_logs())

def main():
    global log_data_base, uid_data_base
    server_settings()

    # Initialize database connections
    db_path = os.path.join(os.path.dirname(__file__), UserId.DB_NAME)

    conn1, cursor1 = DBHandler.connect_DB(db_path)
    conn2, cursor2 = DBHandler.connect_DB(db_path)

    log_data_base = UserLogsORM(conn1, cursor1, UserLogsORM.USER_LOGS_NAME)
    uid_data_base = UserId(conn2, cursor2, UserId.USER_ID_NAME)

    # Start server
    try:
        server_comm = server(safety)
        server_comm.set_timeout(1)

        get_clients(server_comm)
    finally:
        # Clean up resources
        server_comm.close()
        DBHandler.close_DB(conn1, cursor1)
        DBHandler.close_DB(conn2, cursor2)
        
        # Clean up client connections
        for client_thread, client_sock in clients_connected:
            client_sock.close()
            client_thread.join()

if __name__ == "__main__":
    main()
