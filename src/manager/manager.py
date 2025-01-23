#
#   'silent net' Manager side.
#   Manager can get different kinds of data
#   About his employees with their monitored work
#   Through requests to server which holds the data
#
#   Omer Kfir (C)
import sys, webbrowser
from flask import *

sys.path.append("..")
from protocol import *

__author__ = "Omer Kfir"

web_app = Flask(__name__)

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
    connected_clients = ...
    return render_template("ip_screen.html", ip_list=connected_clients)


def main():
    
    port = TCPsocket.get_free_port()
    webbrowser.open(f"http://127.0.0.1:{port}")

    web_app.run(port=port)
    

if __name__ == "__main__":
    main()