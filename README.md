<p align="center">
  <img src="https://github.com/user-attachments/assets/94e37340-9791-4739-a4bf-f2c3eaebd1c8" alt="Silent Net Logo" width="650"/>
</p>

<h1 align="center">Silent Net</h1>
<p align="center"><i>Advanced Employee Monitoring & Analytics Platform</i></p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version 1.0.0"/>
  <img src="https://img.shields.io/badge/kernel-6.11.0_19_generic-orange" alt="Kernel 6.11.0-19-generic"/>
  <img src="https://img.shields.io/badge/license-GPL-green" alt="GPL License"/>
</p>

---

## 🔍 Overview

**Silent Net** delivers enterprise-grade employee monitoring with unparalleled depth and security. Built on kernel-level hooking technology, it provides real-time visibility into employee activities while maintaining robust security and management controls.

### Key Features

- **Comprehensive Monitoring** - Capture process creation, input events, CPU usage, and network patterns
- **Secure Architecture** - End-to-end encryption with multi-layered authentication
- **Intuitive Management** - Real-time web dashboard with powerful visualization tools
- **Scalable Deployment** - Support for multiple clients with centralized management

---

## 🏗️ Architecture

Silent Net employs a three-tier architecture:

### 1. Kernel Module Client

The core monitoring engine that operates at OS kernel level:

- **Kernel Integration** - Utilizes kprobes to hook critical system functions
- **Low Footprint** - Minimal performance impact while collecting detailed metrics
- **Stealth Operation** - Transparent collection of user activities
- **Comprehensive Coverage** - Monitors processes, inputs, CPU, and networking

### 2. Central Server

The intelligence hub that manages all aspects of the monitoring ecosystem:

- **Multi-client Management** - Handles concurrent connections securely
- **Data Warehousing** - Structured storage of all collected metrics
- **Authentication** - Manager identity verification and access control
- **Data Processing** - Real-time analysis of incoming monitoring data

### 3. Manager Interface

The command center for administrators:

- **Interactive Dashboard** - Flask-based web interface for monitoring activities
- **Data Visualization** - Real-time graphs and analytics
- **Configuration Controls** - Customizable monitoring parameters
- **User Management** - Employee activity oversight and reporting

---

## 🔐 Security Framework

Silent Net implements enterprise-grade security at all levels:

- **Transport Layer Security** - Encrypted communications between components
- **Authentication Protocols** - Secure password protection for administrator access
- **Threat Mitigation** - Automatic disconnection for suspicious activity patterns
- **Data Protection** - Secure storage of all monitoring information

---

## 🚀 Getting Started

### Server Deployment

```bash
cd server
python server.py <max_clients> <safety> <password>
```

Configuration parameters:
- `max_clients`: Maximum concurrent client connections (default: 5)
- `safety`: Tolerance limit for invalid messages (default: 5)
- `password`: Manager authentication credentials (default: "itzik")

### Client Installation

```bash
make
sudo insmod proj.ko
```

### Manager Setup

```bash
cd manager
python manager.py
```

Access the dashboard at `http://localhost:5000` by default.

---

## 📊 Analytics Capabilities

Silent Net collects and visualizes key metrics:

- **Process Analytics** - Track application usage patterns and durations
- **Input Activity** - Monitor keyboard and mouse engagement levels
- **System Utilization** - Core-by-core CPU usage statistics
- **Network Classification** - Communication categorized by type (web, email, etc.)

---

## 📋 System Requirements

- **Server**: Python 3.x, Flask framework
- **Client**: Linux 6.11.0-19-generic kernel
- **Manager**: Python 3.x, modern web browser
- **Network**: TCP/IP connectivity between all components

---

## 📜 License

This project is distributed under the GNU General Public License (GPL).

---

<p align="center">Developed by <strong>Omer Kfir</strong> | &copy; 2025</p>