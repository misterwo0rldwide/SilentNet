/*
 *	'silent_net' header file for file_storage.c
 *
 *	Omer Kfir (C)
 */

#ifndef FILE_STORAGE_H
#define FILE_STORAGE_H

#include "../headers.h"
#include "../protocol.h"
#include <linux/dcache.h>
#include <linux/err.h>
#include <linux/fs.h>
#include <linux/mount.h>
#include <linux/namei.h>
#include <linux/stat.h>

// Amount of minutes the module will backup data
// Continuing to backup data after that will erase the data from before
#define BACKUP_MINUTES (5)
#define MINUTE_BACKUP_STORAGE (13 * 1024) // Approximately 13k bytes for one minute
#define MAX_FILE_SIZE (BACKUP_MINUTES * MINUTE_BACKUP_STORAGE)
#define TRUNCATE_PERCENTAGE (0.2f) // 20%
#define TRUNCATE_SIZE ((size_t)(MAX_FILE_SIZE * TRUNCATE_PERCENTAGE))
#define FILE_PERMISSIONS (S_IRUSR | S_IWUSR) // 0600 - Only owner can read/write

#define MSG_SEPRATOR "\xff"     // Separator for messages
#define MSG_SEPRATOR_CHR '\xff' // Separator character for messages

void file_storage_init(void);
void file_storage_release(void);
void truncate_file(void);
void write_circular(const char *, size_t);
int read_circular(char *, size_t);
void backup_data_log(const char *, size_t);
int read_backup_data_log(char *);

/* FILE_STORAGE_H */
#endif
