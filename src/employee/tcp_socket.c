/*
 * 'slient net' project client tcp socket code.
 * Handles communication implementation.
 *
 * Provides basic tcp socket abstraction
 * For KLM
 *
 * Omer Kfir (C)
 */

#include "tcp_socket.h"
#include "headers.h"

/* Initialize a TCP struct socket */
struct socket *tcp_sock_create(void) {
  struct socket *sock;
  struct timespec64 tv;
  int err;

  /* Create tcp socket */
  err = sock_create(AF_INET, SOCK_STREAM, IPPROTO_TCP, &sock);
  if (err < 0) {
    printk(KERN_ERR "Failed to create TCP socket\n");
    return ERR_PTR(err);
  }

  // Set mark on socket
  sock_set_mark(sock->sk, MODULE_MARK);

  /* Set 0.5 second timeout for recv/connect/send */
  tv.tv_sec = 0;           // Seconds
  tv.tv_nsec = SOCK_TIMEO; // Nanoseconds

  err = sock_setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO_NEW, KERNEL_SOCKPTR(&tv),
                        sizeof(tv));
  if (err < 0) {
    printk(KERN_ERR "Failed to set recv timeo %d\n", err);
    return ERR_PTR(err);
  }

  err = sock_setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO_NEW, KERNEL_SOCKPTR(&tv),
                        sizeof(tv));
  if (err < 0) {
    printk(KERN_ERR "Failed to set send timeo\n");
    return ERR_PTR(err);
  }

  return sock;
}

/* Initialize a tcp connection */
int tcp_sock_connect(struct socket *sock, const char *dst_ip, uint16_t port) {
  struct sockaddr_in addr = {0}; // Ensure all values inside struct are zeroed
  int err;

  /* Validate all arguments */
  if (!sock || !sock->ops || !sock->ops->connect || !dst_ip)
    return -EINVAL; // Invalid argument passed

  /* Initialize address structure */
  addr.sin_family = AF_INET;
  addr.sin_port = htons(port);
  addr.sin_addr.s_addr = in_aton(dst_ip);

  // 0 - Means no specific use of the socket (Writing/Receving)
  err = sock->ops->connect(sock, (struct sockaddr *)&addr, sizeof(addr), 0);
  if (err < 0 && err != -EINPROGRESS)
    return err;

  return err;
}

/* Send message through a TCP socket */
int tcp_send_msg(struct socket *sock, const char *msg, size_t length) {
  struct msghdr msg_met = {0};
  struct kvec vec;
  int err;

  /* Validate arguemnts */
  if (!sock || !msg)
    return -EINVAL; // Invalid argument passed

  /* I/O Vector for message tranfering */
  vec.iov_base = (void *)msg;
  vec.iov_len = length;

  err = kernel_sendmsg(sock, &msg_met, &vec, 1, length);
  if (err < 0)
    printk(KERN_ERR "Failed to send message %d\n", err);

  return err;
}

/* Close socket struct */
void tcp_sock_close(struct socket *sock) {
  if (sock)
    sock_release(sock);
}

/* Checks if socket has a certain mark */
bool check_sock_mark(struct sock *sock, __u32 mark) {
  if (!sock)
    return false;

  return sock->sk_mark == mark;
}
