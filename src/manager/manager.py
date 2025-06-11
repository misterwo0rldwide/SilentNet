"""
'Silent net' Manager Web Interface

This module implements the manager-side web interface for the Silent net project.
It provides a Flask-based web application that allows managers to request data from server

The application enforces a screen hierarchy and handles all communication with the server.
Omer Kfir (C)
"""

import sys
import webbrowser
import os
import signal
import json
from sys import argv
from functools import wraps
from flask import Flask, redirect, render_template, request, jsonify, url_for, send_from_directory

# Append parent directory to be able to import protocol
# sys.path - list of directories that the interpreter will search for modules when importing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../shared')))
from protocol import *

__author__ : str = "Omer Kfir"
server_ip : str = "127.0.0.1"

class SilentNetManager:
    """Main manager application class that encapsulates all Flask routes and server communication"""

    def __init__(self):
        """Initialize the manager application"""
        self.app : webbrowser = Flask(__name__)
        self.manager_socket : bool = None
        self.is_connected : bool = False
        self.screens : dict = {
            "/exit": 0,
            "/loading": 1,
            "/": 2,
            "/settings": 3,
            "/employees": 4,
            "/stats_screen": 5,
        }
        self.current_screen : str = "/"
        self.previous_screen : str = ""
        
        self._setup_routes()
        self._setup_error_handlers()

    def _setup_routes(self):
        """Configure all Flask routes"""
        self.app.route("/exit-program")(self.exit_program)
        self.app.route("/exit")(self.check_screen_access(self.exit_page))
        self.app.route("/loading")(self.check_screen_access(self.loading_screen))
        self.app.route("/")(self.check_screen_access(self.start_screen))
        self.app.route('/check_password', methods=['POST'])(self.check_password)
        self.app.route("/settings")(self.check_screen_access(self.settings_screen))
        self.app.route("/submit_settings", methods=["POST"])(self.submit_settings)
        self.app.route("/employees")(self.check_screen_access(self.employees_screen))
        self.app.route('/delete_client', methods=['POST'])(self.delete_client)
        self.app.route("/manual-connect")(self.manual_connect)
        self.app.route('/update_client_name', methods=['POST'])(self.update_client_name)
        self.app.route("/stats_screen")(self.check_screen_access(self.stats_screen))
        self.app.route("/favicon.ico")(lambda: send_from_directory(os.path.join(self.app.root_path, 'static/images'), 'Logo.png', mimetype='image/vnd.microsoft.icon'))

    def _setup_error_handlers(self):
        """Configure error handlers"""
        self.app.errorhandler(404)(self.page_not_found)
        self.app.errorhandler(500)(self.internal_error)

    def check_screen_access(self, f : callable) -> callable:
        """Decorator to enforce screen hierarchy and track navigation"""

        @wraps(f)
        def wrapper(*args, **kwargs):
            # Allow access to the loading/exit screen regardless of current screen
            if request.path in ["/loading", "/exit"]:
                self.previous_screen = self.current_screen
                self.current_screen = request.path
                return f(*args, **kwargs)
            
            # Allow access to employees screen if current screen is higher in hierarchy
            elif ((request.path == "/employees" and 
                  self.screens[self.current_screen] > self.screens[request.path]) or (request.path == "/settings" and self.current_screen == "/employees")):
                self.previous_screen = self.current_screen
                self.current_screen = request.path
                return f(*args, **kwargs)

            # For other screens, enforce the hierarchy
            elif self.screens[self.current_screen] > self.screens[request.path]:
                return redirect(self.current_screen)
            
            elif self.screens[self.current_screen] == self.screens[request.path]:
                # If the current screen is the same as the requested one, just return the function
                return f(*args, **kwargs)

            self.previous_screen = self.current_screen
            self.current_screen = request.path
            return f(*args, **kwargs)
        return wrapper

    def disconnect(self):
        """Disconnect from the server and clean up resources"""
        if self.manager_socket:
            self.manager_socket.close()
        self.is_connected = False

    def exit_program(self):
        """Handle application exit"""
        if self.is_connected:
            self.manager_socket.protocol_send(MessageParser.MANAGER_MSG_EXIT)
        self.disconnect()
        os.kill(os.getpid(), signal.SIGINT)
        return '', 204

    def page_not_found(self, error):
        """Handle 404 errors"""
        return render_template("http_error.html", redirect_url=self.current_screen)

    def internal_error(self, error):
        """Handle 500 errors"""
        return render_template("internal_error.html")

    def exit_page(self):
        """Render exit confirmation screen"""
        return render_template("exit_screen.html", previous_screen=self.previous_screen)

    def loading_screen(self):
        """Render loading screen and attempt connection"""
        self.disconnect()
        return render_template("loading_screen.html")

    def start_screen(self):
        """Render the initial login screen"""
        password_incorrect = request.args.get('password_incorrect', 'false')
        return render_template("opening_screen.html", password_incorrect=password_incorrect)

    def check_password(self):
        """Validate manager password with server"""
        password = request.form.get('password')

        if not self.is_connected:
            self.connect_to_server()
            if not self.is_connected:
                return redirect(url_for("loading_screen"))
        
        sent = self.manager_socket.protocol_send(MessageParser.MANAGER_MSG_PASSWORD, encrypt=False, compress=False)
        if sent == 0:
            self.connect_to_server()
            if not self.is_connected:
                return redirect(url_for("loading_screen"))
            
            self.manager_socket.protocol_send(MessageParser.MANAGER_MSG_PASSWORD, encrypt=False, compress=False)

        if not self.manager_socket.exchange_keys():
            return redirect(url_for("loading_screen"))

        sent = self.manager_socket.protocol_send(password)
        if sent == 0:
            return redirect(url_for("loading_screen"))
        
        response = self.manager_socket.protocol_recv()[MessageParser.PROTOCOL_DATA_INDEX - 1].decode()
        
        if response == MessageParser.MANAGER_VALID_CONN:
            return redirect(url_for("settings_screen"))
        
        if not self.is_connected:
            return redirect(url_for("loading_screen"))
        
        self.disconnect()
        return redirect(url_for("start_screen", password_incorrect='true'))

    def settings_screen(self):
        """Render server settings screen"""
        return render_template("settings_screen.html")

    def submit_settings(self):
        """Update server settings"""
        employees_amount = request.form.get('employees_amount')
        safety = request.form.get('safety')

        sent = self.manager_socket.protocol_send(
            MessageParser.MANAGER_SND_SETTINGS, 
            employees_amount, 
            safety
        )
        if sent == 0:
            return redirect(url_for("loading_screen"))
        
        return redirect(url_for("employees_screen"))

    def employees_screen(self):
        """Render employee list screen"""
        sent = self.manager_socket.protocol_send(MessageParser.MANAGER_GET_CLIENTS)
        if sent == 0:
            return redirect(url_for("loading_screen"))
        
        clients = self.manager_socket.protocol_recv()
        if clients == b"" or clients == b"ERR":
            return redirect(url_for("loading_screen"))
        
        clients = clients[MessageParser.PROTOCOL_DATA_INDEX:]
        stats = []
        for client in clients:
            name, active, connected = client.decode().split(",")
            stats.append([name, int(active), int(connected)])

        return render_template("name_screen.html", name_list=stats)

    def delete_client(self):
        """Handle client deletion request"""
        data = request.get_json()
        client_name = data.get('name')
        
        if not client_name:
            return jsonify({'success': False, 'message': 'No name provided'}), 400
        
        sent = self.manager_socket.protocol_send(MessageParser.MANAGER_DELETE_CLIENT, client_name)
        if sent == 0:
            return redirect(url_for("loading_screen"))

        return jsonify({'success': True, 'message': f'Client {client_name} deleted successfully'})

    def manual_connect(self):
        """Handle manual connection attempt"""
        self.connect_to_server()
        current_state = self.is_connected

        if self.is_connected:
            self.manager_socket.protocol_send(MessageParser.MANAGER_CHECK_CONNECTION, encrypt=False, compress=False)
            self.disconnect()

        return jsonify({"status": current_state})

    def update_client_name(self):
        """Handle client name update request"""
        data = request.get_json()
        current_name, new_name = data.get('current_name'), data.get('new_name')
        
        sent = self.manager_socket.protocol_send(
            MessageParser.MANAGER_CHG_CLIENT_NAME, 
            current_name, 
            new_name
        )
        if sent == 0:
            return jsonify({"redirect": url_for("loading_screen")})

        response = self.manager_socket.protocol_recv()[MessageParser.PROTOCOL_DATA_INDEX - 1].decode()
        if response == MessageParser.MANAGER_VALID_CHG:
            return jsonify({"success": True})
        elif response == MessageParser.MANAGER_INVALID_CHG:
            return jsonify({"success": False, "message": "Name is already used"})
        else:
            return jsonify({"redirect": url_for("loading_screen")})

    def stats_screen(self):
        """Render detailed statistics screen for a client"""
        client_name = request.args.get('client_name')
        if client_name is None:
            return redirect(url_for("employees_screen"))

        sent = self.manager_socket.protocol_send(MessageParser.MANAGER_GET_CLIENT_DATA, client_name)
        if sent == 0:
            return redirect(url_for("loading_screen"))
        
        stats = self.manager_socket.protocol_recv()
        if stats == b"" or stats == b"ERR":
            return redirect(url_for("loading_screen"))
        
        if stats[MessageParser.PROTOCOL_DATA_INDEX - 1].decode() == MessageParser.MANAGER_CLIENT_NOT_FOUND:
            return redirect(url_for("employees_screen"))
        
        stats = json.loads(stats[MessageParser.PROTOCOL_DATA_INDEX])
        return render_template("stats_screen.html", stats=stats, client_name=client_name)

    def connect_to_server(self):
        """Attempt to connect to the server"""
        self.manager_socket = client(manager=True)
        self.is_connected = self.manager_socket.connect(server_ip, server.SERVER_BIND_PORT)
        
        if not self.is_connected:
            return render_template("loading_screen.html")
        
        self.manager_socket.set_timeout(5)

    def run(self):
        """Run the Flask application"""
        port = TCPsocket.get_free_port()
        webbrowser.open(f"http://127.0.0.1:{port}/")
        self.app.run(port=port)


def main():
    """Entry point for the manager application"""
    global server_ip

    if len(argv) != 2:
        print("Wrong Usage: python manager.py <server_ip>")
    
    else:
        ip = argv[1].split(".")
        if len(ip) != 4:
            print("IP not valid - ipv4 consists 4 numbers")
            return
            
        for n in ip:
            if (not n.isnumeric()) or (int(n) < 0 or int(n) > 255):
                print("IP not valid - ip numbers are no valid")
                return
                
        server_ip = ".".join(ip)
        manager = SilentNetManager()
        manager.run()

if __name__ == "__main__":
    main()