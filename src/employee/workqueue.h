/*
 *	'silent net' workqueue header file.
 *	Defines specific work message structures
 *
 * 	Omer Kfir (C)
 */
#ifndef WORKQUEUE_H
#define WORKQUEUE_H

#include "headers.h"
#include "protocol.h"

#include <linux/workqueue.h> // Smart work queue implementation for different tasks

void workqueue_message(void (*)(struct work_struct *), const char *, size_t);
int init_singlethread_workqueue(const char *);
void release_singlethread_workqueue(void);

/* Workqueue message */
typedef struct wq_msg {
  /* Current mission */
  struct work_struct work;

  /* Message dara for sending data */
  char msg_buf[BUFFER_SIZE];
  size_t length;
} wq_msg;

/* WORKQUEUE_H */
#endif
