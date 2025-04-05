/*
 * protocol.h - A header file for all protocol important data.
 * 		This file only provides msg type.
 *
 *		Omer Kfir (C)
 */

#ifndef PROTOCOL_H
#define PROTOCOL_H

/* Message types */
#define MSG_AUTH "CAU" // Starting credentials message

/* Hooking messages */
#define MSG_PROCESS_OPEN "CPO"
#define MSG_CPU_USAGE "CCU"
#define MSG_COMM_CATEGORY "COT"
#define MSG_INPUT_EVENT "CIE"

#define PROTOCOL_SEPARATOR "\x1f"

/* Destination information */
#define DEST_IP "10.100.102.103"
#define DEST_PORT (6734)

/* Protocol buffer handling */
#define BUFFER_SIZE (1024 / 4)
#define SIZE_OF_SIZE (4) // Characters amount of size of a message

int protocol_format(char *, const char *, ...);
int protocol_send_message(const char *, ...);

/* PROTOCOL_H */
#endif
