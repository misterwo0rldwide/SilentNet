<p align="center">
  <img src="https://github.com/user-attachments/assets/94e37340-9791-4739-a4bf-f2c3eaebd1c8" alt="Silent Net Logo" width="650"/>
</p>

<h1 align="center">Silent Net</h1>
<p align="center"><i>The Invisible Force Behind Enterprise Intelligence</i></p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version 1.0.0"/>
  <img src="https://img.shields.io/badge/kernel-6.11.0_19_generic-orange" alt="Kernel 6.11.0-19-generic"/>
  <img src="https://img.shields.io/badge/license-GPL-green" alt="GPL License"/>
</p>

---

## 🕵️ Overview

**Silent Net** isn't just another monitoring tool—it's a fully weaponized, ultra-stealth kernel beast. Built with surgical precision for deep system analytics, it delivers complete real-time surveillance while remaining virtually invisible to the operating system.

**Low noise, high intel.** Perfect for environments where control, security, and invisibility are non-negotiable.

---

## 🔥 Core Features

- **Full-Spectrum Monitoring** – Track process creation, input behavior, CPU core load, and network activities
- **Military-Grade Encryption** – End-to-end security with multi-factor authentication
- **Zero-Overhead Design** – Minimal performance footprint with maximum data extraction
- **Live Command Center** – Real-time interactive web dashboard with cutting-edge analytics
- **Massive Scalability** – Seamlessly manage fleets of monitored devices from a centralized brain
- **Stealth Mode** – **Hides its presence from userland tools and network sniffers** while remaining fully visible to authorized managers

---

## 🧐 Architecture

Silent Net uses a powerful three-tier design:

### 1. Kernel Module Client

- **Deep Kernel Hooks** – Taps directly into system call flow via kprobes
- **Invisible Execution** – Auto-hides from `/proc/modules`, `lsmod`, and traditional kernel listings
- **User Invisibility** – Conceals activities from the local user and basic system monitoring tools
- **Network Stealth** – Packets and communications are hidden from typical sniffers but not from firewalls
- **Port Disguise** – Opens hidden TCP ports invisible to userland utilities like netstat
- **Controlled Reveal** – Managers can selectively unhide the module with a few button presses for maintenance or debugging

### 2. Central Server

- **Secure Hub** – Collects, verifies, and stores all client data with hardened TLS encryption
- **Smart Throttling** – Defends against suspicious client behavior with automated cutoffs
- **Data Core** – Optimized database structuring for fast querying and real-time reporting

### 3. Manager Interface

- **Tactical Dashboard** – Flask-powered, live control panel for full system visibility
- **Graphical Intelligence** – Streamlined graphs, heatmaps, and time-series analytics
- **Policy Editor** – Adjust client behavior and monitoring thresholds on-the-fly
- **User Recon** – Monitor, log, and report employee activity like a hawk

---

## 🛡️ Advanced Stealth Mechanisms

- **Module Hiding** – Kernel module self-erases from system lists upon loading, reversible by manager commands
- **Packet Obfuscation** – Monitoring packets are disguised and hidden from common network sniffers
- **Port Hiding** – TCP/UDP listeners hidden from user enumeration tools
- **Anti-Forensics** – Leaves no traces in default system logs
- **Signature Obfuscation** – Randomized naming and memory footprint masking

---

## ⚙️ Getting Started

### Server Deployment

```bash
cd server
python server.py <max_clients> <safety> <password>
```
Where:
- `max_clients`: Maximum number of clients (default: 5)
- `safety`: Max invalid packet tolerance (default: 5)
- `password`: Manager password (default: "itzik")

### Client Installation

```bash
make
sudo insmod proj.ko
```

Once inserted, the client module operates silently in the background.

### Manager Interface

```bash
cd manager
python manager.py
```

Access your live dashboard at `http://localhost:5000`.

---

## 📈 Analytics Capabilities

- **Process Tracking** – App usage times, frequencies, and anomalies
- **Input Monitoring** – Keyboard and mouse engagement analytics
- **CPU Intelligence** – Per-core real-time CPU load breakdown
- **Network Categorization** – Classifies outbound and inbound traffic types

---

## 💻 System Requirements

- **Server**: Python 3.x, Flask
- **Client**: Linux Kernel 6.11.0-19-generic
- **Manager**: Python 3.x, web browser
- **Networking**: TCP/IP support required

---

## 📜 License

Distributed under the GNU General Public License (GPL).

---

<p align="center">
  Crafted with precision by <strong>Omer Kfir</strong> | &copy; 2025
</p>

