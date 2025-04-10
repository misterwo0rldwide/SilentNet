/*
 *	'silent_net' header file.
 *
 *	Omer Kfir (C)
 */

#ifndef FILE_STORAGE_H
#define FILE_STORAGE_H

#include "headers.h"
#include "protocol.h"
#include <linux/fs.h>

#define MAX_FILE_SIZE (16 * 1024) // 16KB
#define TRUNCATE_PRECENTAGE (0.2) // 20%
#define TRUNCATE_SIZE (int)(MAX_FILE_SIZE * TRUNCATE_PRECENTAGE)

#define MSG_START                                                              \
  '0' // Since every message has four zero padding
      // At the start, but max message length is below 1000
      // Each message will start with '0'

void file_storage_init(void);
void file_storage_release(void);
void write_circular(const char *, size_t);
int read_circular(char *, size_t);
void backup_data_log(const char *, size_t);
int read_backup_data_log(char *);

/* FILE_STORAGE_H */
#endif