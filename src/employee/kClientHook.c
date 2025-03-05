/*
 * This is a source code of the client side
 * Of 'silent_net' project.
 *
 * blah blah blah
 *
 *
 */

#include "kClientHook.h"
#include "cpu_stats.h"
#include "headers.h"
#include "mac_find.h"
#include "protocol.h"
#include "tcp_socket.h"
#include "transmission.h"
#include "workqueue.h"

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Omer Kfir");
MODULE_DESCRIPTION("Final project");

/* Kprobes structures */
static struct kprobe kps[PROBES_SIZE] = {
    [kp_do_fork] = {.pre_handler = handler_pre_do_fork,
                    .symbol_name = HOOK_PROCESS_FORK},
    [kp_input_event] = {.pre_handler = handler_pre_input_event,
                        .symbol_name = HOOK_INPUT_EVENT},
    [kp_cpu_usage] = {.pre_handler = handler_pre_calc_global_load,
                      .symbol_name = HOOK_CPU_USAGE},
    [kp_send_message] = {.pre_handler = handler_pre_inet_sendmsg,
                         .symbol_name = HOOK_SEND_MESSAGE}};

/* Fork hook */
static int handler_pre_do_fork(struct kprobe *kp, struct pt_regs *regs) {
  // Check for validity and also not sending kernel process
  if (!current || !current->mm || (current->flags & PF_KTHREAD))
    return 0;

  // Check for processes which activated by user
  if (current_uid().val == 0)
    return 0;

  return protocol_send_message(MSG_PROCESS_OPEN, "%s", current->comm);
}

/* CPU Usage */
static int handler_pre_calc_global_load(struct kprobe *kp,
                                        struct pt_regs *regs) {
  // CPU calculation params
  int cpu_core, cpu_usage;
  struct timespec64 tv; // Measure current time
  static long long int last_tv = 0;

  // Current cpu times
  unsigned long idle_time = 0, idle_delta = 0;
  unsigned long actv_time = 0, actv_delta = 0;

  // All cpu cores and their times
  static unsigned long cpu_idle_time[NR_CPUS] = {0};
  static unsigned long cpu_actv_time[NR_CPUS] = {0};
  static bool first_run = true; // Flag to check if it's the first run

  // Get current time
  ktime_get_real_ts64(&tv);

  if (!last_tv) {
    last_tv = tv.tv_sec;
    return 0;
  }

  // Send only after CPU_USAGE_DELAY has passed
  if (tv.tv_sec - last_tv < CPU_USAGE_DELAY)
    return 0;

  for (cpu_core = 0; cpu_core < NR_CPUS; cpu_core++) {
    idle_time = get_cpu_idle(cpu_core);
    actv_time = get_cpu_active(cpu_core);

    if (first_run) {
      // Initialize the arrays with the current CPU times on the first run
      cpu_idle_time[cpu_core] = idle_time;
      cpu_actv_time[cpu_core] = actv_time;
      continue;
    }

    idle_delta = idle_time - cpu_idle_time[cpu_core];
    actv_delta = actv_time - cpu_actv_time[cpu_core];

    cpu_idle_time[cpu_core] = idle_time;
    cpu_actv_time[cpu_core] = actv_time;

    // Check if CPU did work
    if (!actv_delta)
      continue;

    cpu_usage = CALC_CPU_LOAD(actv_delta, idle_delta);
    protocol_send_message(MSG_CPU_USAGE, "%d" PROTOCOL_SEPARATOR "%d", cpu_core,
                          cpu_usage);
  }

  first_run = false; // Set the flag to false after the first run
  last_tv = tv.tv_sec;
  return 0;
}

/* Device input events */
static int handler_pre_input_event(struct kprobe *kp, struct pt_regs *regs) {
  unsigned int code;
  if (!regs) // Checking current is irrelevant due to interrupts
    return 0;

  code = (unsigned int)regs->dx; // Third paramater

  // Only send code, since code for input is unique
  return protocol_send_message(MSG_INPUT_EVENT, "%d", code);
}

/* Output ip communication */
static int handler_pre_inet_sendmsg(struct kprobe *kp, struct pt_regs *regs) {
  struct socket *skt;
  struct dst_entry *dst;
  struct in_addr dest_ip4;
  if (!regs || !regs->di)
    return 0;

  // First parameter is struct socket pointer
  skt = (struct socket *)regs->di;
  if (!skt->sk || !skt->sk->sk_dst_cache)
    return 0;

  dst = skt->sk->sk_dst_cache;
  dest_ip4 = ((struct sockaddr_in *)&dst->peer)->sin_addr;
  return protocol_send_message(MSG_SEND_IP, "%s", inet_ntoa(dest_ip4));
}

/* Sends mac and hostname to server */
static int handle_credentials(void) {
  char mac_buf[MAC_SIZE];
  get_mac_address(mac_buf);

  // Send mac address and hostname
  return send_message(MSG_AUTH, "%s" PROTOCOL_SEPARATOR "%s", mac_buf,
                      utsname()->nodename);
}

/* Register all hooks */
static int register_probes(void) {
  int ret = 0, i;

  /* Iterate through kps array of structs */
  for (i = 0; i < PROBES_SIZE; i++) {
    ret = register_kprobe(&kps[i]);

    if (ret < 0) {
      unregister_probes(i);
      printk(KERN_ERR "Failed to register: %s\n", kps[i].symbol_name);
      return ret;
    }
  }

  printk(KERN_INFO "Finished hooking succusfully\n");
  return ret;
}

/* Unregister all kprobes */
static void unregister_probes(int max_probes) {
  /* Static char to indicate if already unregistered */
  static atomic_t unreg_kprobes =
      ATOMIC_INIT(0); // Use atomic to avoid race condition

  /* Check if it has been set to 1, if not set it to one */
  if (atomic_cmpxchg(&unreg_kprobes, 0, 1) == 0) {
    int i;
    for (i = 0; i < max_probes; i++) {
      unregister_kprobe(&kps[i]);
    }
  }
}

static int __init hook_init(void) {
  int ret = 0;

  /* Initialize all main module objects */
  ret = init_singlethread_workqueue("tcp_sock_queue");
  if (ret < 0)
    return ret;

  data_transmission_init();
  handle_credentials(); // Send credentials before registering hooks

  /* Registers kprobes, if one fails unregisters all registered kprobes */
  ret = register_probes();
  if (ret < 0) {
    release_singlethread_workqueue();
    data_transmission_release();
    return ret;
  }

  printk(KERN_INFO "Finished initializing succesfully\n");
  return ret;
}

static void __exit hook_exit(void) {
  // Closing all module objects
  unregister_probes(PROBES_SIZE);

  // Only after unregistering all kprobes we can safely destroy workqueue
  release_singlethread_workqueue();
  data_transmission_release();

  printk(KERN_INFO "Unregistered kernel probes");
}

module_init(hook_init);
module_exit(hook_exit);
