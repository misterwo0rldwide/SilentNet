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
    # Preserve data on the original called function
    @wraps(f)
    def wrapper(*args, **kwargs):
        global current_screen

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
    return redirect(url_for("employees_screen"))
 
# Main screen - Gets current connected clients
#               And updates screen through them
@web_app.route("/employees")
@check_screen_access
def employees_screen():
    connected_clients = ["OmerKfirAndYuvalMendel", "aaaaaaaaaaaaaabbbbbbbbbbbbbbcccccccccccccc", "01:23:45:67:89:ab", "a1:b2:c3:d4:e5:f6", "f0:da:00:11:22:33", "3c:ff:ef:45:67:89", "bc:de:12:34:56:78", "00:0a:95:9d:68:16", "ab:cd:ef:01:23:45", "00:1a:2b:3c:4d:5e", "10:20:30:40:50:60"]
    return render_template("mac_screen.html", name_list=connected_clients)

def attemp_server_connection() -> bool:
    """
        Attemp to connect to server

        INPUT: None
        OUTPUT: Boolean value to indicate if connection succeeded
    """
    global manager_server_sock

    manager_server_sock = client()
    connection_status = manager_server_sock.connect("127.0.0.1", 6743)

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

# Closes the whole program
@web_app.route("/exit-program")
def exit_proj():
    manager_server_sock.close()
    os.kill(os.getpid(), signal.SIGINT)

@web_app.errorhandler(404)
def page_not_found(error):
    return render_template("http_error.html")

@web_app.errorhandler(500)
def page_not_found(error):
    return render_template("internal_error.html")

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