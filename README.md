![Logo](https://github.com/user-attachments/assets/94e37340-9791-4739-a4bf-f2c3eaebd1c8)
#Silent Net

A comprehensive employee monitoring system with server-side data collection and manager oversight capabilities.

## Overview

Silent Net is a project designed to monitor employee activities in a networked environment. It consists of three main components:

1. **Kernel Module Client** - Hooks into kernel functions to monitor system activities
2. **Server** - Collects and stores data from clients
3. **Manager Interface** - Web-based dashboard for administrators to view employee activities

The system provides real-time monitoring of various employee activities including process creation, input events, CPU usage, and network communication patterns.

## Components

### Kernel Module Client

The client-side kernel module (`kClientHook.c`) monitors:

- Process creation
- Input events (keyboard/mouse)
- CPU usage statistics
- Network communication

The module uses kprobes to hook into critical kernel functions like process forking, input event handling, and network communications, sending data back to the server.

### Server

The server component (`server.py`) is responsible for:

- Accepting connections from clients and managers
- Storing collected data in databases
- Authentication of manager connections
- Processing and organizing client data

The server can handle multiple client connections simultaneously and enforces security measures through encrypted communications.

### Manager Interface

The manager interface (`manager.py`) provides:

- Web-based dashboard using Flask
- Authentication for administrators
- Real-time employee activity monitoring
- Configuration options for the monitoring system
- Employee data visualization and statistics

## Security Features

- Encrypted communication between components
- Password protection for manager access
- Safety parameters to prevent malicious connections
- Secure storage of monitoring data

## Technical Details

### Server Configuration

The server accepts the following parameters:

- `max_clients`: Maximum number of clients that can connect (default: 5)
- `safety`: Number of invalid messages allowed before disconnection (default: 5)
- `password`: Manager authentication password (default: "itzik")

Example: `python server.py 10 3 my_secure_password`

### Data Collection

The system collects various types of data:

- Process creation events
- User input activity
- CPU usage by core
- Network communication categorized by type (web, email, gaming, etc.)

### Manager Dashboard

The manager interface provides multiple screens:

- Login screen
- Settings configuration
- Employee list with activity percentages
- Detailed statistics for individual employees
- Real-time data visualization

## Installation

1. Set up the server component:
   ```bash
   cd server
   python server.py <max_clients> <safety> <password>
   ```

2. Load the kernel module on client machines:
   ```bash
   make
   sudo insmod proj.ko
   ```

3. Start the manager interface:
   ```bash
   cd manager
   python manager.py
   ```

## Requirements

- Python 3.x
- Flask (for manager interface)
- Linux 6.11.0-19-generic
- Network connectivity between components

## License

This project is licensed under the GPL License - see the LICENSE file for details.

## Author

Omer Kfir
