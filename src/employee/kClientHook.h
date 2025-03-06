/*
 *	'silent net' kClientHook.h - kernel client hook header file
 *	Contains hook names and function declares
 *
 * 	Omer Kfir (C)
 */

#ifndef CLIENT_HOOK_H
#define CLIENT_HOOK_H

#include "headers.h"

#define HOOK_INPUT_EVENT "input_event"
#define HOOK_CPU_USAGE "calc_global_load"
#define HOOK_SEND_MESSAGE "inet_sendmsg"
#define HOOK_PROCESS_FORK                                                      \
  "kernel_clone" // Originally named 'do_fork'
                 // Linux newer versions use 'kernel clone'
/* #define HOOK_FILE_OPEN "do_sys_openat", "__sys_sendmsg" - Not used, OS
 * frequently uses this functions Hooking such function can crash the computer
 */

#define CPU_USAGE_DELAY (2 * 60) // Two minutes

static int handler_pre_do_fork(struct kprobe *, struct pt_regs *);
static int handler_pre_input_event(struct kprobe *, struct pt_regs *);
static int handler_pre_calc_global_load(struct kprobe *, struct pt_regs *);
static int handler_pre_inet_sendmsg(struct kprobe *, struct pt_regs *);
static int handle_credentials(void);
static int register_probes(void);
static void unregister_probes(int);

static int __init hook_init(void);
static void __exit hook_exit(void);

/* Enum of all kprobes, each kprobe value is the index inside the array */
enum { kp_do_fork, kp_input_event, kp_cpu_usage, kp_send_message, PROBES_SIZE };

/* CLIENT_HOOK_H */
#endif
