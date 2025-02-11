#
#   'silent net' Manager side.
#   Manager can get different kinds of data
#   About his employees with their monitored work
#   Through requests to server which holds the data
#
#   Omer Kfir (C)
import sys, webbrowser, os, signal
from functools import wraps
from flask import *

# Append parent directory to be able to append protocol
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../shared')))
from protocol import *
from encryption import *

__author__ = "Omer Kfir"

web_app = Flask(__name__)

# Global client socket variable
manager_server_sock = ...

screens_dictionary = {"/loading" : 0,
                      "/": 1,
                      "/settings": 2,
                      "/employees": 3,
                      "/stats_screen" : 4,
                      "/exit" :  5, # Not a real number, Just to add it to the dictionary
                      }

current_screen = "/loading"
previous_screen = ...

#Decorator to handle screen access and redirections
def check_screen_access(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        global current_screen, previous_screen

        # Allow access to the loading/exit screen regardless of the current screen
        if request.path == "/loading" or request.path == "/exit":
            previous_screen = current_screen
            current_screen = request.path
            return f(*args, **kwargs)
        
        elif request.path == "/employees" and screens_dictionary[current_screen] > screens_dictionary[request.path]:
            previous_screen = current_screen
            current_screen = request.path
            return f(*args, **kwargs)


        # For other screens, enforce the hierarchy
        elif screens_dictionary[current_screen] > screens_dictionary[request.path]:
            return redirect(current_screen)

        current_screen = request.path
        return f(*args, **kwargs)
    return wrapper

# Starting screen (index)
@web_app.route("/")
@check_screen_access
def start_screen():
    return render_template("opening_screen.html")

# Settings screen
@web_app.route("/settings")
@check_screen_access
def settings_screen():
    return render_template("settings_screen.html")

# Get settings screen data
@web_app.route("/submit_settings", methods=["POST"])
def submit_settings():
    employees_amount = request.form.get('employees_amount')
    safety = request.form.get('safety')

    #manager_server_sock.protocol_send(MessageParser.MANAGER_START_COMM, employees_amount, safety)
    
    return redirect(url_for("employees_screen"))
 
# Main screen - Gets current connected clients
#               And updates screen through them
@web_app.route("/employees")
@check_screen_access
def employees_screen():

    #manager_server_sock.protocol_send(MessageParser.MANAGER_GET_CLIENTS)
    #connected_clients = [name.decode() for name in manager_server_sock.protocol_recv()[1:]]

    connected_clients = ["itzik", "shlomo", "itzik", "shlomo", "itzik", "shlomo", "itzik", "shlomo", "itzik", "shlomo", "itzik", "shlomo", "itzik", "shlomo"]

    return render_template("name_screen.html", name_list = connected_clients)

def attemp_server_connection() -> bool:
    """
        Attemp to connect to server

        INPUT: None
        OUTPUT: Boolean value to indicate if connection succeeded
    """
    global manager_server_sock

    manager_server_sock = client()
    connection_status = manager_server_sock.connect("127.0.0.1", server.SERVER_BIND_PORT)
    
    if connection_status:
        manager_server_sock.set_timeout(0.5)
    
    return connection_status

# Notifies if managed to connect to server
@web_app.route("/manual-connect")
def manual_connect():
    return jsonify({"status": attemp_server_connection()})

# Notifies if managed to connect to server
@web_app.route("/loading")
@check_screen_access
def loading_screen():
    return render_template("loading_screen.html")

@web_app.route("/stats_screen")
@check_screen_access
def stats_screen():
    client_name = request.args.get('client_name')

    # Tmp data till actual data is written in proj
    stats = {
        "processes": {
            "labels": ["Process A", "Process B", "Process C", "itzik", "shlomo", "ani"],
            "data": [12, 19, 3, 4, 25, 0.5]
        },
        "inactivity": {
            "labels": [
                "2023-10-01 10:00",
                "2023-10-01 10:05",
                "2023-10-01 10:10",
                "2023-10-01 10:15",
                "2023-10-01 10:20",
                "2023-10-01 10:25",
                "2023-10-01 10:30",
                "2023-10-01 10:35",
                "2023-10-01 10:40",
                "2023-10-01 10:45",
                "2023-10-01 10:50",
                "2023-10-01 10:55",
                "2023-10-01 11:00",
                "2023-10-01 11:02",
                "2023-10-01 11:04",
                "2023-10-01 11:06",
                "2023-10-01 11:08",
                "2023-10-01 11:10",
                "2023-10-01 11:15",
                "2023-10-01 11:20",
                "2023-10-01 11:25",
                "2023-10-01 11:30",
                "2023-10-01 11:35",
                "2023-10-01 11:40",
                "2023-10-01 11:45",
                "2023-10-01 11:50",
                "2023-10-01 11:55",
                "2023-10-01 12:00"
            ],
            "data": [
                0.1, 0.3, 0.2, 0.4, 0.5, 0.7, 0.3, 0.6, 0.9, 1.2,
                0.8, 1.1, 0.6, 0.4, 0.3, 0.7, 0.5, 1.3, 0.9, 1.5,
                0.4, 0.7, 1.0, 0.5, 0.9, 1.2, 0.6, 0.8
            ]
        },
        "wpm" : 5,
    }

    return render_template("stats_screen.html", stats=stats, client_name=client_name)

@web_app.route("/exit-program")
def exit_proj():
    manager_server_sock.close()  # Close the server socket
    os.kill(os.getpid(), signal.SIGINT)  # Terminate the process
    return '', 204  # No content as response

@web_app.errorhandler(404)
def page_not_found(error):
    return render_template("http_error.html")

@web_app.errorhandler(500)
def page_not_found(error):
    return render_template("internal_error.html")

@web_app.route("/exit")
@check_screen_access
def exit_page():
    return render_template("exit_screen.html", previous_screen=previous_screen)

def main():
    
    direct = ""
    
    connected = attemp_server_connection()
    connected = True
    if not connected:
        direct = "/loading"
    
    port = TCPsocket.get_free_port()
    webbrowser.open(f"http://127.0.0.1:{port}" + direct)

    web_app.run(port=port)

if __name__ == "__main__":
    main()