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
sys.path.append(sys.path[0][:sys.path[0].index("\\manager")])
from protocol import *

__author__ = "Omer Kfir"

web_app = Flask(__name__)

# Global client socket variable
manager_server_sock = ...

screens_dictionary = {"/loading" : 0,
                      "/": 1,
                      "/settings": 2,
                      "/employees": 3,
                      }

current_screen = "/loading"

#Decorator to handle screen access and redirections
def check_screen_access(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        global current_screen

        # Allow access to the loading screen regardless of the current screen
        if request.path == "/loading":
            current_screen = request.path
            return f(*args, **kwargs)

        # For other screens, enforce the hierarchy
        if screens_dictionary[current_screen] > screens_dictionary[request.path]:
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

    manager_server_sock.protocol_send(MessageParser.MANAGER_START_COMM, employees_amount, safety)
    
    return redirect(url_for("employees_screen"))
 
# Main screen - Gets current connected clients
#               And updates screen through them
@web_app.route("/employees")
@check_screen_access
def employees_screen():

    manager_server_sock.protocol_send(MessageParser.MANAGER_GET_CLIENTS)
    connected_clients = [name.decode() for name in manager_server_sock.protocol_recv()[1:]]

    return render_template("mac_screen.html", name_list = connected_clients)

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
def exit_page():
    return render_template("exit_screen.html")

def main():
    
    direct = ""
    
    connected = attemp_server_connection()
    if not connected:
        direct = "/loading"
    
    port = TCPsocket.get_free_port()
    webbrowser.open(f"http://127.0.0.1:{port}" + direct)

    web_app.run(port=port)

if __name__ == "__main__":
    main()