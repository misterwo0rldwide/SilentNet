#ifndef HEADER_H
#define HEADER_H

#define _GNU_SOURCE
#define __GNU_SOURCE
/* Common header files */
#include <asm/uaccess.h>     // Copy and write to user buffers
#include <linux/fs.h>        // Kernel file system
#include <linux/init.h>      // Module __init __exit
#include <linux/input.h>     // Structures of devices
#include <linux/kernel.h>    // Kernel base functions
#include <linux/kprobes.h>   // Kprobe lib (King)
#include <linux/module.h>    // Kernel module macros
#include <linux/mutex.h>     // Mutex data structure
#include <linux/netdevice.h> // List netdevices of pc
#include <linux/sched.h>   // Scheduler lib, Mainly for current structure (PCB)
#include <linux/slab.h>    // Linux memory allocation
#include <linux/types.h>   // Different data structures types
#include <linux/utsname.h> // Hostname of machine

/* HEADER_H */
#endif
