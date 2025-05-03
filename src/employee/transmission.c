/*
 *	'silent_net' data transmission
 *
 * 	Handles data transmission to destination ip
 *	Message failure result in backup to a circular buffer file
 *
 *	Omer Kfir (C)
 */

#include "transmission.h"

static struct socket *sock;    // Struct socket
static bool connected = false; // Boolean which indicates if currently connected
static struct mutex trns_mutex; // Mutex for thread safe socket handling

int i = 0;

static char cred[BUFFER_SIZE];

static void disconnect(char *msg, size_t len) {
  if (sock) {
    tcp_sock_close(sock);
    sock = NULL;
  }
  connected = false;

  if (!msg || len <= 0)
    return;

  backup_data_log(msg, len);
}

void transmit_data(struct work_struct *work) {
  wq_msg *curr_msg = container_of(work, wq_msg, work);
  int ret;

  // Mainly for backup data when server is up
  char msg_buf[BUFFER_SIZE];
  size_t msg_len;

  mutex_lock(&trns_mutex);

  /* If socket is disconnected try to connect */
  if (!connected) {
    /* When a socket disconnects a new socket needs to be created */
    sock = tcp_sock_create();
    if (IS_ERR(sock)) {
      disconnect(curr_msg->msg_buf, curr_msg->length);
      goto end;
    }

    ret = tcp_sock_connect(sock, dAddress, dPort);
    if (ret < 0) {
      disconnect(curr_msg->msg_buf, curr_msg->length);
      goto end;
    }
    connected = true;

    // Send credentials - only after successful connection
    ret = tcp_send_msg(sock, cred, strlen(cred));
    if (ret < 0) {
      disconnect(curr_msg->msg_buf, curr_msg->length);
      goto end;
    }
  }

  ret = tcp_send_msg(sock, curr_msg->msg_buf, curr_msg->length);
  if (ret < 0) {
    disconnect(curr_msg->msg_buf, curr_msg->length);
  } else if (sock && sock->sk && sock->sk->sk_state == TCP_ESTABLISHED) {
    // If sending message was successful then employee is connected to server
    // So now we will try to flush the backup data to the server
    ret = read_backup_data_log(msg_buf);
    while (ret > 0) {
      msg_len = ret;
      if (msg_len > BUFFER_SIZE) {
        printk(KERN_ERR "Invalid message length: %lu\n", msg_len);
        break;
      }

      ret = tcp_send_msg(sock, msg_buf, msg_len);
      if (ret < 0) {
        disconnect(msg_buf, msg_len);
        break;
      }
      ret = read_backup_data_log(msg_buf);
    }
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
  file_storage_init();
  handle_credentials();
}

/* Closes all transmission objects */
void data_transmission_release(void) {
  // Close socket
  tcp_sock_close(sock);
  file_storage_release();

  /*
   * No need for releasing trns_mutex since
   * The operating system knows to release it on
   * It's own when module is unloaded
   */
}
