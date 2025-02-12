#   'Silent net' project server
#   
#       Contains server side implementation 
#       Stores and handles DB
#
#   Omer Kfir (C)

import sys, threading, os

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
    
    if log_type == MessageParser.CLIENT_MSG_AUTH:
        mac, hostname = MessageParser.protocol_message_deconstruct(log_params)
        
        client.set_address(mac)
        uid_data_base.insert_data(mac, hostname)

    else:
        log_data_base.insert_data(client.get_address(), log_type, log_params)
    
    print(log_type, log_params)

def process_manager_request(client : client, msg_type : str, msg_params : bytes) -> None:
    """
        Processes client's sent data
        
        INPUT: client, msg_type, msg_params
        OUTPUT: None
        
        @client -> Protocol client object
        @msg_type -> Message type
        @msg_params -> Message paramteres
    """

    ret_msg = ""
    ret_msg_type = ""

    # Buisnes logic of manager requets
    if msg_type == MessageParser.MANAGER_GET_CLIENTS:
        ret_msg = uid_data_base.get_clients()
        ret_msg_type = MessageParser.MANAGER_GET_CLIENTS
    
    else:
        ...
    
    client.protocol_send(ret_msg_type, *ret_msg)

def remove_disconnected_client(client : client) -> None:
    """
        Removes a client from global list of clients that are connected
        
        INPUT: client
        OUTPUT: None
        
        @client -> Protocol client object
    """
    
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
                

def manage_comm(client : client) -> None:
    """
        Manages communication 
        
        INPUT: client
        OUTPUT: None
        
        @client -> Protocol client object
    """
    global clients_connected
    
    while proj_run:

        # Receive data splitted by message type and all parameters (msg_type, all_params_concatanated)
        data = client.protocol_recv(MessageParser.PROTOCOL_DATA_INDEX)
        
        # Ensure client is connected
        if data == b'':
            break
    
        msg_type = data[0]
        msg_type = msg_type.decode()

        if msg_type[MessageParser.SIG_MSG_INDEX] == MessageParser.CLIENT_MSG_SIG:
            process_client_data(client, msg_type, data[1])
        
        elif msg_type[MessageParser.SIG_MSG_INDEX] == MessageParser.MANAGER_MSG_SIG:
            process_manager_request(client, msg_type, data[1])
        
    
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
    global max_clients, log_data_base, uid_data_base

    log_data_base = UserLogsORM(path + "\\" + UserId.DB_NAME, UserLogsORM.USER_LOGS_NAME)
    uid_data_base = UserId(path + "\\" + UserId.DB_NAME, UserId.USER_ID_NAME)

    max_clients = 5

    server_comm = server(max_clients)
    get_clients(server_comm, max_clients)

    server_comm.close()

    log_data_base.delete_records_DB()
    log_data_base.close_DB()

    for client_thread, client_sock in clients_connected:
        client_sock.close()
        client_thread.join()

if __name__ == "__main__":
    main()
