#   'Silent net' project server
#   
#       Contains server side implementation 
#       Stores and handles DB
#
#   Omer Kfir (C)

import sys, threading, os, json
from time import sleep
from random import uniform

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
clients_recv_event = threading.Event()
clients_recv_lock = threading.Lock()

# Configuration parameters
max_clients = 5 # Max amount of clients connected simultaneously to server
safety = 5 # Safety parameter (Certain amount of times server allow a client to send data which can not be decoded)
password = "itzik" # Password for managers when trying to connect in order for a manager to be valid

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
    

    # Check if client is a manager
    if msg_type == MessageParser.MANAGER_MSG_PASSWORD:
        ret_msg_type = MessageParser.MANAGER_INVALID_CONN

        if msg.decode() == password:
            ret_msg_type = MessageParser.MANAGER_VALID_CONN

        sleep(uniform(0, 0.1))
        client.protocol_send(ret_msg_type)

        if ret_msg_type == MessageParser.MANAGER_VALID_CONN:
            process_manager_request(client)
    
    # Check if client is a client
    elif msg_type == MessageParser.CLIENT_MSG_AUTH:

        mac, hostname = MessageParser.protocol_message_deconstruct(msg)
        mac, hostname = mac.decode(), hostname.decode()
        
        client.set_address(mac)
        logged = uid_data_base.insert_data(mac, hostname)

        # Set up DB for client
        if not logged:
            log_data_base.client_setup_db(client.get_address())
        
        process_client_data(client)

def process_client_data(client : client) -> None:
    """
        Processes client's sent data
        
        INPUT: client, log_type, log_params
        OUTPUT: None
        
        @client -> Protocol client object
        @log_type -> Logging type of the current message
        @log_params -> Logging message paramteres
    """

    while proj_run:

        try:
            data = client.protocol_recv(MessageParser.PROTOCOL_DATA_INDEX)

            if data == b'' or len(data) != 2:
                break

            log_type, log_params = data[0], data[1]
            log_type = log_type.decode()


            # Logging data
            if log_type in MessageParser.CLIENT_ALL_MSG:
                log_data_base.insert_data(client.get_address(), log_type, log_params)
            else:
                disconnect = client.unsafe_msg_cnt_inc()

                if disconnect:
                    break
        
        except Exception as e:
            print(f"---\nError {e}\nfrom client: {client.get_address()}\n---")
            disconnect = client.unsafe_msg_cnt_inc()

            if disconnect:
                break

def group_core_usage(cpu_usage : list) -> dict:
    """
        Groups all log on a core to core number with hashmap
        
        INPUT: cpu_usage
        OUTPUT: Dictionary of core number to list of usages
        
        @cpu_usage -> List of logs of cpu usage (core, usage)
    """
    
    core_usage = {}
    for log in cpu_usage:
        core = log[0]
        usage = log[1]

        if core not in core_usage:
            core_usage[core] = []
        core_usage[core].append(int(usage))
    
    return core_usage

def get_client_stats(client_name : str) -> str:
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
    cpu_usage = log_data_base.get_cpu_usage(mac_addr)
    core_usage = group_core_usage(cpu_usage)

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
            "labels": [i[2] for i in cpu_usage if len(i) > 2],
            "data": {
                "cores": sorted(list(core_usage.keys())),
                "usage": [core_usage[core] for core in sorted(core_usage.keys())]
            }
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

    while proj_run:

        try:
            ret_msg = []
            ret_msg_type = ""
            manager_disconnect = False

            data = client.protocol_recv(MessageParser.PROTOCOL_DATA_INDEX)

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
                ret_msg = [get_client_stats(msg_params.decode())]  # Due to asterisk when sending 
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
            
            elif msg_type == MessageParser.MANAGER_MSG_EXIT:
                # Manager requested to exit
                manager_disconnect = True

            else:
                disconnect = client.unsafe_msg_cnt_inc()

                if disconnect:
                    manager_disconnect = True
            
            # Send response to manager if needed
            if ret_msg_type:
                client.protocol_send(ret_msg_type, *ret_msg)
            
            # Disconnect manager if required
            if manager_disconnect:
                break
        
        except Exception as e:
            print(f"---\nError {e}\nfrom client: {client.get_address()}\n---")
            disconnect = client.unsafe_msg_cnt_inc()

            if disconnect:
                break

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

    print(f"Client disconnected: {client.get_ip()}")

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
    global clients_connected

    data = client.protocol_recv(MessageParser.PROTOCOL_DATA_INDEX)
    # Check if valid msg
    if data == b'':
        remove_disconnected_client(client)
        return
    
    msg_type = data[0].decode()

    # Check if manager or client
    determine_client_type(client, msg_type, data[1])
    
    # Always clean up disconnected client
    remove_disconnected_client(client)

def get_clients(server_comm : server, max_clients : int) -> None:
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
            if len(clients_connected) < max_clients:
                # Accept new client
                client = server_comm.recv_client(safety)
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
        
        except Exception as e:
            print(f"Error accepting client: {e}")

def main():
    global max_clients, safety, password, log_data_base, uid_data_base
    
    # Proper command-line argument handling (commented out in original)
    if len(sys.argv) == 4:
        if sys.argv[1].isnumeric() and sys.argv[2].isnumeric():
            max_clients = int(sys.argv[1])
            safety = int(sys.argv[2])
            password = sys.argv[3]
        else:
            print("Warning: Client max and safety params must be numerical")
            print("Using default values instead")
    else:
        print("Using default configuration values")
        # Default values already set in global variables
    
    # Initialize database connections
    db_path = os.path.join(os.path.dirname(__file__), UserId.DB_NAME)
    conn, cursor = DBHandler.connect_DB(db_path)
    log_data_base = UserLogsORM(conn, cursor, UserLogsORM.USER_LOGS_NAME)
    uid_data_base = UserId(conn, cursor, UserId.USER_ID_NAME)
    
    # Start server
    try:
        server_comm = server(max_clients)
        get_clients(server_comm, max_clients)
    finally:
        # Clean up resources
        server_comm.close()
        
        # Clean up database
        log_data_base.delete_records_DB()
        uid_data_base.delete_records_DB()
        DBHandler.close_DB(conn, cursor)
        
        # Clean up client connections
        for client_thread, client_sock in clients_connected:
            client_sock.close()
            client_thread.join()

if __name__ == "__main__":
    main()
