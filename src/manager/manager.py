#
#   'silent net' Manager side.
#   Manager can get different kinds of data
#   About his employees with their monitored work
#   Through requests to server which holds the data
#
#   Omer Kfir (C)
import sys, webbrowser, os, signal
from flask import *

sys.path.append("..")
from protocol import *

__author__ = "Omer Kfir"

web_app = Flask(__name__)

# Global client socket variable
manager_server_sock = ...

# Starting screen (index)
@web_app.route("/")
def start_screen():
    return render_template("opening_screen.html")

# Settings screen
@web_app.route("/settings")
def settings_screen():
    return render_template("settings_screen.html")

# Get settings screen data
@web_app.route("/submit_settings", methods=["POST"])
def submit_settings():
    # Get data from post request
    employees_amount = request.form.get("employees_amount", type=int)
    safety = request.form.get("safety", type=int)

    print(employees_amount, safety)
    return redirect(url_for("employees_screen"))

# Main screen - Gets current connected clients
#               And updates screen through them
@web_app.route("/employees")
def employees_screen():
    connected_clients = ["00:14:22:01:23:45", "01:23:45:67:89:ab", "a1:b2:c3:d4:e5:f6", "f0:da:00:11:22:33", "3c:ff:ef:45:67:89", "bc:de:12:34:56:78", "00:0a:95:9d:68:16", "ab:cd:ef:01:23:45", "00:1a:2b:3c:4d:5e", "10:20:30:40:50:60"]
    return render_template("mac_screen.html", mac_list=connected_clients)

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
def loading_screen():
    return render_template("loading_screen.html")

# Closes the whole program
@web_app.route("/exit-program")
def exit_proj():
    manager_server_sock.close()
    os.kill(os.getpid(), signal.SIGINT)

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