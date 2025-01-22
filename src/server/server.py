#   'Silent net' project server
#   
#       Contains server side implementation 
#       Stores and handles DB
#
#   Omer Kfir (C)

import sys, threading

sys.path.append("..")
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
data_base = ...

def process_client_data(client : client, log_type : str, log_params : bytes) -> None:
    """
        Processes client's sent data
        
        INPUT: client, data
        OUTPUT: None
        
        @client -> Protocol client object
        @data -> List of fields of message sent by client
    """
    
    data_base.insert_data(client.get_address()[0], log_type, log_params)


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
                

def get_clients_hooked_data(client : client) -> None:
    """
        Gets connected client data from hooked functions
        
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
    
        log_type, log_params = data
        log_type = log_type.decode()

        process_client_data(client, log_type, log_params)
    
    remove_disconnected_client(client)
    
    # If removed and now amount of clients is one below max
    # We can let the main thread which receives clients to get
    # Back to receiving clients
    if len(clients_connected) + 1 == max_clients:
        clients_recv_event.set()

def get_clients(server : server, max_clients : int) -> None:
    """
        Connect clients to server
        
        INPUT: server, max_clients
        OUTPUT: None
        
        @server -> Protocol server object
        @max_clients -> Maximum amount of clients chosen by the manager
    """
    global clients_connected
    
    # Main loop for receiving clients
    while proj_run:
    
        try:

            # If did not receive maximum amount of clients
            if len(clients_connected) < max_clients:
                client = server.recv_client()
                clients_thread = threading.Thread(target=get_clients_hooked_data, args=(client,))
                
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
    global max_clients, data_base

    data_base = UserLogsORM(UserLogsORM.DB_NAME, UserLogsORM.USER_LOGS_NAME)
    max_clients = 5

    server = server(max_clients)
    get_clients(server, max_clients)

    server.close()

    data_base.delete_records_DB()
    data_base.close_DB()

    for client_thread, client_sock in clients_connected:
        client_sock.close()
        client_thread.join()
    

if __name__ == "__main__":
    main()
