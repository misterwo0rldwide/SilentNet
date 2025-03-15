/*
 *	'silent net' workqueue header file.
 *	Defines specific work message structures
 *
 * 	Omer Kfir (C)
 */
#ifndef WORKQUEUE_H
#define WORKQUEUE_H

void workqueue_message(void (*)(struct work_struct *), const char *, size_t,
                       bool);
int init_singlethread_workqueue(const char *);
void release_singlethread_workqueue(void);

/* Workqueue message */
typedef struct wq_msg {
  /* Current mission */
  struct work_struct work;

  /* Message dara for sending data */
  char msg_buf[BUFFER_SIZE];
  size_t length;
  bool encrypt;
} wq_msg;

/* WORKQUEUE_H */
#endif
