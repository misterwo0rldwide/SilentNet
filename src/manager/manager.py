# 'silent net' Manager side.
# Manager can get different kinds of data about his employees with their monitored work
# through requests to the server which holds the data.
#
# Omer Kfir (C)

import sys
import webbrowser
import os
import signal
import json
from functools import wraps
from flask import Flask, redirect, render_template, request, jsonify, url_for

# Append parent directory to be able to import protocol
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../shared')))
from protocol import *
from encryption import *

__author__ = "Omer Kfir"

web_app = Flask(__name__)

# Global client socket variable
manager_server_sock = None
manager_connected = False

screens_dictionary = {
    "/exit": 0,  # Since we want to be able to return to any screen from exit screen, we need it to be zero
    "/loading": 1,
    "/": 2,
    "/settings": 3,
    "/employees": 4,
    "/stats_screen": 5,
}

current_screen = "/"
previous_screen = None

# Decorator to handle screen access and redirections
def check_screen_access(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        global current_screen, previous_screen

        # Allow access to the loading/exit screen regardless of the current screen
        if request.path in ["/loading", "/exit"]:
            previous_screen = current_screen
            current_screen = request.path
            return f(*args, **kwargs)
        
        # Allow access to employees screen if current screen is higher in hierarchy
        elif request.path == "/employees" and screens_dictionary[current_screen] > screens_dictionary[request.path]:
            previous_screen = current_screen
            current_screen = request.path
            return f(*args, **kwargs)

        # For other screens, enforce the hierarchy
        elif screens_dictionary[current_screen] > screens_dictionary[request.path]:
            return redirect(current_screen)

        previous_screen = current_screen
        current_screen = request.path
        return f(*args, **kwargs)
    return wrapper

def disconnect_manager():
    global manager_connected
    if manager_server_sock:
        manager_server_sock.close()
    
    manager_connected = False

@web_app.route("/exit-program")
def exit_proj():
    disconnect_manager()
    os.kill(os.getpid(), signal.SIGINT)  # Terminate the process
    return '', 204  # No content as response

@web_app.errorhandler(404)
def page_not_found(error):
    return render_template("http_error.html")

@web_app.errorhandler(500)
def internal_error(error):
    return render_template("internal_error.html")

@web_app.route("/exit")
@check_screen_access
def exit_page():
    return render_template("exit_screen.html", previous_screen=previous_screen)

@web_app.route("/loading")
@check_screen_access
def loading_screen():
    # Ensure closing the socket if redirected to loading while socket is still up
    disconnect_manager()
    return render_template("loading_screen.html")

@web_app.route("/")
@check_screen_access
def start_screen():
    password_incorrect = request.args.get('password_incorrect', 'false')
    return render_template("opening_screen.html", password_incorrect=password_incorrect)

@web_app.route('/check_password', methods=['POST'])
def check_password():
    password = request.form.get('password')

    if not manager_connected:
        attempt_server_connection()
        if not manager_connected:
            return redirect(url_for("loading_screen"))
    
    # Split password sending into two parts, first one is to notice server of manager trying to connect
    # And then key exchange and password sending
    manager_server_sock.protocol_send(MessageParser.MANAGER_MSG_PASSWORD,  encrypt=False)
    if not manager_server_sock.exchange_keys():
        return redirect(url_for("loading_screen"))

    manager_server_sock.protocol_send(password)
    valid_pass = manager_server_sock.protocol_recv()[MessageParser.PROTOCOL_DATA_INDEX - 1].decode()
    if valid_pass == MessageParser.MANAGER_VALID_CONN:
        return redirect(url_for("settings_screen"))
    
    # Server disconnected socket so we need to reconnect
    attempt_server_connection()

    if not manager_connected:
        return redirect(url_for("loading_screen"))
    
    return redirect(url_for("start_screen", password_incorrect='true'))

@web_app.route("/settings")
@check_screen_access
def settings_screen():
    return render_template("settings_screen.html")

@web_app.route("/submit_settings", methods=["POST"])
def submit_settings():
    employees_amount = request.form.get('employees_amount')
    safety = request.form.get('safety')

    manager_server_sock.protocol_send(MessageParser.MANAGER_SND_SETTINGS, employees_amount, safety)
    return redirect(url_for("employees_screen"))

@web_app.route("/employees")
@check_screen_access
def employees_screen():
    manager_server_sock.protocol_send(MessageParser.MANAGER_GET_CLIENTS)
    connected_clients = manager_server_sock.protocol_recv()[MessageParser.PROTOCOL_DATA_INDEX:]

    stats = []
    for client in connected_clients:
        name, active = client.decode().split(",")
        stats.append([name, int(active)])

    return render_template("name_screen.html", name_list=stats)

@web_app.route('/delete_client', methods=['POST'])
def delete_client():
    data = request.get_json()
    client_name = data.get('name')
    
    if not client_name:
        return jsonify({'success': False, 'message': 'No name provided'}), 400
    
    manager_server_sock.protocol_send(MessageParser.MANAGER_DELETE_CLIENT, client_name)
    return jsonify({'success': True, 'message': f'Client {client_name} deleted successfully'})
    

@web_app.route("/manual-connect")
def manual_connect():
    attempt_server_connection()
    curr_state = manager_connected

    if manager_connected:
        manager_server_sock.protocol_send(MessageParser.MANAGER_CHECK_CONNECTION, encrypt=False)
        disconnect_manager()

    return jsonify({"status": curr_state})

@web_app.route('/update_client_name', methods=['POST'])
def update_client_name():
    data = request.get_json()
    current_name, new_name = data.get('current_name'), data.get('new_name')
    manager_server_sock.protocol_send(MessageParser.MANAGER_CHG_CLIENT_NAME, current_name, new_name)

    ans = manager_server_sock.protocol_recv()[MessageParser.PROTOCOL_DATA_INDEX - 1].decode()
    
    # If name is free to use
    if ans == MessageParser.MANAGER_VALID_CHG:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Name is already used"})

@web_app.route("/stats_screen")
@check_screen_access
def stats_screen():
    client_name = request.args.get('client_name')
    manager_server_sock.protocol_send(MessageParser.MANAGER_GET_CLIENT_DATA, client_name)

    # Since Flask will catch internal errors, even if protocol_recv returns an empty string, it will go to the error page
    stats = json.loads(manager_server_sock.protocol_recv()[MessageParser.PROTOCOL_DATA_INDEX])

    return render_template("stats_screen.html", stats=stats, client_name=client_name)

def attempt_server_connection() -> bool:
    """
    Attempt to connect to the server.

    INPUT: None
    OUTPUT: Boolean value to indicate if the connection succeeded.
    """
    global manager_server_sock, manager_connected

    manager_server_sock = client(manager = True)
    manager_connected = manager_server_sock.connect("127.0.0.1", server.SERVER_BIND_PORT)
    if not manager_connected:
        return render_template("loading_screen.html")
    
    manager_server_sock.set_timeout(0.1)

def main():
    port = TCPsocket.get_free_port()
    webbrowser.open(f"http://127.0.0.1:{port}/")

    web_app.run(port=port)

if __name__ == "__main__":
    main()