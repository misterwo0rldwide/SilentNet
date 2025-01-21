#
#   'silent net' Manager side.
#   Manager can get different kinds of data
#   About his employees with their monitored work
#   Through requests to server which holds the data
#
#   Omer Kfir (C)
import sys

sys.path.append("..")
import protocol

__author__ = "Omer Kfir"

def main():
    
    client = protocol.client()
    client.connect(protocol.server.SERVER_BIND_IP, protocol.server.SERVER_BIND_PORT)

    
    client.close()

if __name__ == "__main__":
    main()