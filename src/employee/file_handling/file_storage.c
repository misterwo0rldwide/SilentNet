/*
 *	'silent_net' File storage handling.
 *      - Used for backup when server is down
 *      - Implements circular buffer
 *      - Meant for single threaded access
 *
 *	Omer Kfir (C)
 */

#include "file_storage.h"

static char *filename = "/var/tmp/.syscache";
static struct file *file;

static loff_t read_pos = 0;  // File read position
static loff_t write_pos = 0; // File write position

static loff_t read_pos_offset;  // Offset for read position
static loff_t write_pos_offset; // Offset for write position

/* Safe file opening function */
static struct file *safe_file_open(const char *path, int flags, umode_t mode) {
  struct file *filp = NULL;

  filp = filp_open(path, flags, mode);

  if (IS_ERR(filp)) {
    printk(KERN_ERR "Cannot open file %s, error: %ld\n", path, PTR_ERR(filp));
    return NULL;
  }

  return filp;
}

/* Safe file reading function */
static ssize_t safe_file_read(struct file *filp, char *buf, size_t len,
                              loff_t *pos) {
  ssize_t ret;

  if (!filp || !buf || len <= 0)
    return -EINVAL;

  ret = kernel_read(filp, buf, len, pos);
  if (ret < 0)
    printk(KERN_ERR "Error reading file, error: %ld\n", ret);

  return ret;
}

/* Safe file writing function */
static ssize_t safe_file_write(struct file *filp, const char *buf, size_t len,
                               loff_t *pos) {
  ssize_t ret;

  if (!filp || !buf || len <= 0)
    return -EINVAL;

  ret = kernel_write(filp, buf, len, pos);
  if (ret < 0)
    printk(KERN_ERR "Error writing to file, error: %ld\n", ret);

  return ret;
}

/* Safe file closing function */
static int safe_file_close(struct file *filp) {
  struct path path;
  struct dentry *dentry;
  int err;

  if (!filp || !filename)
    return -EINVAL; // Invalid arguments

  // Get the file's path
  err = kern_path(filename, LOOKUP_FOLLOW, &path);
  if (err)
    return err;

  // Get the dentry and inode for unlinking
  dentry = path.dentry;
  if (!dentry || !dentry->d_inode) {
    path_put(&path);
    return -ENOENT; // File not found
  }

  // Unlink the file
  err = vfs_unlink(&nop_mnt_idmap, d_inode(dentry->d_parent), dentry, NULL);
  path_put(&path);
  if (err)
    return err; // Return error if unlink fails

  // Close the file
  filp_close(filp, NULL);
  return 0;
}

void file_storage_init(void) {
  char buf[sizeof(loff_t)];
  file = safe_file_open(filename, O_RDWR | O_CREAT, FILE_PERMISSIONS);
  if (!file) {
    printk(KERN_ERR "Failed to open file %s\n", filename);
    return;
  }

  /*
   * In case where the file wasn't erased properly (Computer crashed)
   * we need to read the last read/write positions from the file
   * and set them to the current positions.
   */
  read_pos_offset = MAX_FILE_SIZE + 1;
  write_pos_offset = read_pos_offset + sizeof(loff_t);

  safe_file_read(file, buf, sizeof(loff_t), &read_pos_offset);
  memcpy(&read_pos, buf, sizeof(loff_t));

  safe_file_read(file, buf, sizeof(loff_t), &write_pos_offset);
  memcpy(&write_pos, buf, sizeof(loff_t));

  read_pos = read_pos > MAX_FILE_SIZE ? 0 : read_pos;
  write_pos = write_pos > MAX_FILE_SIZE ? 0 : write_pos;
}

void file_storage_release(void) {
  safe_file_close(file);
  file = NULL;
}

static void save_file_pos(loff_t *pos, loff_t *offset) {
  char buf[sizeof(loff_t)];
  if (!file) {
    printk(KERN_ERR "File not opened\n");
    return;
  }

  memcpy(buf, pos, sizeof(loff_t));
  if (safe_file_write(file, buf, sizeof(loff_t), offset) < 0)
    printk(KERN_ERR "Failed to write read_pos to file\n");

  offset -= sizeof(loff_t);
}

void truncate_file(void) {
  char cur_chr_read;
  int attempts = 0;
  loff_t distance;
  const int max_attempts = MAX_FILE_SIZE;

  if (write_pos >= read_pos)
    distance = write_pos - read_pos;
  else
    distance = MAX_FILE_SIZE - (read_pos - write_pos);

  // If called it means an error was caused, therefore we must fix it
  if (distance < TRUNCATE_SIZE) {
    read_pos = write_pos;
    return;
  }

  distance -= TRUNCATE_SIZE;
  read_pos = (read_pos + TRUNCATE_SIZE) % MAX_FILE_SIZE;
  while (attempts++ < max_attempts && distance > 0) {
    if (safe_file_read(file, &cur_chr_read, 1, &read_pos) < 0)
      break;
    if (cur_chr_read == MSG_SEPRATOR_CHR) {
      return;
    }
    read_pos %= MAX_FILE_SIZE;
    distance--;
  }

  read_pos = write_pos = 0;
}

void write_circular(const char *data, size_t len) {
  ssize_t ret;
  loff_t original_write_pos = write_pos;

  if (!data || len == 0 || len > MAX_FILE_SIZE) {
    printk(KERN_ERR "Invalid parameters for write_circular\n");
    return;
  }

  write_pos %= MAX_FILE_SIZE; // Ensure write_pos is within bounds

  // Check space (with truncation if needed)
  size_t space_remaining;
  if (write_pos >= read_pos)
    space_remaining = MAX_FILE_SIZE - (write_pos - read_pos);
  else
    space_remaining = read_pos - write_pos;

  if (len >= space_remaining) {
    truncate_file(); // Free space by discarding old messages
  }

  // Handle wrap-around: Write in two parts if needed
  if (write_pos + len > MAX_FILE_SIZE) {
    size_t first_part = MAX_FILE_SIZE - write_pos;
    ret = safe_file_write(file, data, first_part, &write_pos);
    if (ret != first_part) {
      write_pos = original_write_pos; // Rollback on failure
      printk(KERN_ERR "Failed to write first part (ret=%zd)\n", ret);
      return;
    }

    // Update for second part
    data += first_part;
    len -= first_part;
    write_pos = 0;
  }

  // Write remaining data (or full data if no wrap-around)
  ret = safe_file_write(file, data, len, &write_pos);
  if (ret != len) {
    write_pos = original_write_pos; // Rollback on failure
    printk(KERN_ERR "Failed to write data (ret=%zd)\n", ret);
  }
}

int read_circular(char *buf, size_t len) {
  ssize_t ret;
  loff_t original_read_pos = read_pos;

  read_pos %= MAX_FILE_SIZE; // Ensure read_pos is within bounds

  if (buf == NULL) {
    read_pos = (read_pos + len) % MAX_FILE_SIZE;
    return len;
  }

  if (!buf || len == 0 || len > MAX_FILE_SIZE) {
    printk(KERN_ERR "Invalid parameters for read_circular\n");
    return -EINVAL;
  }

  // Handle wrap-around: Read in two parts if needed
  if (read_pos + len > MAX_FILE_SIZE) {
    size_t first_part = MAX_FILE_SIZE - read_pos;
    ret = safe_file_read(file, buf, first_part, &read_pos);
    if (ret != first_part) {
      read_pos = original_read_pos; // Rollback on failure
      printk(KERN_ERR "Failed to read first part (ret=%zd)\n", ret);
      return ret < 0 ? ret : -EIO;
    }

    // Update for second part
    buf += first_part;
    len -= first_part;
    read_pos = 0;
  }

  // Read remaining data (or full data if no wrap-around)
  ret = safe_file_read(file, buf, len, &read_pos);
  if (ret != len) {
    read_pos = original_read_pos; // Rollback on failure
    printk(KERN_ERR "Failed to read data (ret=%zd)\n", ret);
    return ret < 0 ? ret : -EIO;
  }

  return len; // Total bytes read
}

void backup_data_log(const char *data, size_t len) {
  if (!file || !data || len > MAX_FILE_SIZE) {
    printk(KERN_ERR "Invalid parameters for backup_data\n");
    return;
  }

  write_circular(data, len);
  write_circular(MSG_SEPRATOR, 1);

  // Write the write_pos to the file
  save_file_pos(&write_pos, &write_pos_offset);
}

// buf should no less than BUFFER_SIZE (protocol.h)
// RETURN VALUE: Length of message
int read_backup_data_log(char *buf) {
  size_t len;
  ssize_t ret;
  char len_str[SIZE_OF_SIZE + 1] = {0}; // Temporary buffer for length
  loff_t prev_read_pos;                 // Store the original read position

  if (!file || !buf) {
    printk(KERN_ERR "Invalid parameters for read_backup_data\n");
    return -EINVAL;
  }

  if (read_pos == write_pos) {
    return 0; // No data to read
  }

  // Save current read position in case we need to revert
  prev_read_pos = read_pos;

  // First, read the size prefix
  ret = read_circular(len_str, SIZE_OF_SIZE);
  if (ret != SIZE_OF_SIZE) {
    printk(KERN_ERR "Failed to read message length (ret=%zd)\n", ret);
    truncate_file();
    return ret < 0 ? ret : -EIO;
  }

  ret = kstrtoul(len_str, 10, &len);
  if (ret < 0) {
    printk(KERN_ERR "0.Invalid message length format: %s\n", len_str);
    // Restore original read position on error
    truncate_file();
    return ret;
  }

  if (len == 0 || len > BUFFER_SIZE - SIZE_OF_SIZE) {
    printk(KERN_ERR "1.Invalid message length: %zu\n", len);
    // Restore original read position on error
    read_pos = prev_read_pos;
    return -EINVAL;
  }

  // Copy length to the output buffer
  memcpy(buf, len_str, SIZE_OF_SIZE);

  // Read the actual message content
  ret = read_circular(buf + SIZE_OF_SIZE, len);
  if (ret != len) {
    printk(KERN_ERR "Failed to read message (expected=%lu, got=%lu)\n", len,
           ret);
    // Restore original read position on error
    read_pos = prev_read_pos;
    return ret < 0 ? ret : -EIO;
  }

  buf[len + SIZE_OF_SIZE] = '\0'; // Null-terminate the message
  read_circular(NULL, 1);         // Read the separator

  save_file_pos(&read_pos, &read_pos_offset); // Save the read position
  return len + SIZE_OF_SIZE;                  // Total bytes read
}
