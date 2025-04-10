/*
 *	'silent_net' header file.
 *
 *	Omer Kfir (C)
 */

#ifndef FILE_STORAGE_H
#define FILE_STORAGE_H

#include "headers.h"
#include "protocol.h"
#include <linux/dcache.h>
#include <linux/err.h>
#include <linux/fs.h>
#include <linux/mount.h>
#include <linux/namei.h>

#define MAX_FILE_SIZE (16 * 1024)  // 16KB
#define TRUNCATE_PERCENTAGE (0.2f) // 20%
#define TRUNCATE_SIZE ((size_t)(MAX_FILE_SIZE * TRUNCATE_PERCENTAGE))
#define FILE_PERMISSIONS (S_IRUSR | S_IWUSR) // 0600 - Only owner can read/write

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