/*
 *	'silent net' work queue handling
 *
 *	Basic abstraction for data set workqueue
 *	Omer Kfir (C)
 */

#include "workqueue.h"

static struct workqueue_struct
    *workqueue; // Global workqueue for transmission of data

/* Initialize a single thread workqueue */
int init_singlethread_workqueue(const char *workqueue_name) {
  workqueue = create_singlethread_workqueue(workqueue_name);

  if (!workqueue) {
    destroy_workqueue(workqueue);
    return -ENOMEM;
  }

  return 0;
}

/* Flush and destroy singlethread workqueue */
void release_singlethread_workqueue(void) {
  /*
   * Flush all current works in the workqueue
   * Waits for all of kThreads (works) to be closed
   */
  flush_workqueue(workqueue);

  // Destroy workqueue object
  destroy_workqueue(workqueue);
}

/* Queue a new message to be sent */
void workqueue_message(void (*queued_function)(struct work_struct *),
                       const char *msg, size_t length) {
  struct wq_msg *work;

  /* Because we are only able to send the pointer to work_struct
   * We will create a 'father' struct for it, which will contain it
   * And in the function we will perform container_of in order to get
   * The message itself and the length
   */
  work = kmalloc(sizeof(wq_msg), GFP_ATOMIC);
  if (!work)
    return;

  /* Initialize work for it to point to the desired function*/
  INIT_WORK(&work->work, queued_function);

  /* Copy data to wq_msg metadata */
  work->length = min(length, BUFFER_SIZE - 1);
  memcpy(work->msg_buf, msg, work->length);

  /* Push work to workqueue - thread safe function (dont worry :) )*/
  if (!queue_work(workqueue, &work->work))
    kfree(work); // Free if queueing fails
}
