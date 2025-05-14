ignored_processes = {
    # Kernel threads and low-level
    "kthreadd", "rcu_sched", "rcu_bh", "migration", "ksoftirqd", "kworker",
    "kdevtmpfs", "kauditd", "kswapd", "watchdog", "bioset", "crypto",
    "scsi_eh", "kpsmoused", "ipv6_addrconf", "systemd", "systemd-kthread",

    # Init/system base
    "init", "systemd-journald", "systemd-logind", "systemd-udevd",
    "systemd-timesyncd", "systemd-resolved", "systemd-networkd",
    "upstart", "rsyslogd", "cron", "atd", "dbus-daemon", "login", "agetty",
    "polkitd", "udisksd", "colord", "fwupd", "rtkit-daemon", "accounts-daemon",

    # Udev-related
    "udevd", "systemd-udevd", "udevadm", "eudev", "devtmpfs", "mdev",

    # Network / system services
    "sshd", "avahi-daemon", "wpa_supplicant", "NetworkManager", "ModemManager",
    "rpcbind", "nscd", "dnsmasq", "cupsd", "bluetoothd", "nm-dispatcher",

    # Display/session managers
    "gdm", "gdm3", "lightdm", "sddm", "Xorg", "X", "xwayland", "wayland-0",
    "gnome-session", "gnome-shell", "plasmashell", "kwin_x11", "kwin_wayland",

    # Sound, input, graphical services
    "pulseaudio", "pipewire", "pipewire-media-session", "wireplumber",
    "gsettings", "dconf-service", "gnome-keyring-daemon", "gconfd-2",

    # Tracker / GVFS / indexing
    "tracker-miner-fs", "tracker-store", "tracker-extract", "tracker-miner-apps",
    "tracker-writeback", "gvfsd", "gvfsd-fuse", "gvfs-udisks2-volume-monitor",
    "gvfs-mtp-volume-monitor", "gvfs-gphoto2-volume-monitor",
    "gvfs-afc-volume-monitor", "gvfs-goa-volume-monitor",

    # Accessibility and session helpers
    "at-spi-bus-launcher", "at-spi2-registryd", "brltty", "gpg-agent", "gpgv", "gpgconf", 
    "seahorse", "evolution-addressbook-factory", "evolution-calendar-factory",

    # Snap/Flatpak/sandboxing
    "snapd", "flatpak", "xdg-document-portal", "xdg-desktop-portal",
    "xdg-permission-store", "bubblewrap", "xdg-settings", "xdg-mime", "pingsender",

    # Containers, virtualization
    "dockerd", "containerd", "runc", "crio", "podman", "lxcfs", "libvirtd",
    "qemu-system-x86_64", "virtlogd", "virtlockd",

    # Misc session/system
    "gnome-software", "update-notifier", "packagekitd", "packagekit",
    "mission-control-5", "telepathy-*", "boltd", "geoclue", "ibus-daemon",
    "ibus-engine-simple", "ibus-x11", "pactl", "pw-cat", "pw-cli", "gnome-session-b",

    # Firmware and security agents
    "fwupd", "fwupd-refresh", "apport", "whoopsie", "kerneloops",
    
    # Firefox internal processes
    "Web Content", "RDD Process", "Socket Process", "Privileged Cont",
    "Utility Process", "Sandbox", "Isolated Web Co", "Forked",
    "plugin-cont", "WebExtensions", "Sandbox Forked", "WebKitNetworkPr", "WebKitWebProces",
    "apt-key", "apt-config", 

    # Snap-related
    "snap", "snapd", "snap-exec", "snap-confine", "snap-rev", "snap-update",
    "snap-desktop-launch", "snap-seccomp", "snapctl",

    # XDG / Desktop helpers
    "XdgDesktop", "XdgTerms", "Isolated Servic", "app", "5", "pigzreader",
    "desktop-launch", "glxtest", "MainThread"
}
