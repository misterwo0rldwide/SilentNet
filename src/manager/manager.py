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

def main():
    pass
    

if __name__ == "__main__":
    main()