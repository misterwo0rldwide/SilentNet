#   'Silent net' project server
#   
#       Contains server side implementation 
#       Stores and handles DB
#
#   Omer Kfir (C)

import sys, threading, os, json

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

max_clients = ... # Max amount of clients connected simultaneously to server
safety = ... # Safety parameter (Certain amount of times server allow a client to send data which can not be decoded)
password = ... # Password for managers when trying to connect in order for a manager to be valid

# Data base object
log_data_base = ...
uid_data_base = ...

def process_client_data(client : client, log_type : str, log_params : bytes) -> None:
    """
        Processes client's sent data
        
        INPUT: client, log_type, log_params
        OUTPUT: None
        
        @client -> Protocol client object
        @log_type -> Logging type of the current message
        @log_params -> Logging message paramteres
    """

    # Mac and user auth
    if log_type == MessageParser.CLIENT_MSG_AUTH:
        mac, hostname = MessageParser.protocol_message_deconstruct(log_params)
        mac, hostname = mac.decode(), hostname.decode()
        
        client.set_address(mac)
        logged = uid_data_base.insert_data(mac, hostname)

        # Set up DB for client
        if not logged:
            log_data_base.client_setup_db(client.get_address())

    # Logging data
    else:
        log_data_base.insert_data(client.get_address(), log_type, log_params)

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

def process_manager_request(client : client, msg_type : str, msg_params : bytes) -> None:
    """
        Processes client's sent data
        
        INPUT: client, msg_type, msg_params
        OUTPUT: None
        
        @client -> Protocol client object
        @msg_type -> Message type
        @msg_params -> Message paramteres
    """
    global max_clients, safety

    ret_msg = []
    ret_msg_type = ""

    manager_disconnect = False

    # Buisnes logic of manager requets
    if msg_type == MessageParser.MANAGER_SND_SETTINGS:
        max_clients, safety = MessageParser.protocol_message_deconstruct(msg_params)
        max_clients, safety = int(max_clients), int(safety)
        
    elif msg_type == MessageParser.MANAGER_GET_CLIENTS:
        ret_msg = uid_data_base.get_clients()
        ret_msg_type = MessageParser.MANAGER_GET_CLIENTS
    
    elif msg_type == MessageParser.MANAGER_GET_CLIENT_DATA:
        ret_msg = [get_client_stats(msg_params.decode())] # Due to asterik when sending 
        ret_msg_type = MessageParser.MANAGER_GET_CLIENTS
    
    elif msg_type == MessageParser.MANAGER_CHG_CLIENT_NAME:
        prev_name, new_name = MessageParser.protocol_message_deconstruct(msg_params)
        prev_name, new_name = prev_name.decode(), new_name.decode()

        ret_msg = []
        
        # If new_name does not exists
        if not uid_data_base.check_user_existence(new_name):
            uid_data_base.update_name(prev_name, new_name)
            ret_msg_type = MessageParser.MANAGER_VALID_CHG

        else:
            ret_msg_type = MessageParser.MANAGER_INVALID_CHG
    
    elif msg_type == MessageParser.MANAGER_MSG_PASSWORD:
        ret_msg = [] # Not any params to send
        
        # Check wether password is correct
        ret_msg_type = MessageParser.MANAGER_VALID_CONN if password == msg_params.decode() else MessageParser.MANAGER_INVALID_CONN

        if ret_msg_type == MessageParser.MANAGER_INVALID_CONN:
            manager_disconnect = True
    
    elif msg_type == MessageParser.MANAGER_MSG_EXIT:
        manager_disconnect = True
    
    # If there is data to send to manager
    if ret_msg_type:
        client.protocol_send(ret_msg_type, *ret_msg)
    
    # If manager did not enter correct password disconnect it
    if manager_disconnect:
        remove_disconnected_client(client)

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
                

def manage_comm(client : client) -> None:
    """
        Manages communication 
        
        INPUT: client
        OUTPUT: None
        
        @client -> Protocol client object
    """
    global clients_connected
    
    try:
        
        while proj_run:

            # Receive data splitted by message type and all parameters (msg_type, all_params_concatanated)
            data = client.protocol_recv(MessageParser.PROTOCOL_DATA_INDEX)
            
            # Ensure client is connected
            if data == b'':
                break
        
            msg_type = data[0]
            msg_type = msg_type.decode()

            if msg_type[MessageParser.SIG_MSG_INDEX] == MessageParser.CLIENT_MSG_SIG:
                process_client_data(client, msg_type, data[MessageParser.PROTOCOL_DATA_INDEX])
            
            elif msg_type[MessageParser.SIG_MSG_INDEX] == MessageParser.MANAGER_MSG_SIG:
                process_manager_request(client, msg_type, data[MessageParser.PROTOCOL_DATA_INDEX] if len(data) > 1 else "")
    
    except Exception as e:
        print(e)
        
    
    remove_disconnected_client(client)
    
    # If removed and now amount of clients is one below max
    # We can let the main thread which receives clients to get
    # Back to receiving clients
    if len(clients_connected) + 1 == max_clients:
        clients_recv_event.set()

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

            # If did not receive maximum amount of clients
            if len(clients_connected) < max_clients:
                client = server_comm.recv_client()
                clients_thread = threading.Thread(target=manage_comm, args=(client,))
                
                # Append client thread to list
                with clients_recv_lock:
                    clients_connected.append((clients_thread, client))
                
                clients_thread.start()
                
                # If reached maximum amount of clients set the lock
                if len(clients_connected) >= max_clients:
                    clients_recv_event.clear()
                
            else:
                
                # Efficienlty waiting for receiving clients again
                clients_recv_event.wait()
        
        except Exception as e:
            print(f"Error accepting client: {e}")

def main():
    global max_clients, safety, password, log_data_base, uid_data_base
    
    if len(sys.argv) != 4:
        print(f"Wrong Usage: python server.py <Client max> <Safety> <password>")
        #return
    #if not (sys.argv[1].isnumeric() and sys.argv[2].isnumeric()):
    #    print(f"Wrong Usage: Client max and safety params must be numerical")
        #return
    
    max_clients = 5 #int(sys.argv[1])
    safety = 5 #int(sys.argv[2])
    password = "itzik" # sys.argv[3]

    conn, cursor = DBHandler.connect_DB(os.path.join(os.path.dirname(__file__), UserId.DB_NAME))
    log_data_base = UserLogsORM(conn, cursor, UserLogsORM.USER_LOGS_NAME)
    uid_data_base = UserId(conn, cursor, UserId.USER_ID_NAME)
    
    server_comm = server(max_clients)
    get_clients(server_comm, max_clients)

    server_comm.close()

    log_data_base.delete_records_DB()
    uid_data_base.delete_records_DB()
    
    DBHandler.close_DB(conn, cursor)

    for client_thread, client_sock in clients_connected:
        client_sock.close()
        client_thread.join()

if __name__ == "__main__":
    main()
