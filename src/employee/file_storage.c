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
  file = safe_file_open(filename, O_RDWR | O_CREAT, FILE_PERMISSIONS);
  if (!file) {
    printk(KERN_ERR "Failed to open file %s\n", filename);
    return;
  }
}

void file_storage_release(void) {
  safe_file_close(file);
  file = NULL;
}

static void truncate_file(void) {
  char cur_chr_read;
  int attempts = 0;
  const int max_attempts = MAX_FILE_SIZE;

  read_pos = (read_pos + TRUNCATE_SIZE) % MAX_FILE_SIZE;

  while (attempts++ < max_attempts) {
    if (safe_file_read(file, &cur_chr_read, 1, &read_pos) < 0)
      break;
    if (cur_chr_read == MSG_START)
      return;
    read_pos = (read_pos + 1) % MAX_FILE_SIZE;
  }

  read_pos = write_pos = 0;
}

void write_circular(const char *data, size_t len) {
  size_t space_remaining;
  ssize_t ret;

  if (write_pos >= read_pos)
    space_remaining = MAX_FILE_SIZE - (write_pos - read_pos);
  else
    space_remaining = read_pos - write_pos;

  if (len >= space_remaining) {
    truncate_file(); // You could also truncate only what's needed
  }

  // Handle wrap-around case
  if (write_pos + len > MAX_FILE_SIZE) {
    // Write first part up to the end of the buffer
    ret = safe_file_write(file, data, MAX_FILE_SIZE - write_pos, &write_pos);
    if (ret < 0) {
      printk(KERN_ERR "Failed to write first part of data to file\n");
      return;
    }

    // Update pointers for the remaining data
    size_t written = MAX_FILE_SIZE - write_pos;
    data += written;
    len -= written;
    write_pos = 0;
  }

  // Write the main data
  ret = safe_file_write(file, data, len, &write_pos);
  if (ret < 0) {
    printk(KERN_ERR "Failed to write data to file\n");
    return;
  }
}

int read_circular(char *buf, size_t len) {
  ssize_t ret;

  if (!file || !buf || len <= 0) {
    printk(KERN_ERR "Invalid parameters for read_circular\n");
    return -EINVAL;
  }

  if (read_pos + len > MAX_FILE_SIZE) {
    // Read first part up to the end of the buffer
    ret = safe_file_read(file, buf, MAX_FILE_SIZE - read_pos, &read_pos);
    if (ret < 0) {
      printk(KERN_ERR "Failed to read first part of data from file\n");
      return ret;
    }

    // Update pointers for the remaining data
    size_t read = MAX_FILE_SIZE - read_pos;
    buf += read;
    len -= read;
    read_pos = 0;
  }

  ret = safe_file_read(file, buf, len, &read_pos);
  if (ret < 0) {
    printk(KERN_ERR "Failed to read data from file\n");
    return ret;
  }
  return ret;
}

void backup_data_log(const char *data, size_t len) {
  if (!file || !data || len > MAX_FILE_SIZE) {
    printk(KERN_ERR "Invalid parameters for backup_data\n");
    return;
  }

  write_circular(data, len);
}

// buf should no less than BUFFER_SIZE (protocol.h)
// RETURN VALUE: Length of message
int read_backup_data_log(char *buf) {
  size_t len;
  ssize_t ret;
  char len_str[SIZE_OF_SIZE + 1] = {0}; // Temporary buffer for length

  if (!file || !buf) {
    printk(KERN_ERR "Invalid parameters for read_backup_data\n");
    return -EINVAL;
  }

  if (read_pos == write_pos) {
    return 0; // No data to read
  }

  ret = read_circular(len_str, SIZE_OF_SIZE);
  if (ret != SIZE_OF_SIZE) {
    printk(KERN_ERR "Failed to read message length (ret=%zd)\n", ret);
    return ret < 0 ? ret : -EIO;
  }

  ret = kstrtoul(len_str, 10, &len);
  if (ret < 0) {
    printk(KERN_ERR "Invalid message length format: %.*s\n", SIZE_OF_SIZE,
           len_str);
    return ret;
  }

  if (len == 0 || len > BUFFER_SIZE - SIZE_OF_SIZE) {
    printk(KERN_ERR "Invalid message length: %zu\n", len);
    return -EINVAL;
  }

  memcpy(buf, len_str, SIZE_OF_SIZE);
  ret = read_circular(buf + SIZE_OF_SIZE, len);
  if (ret != len) {
    printk(KERN_ERR "Failed to read message (expected=%lu, got=%lu)\n", len,
           ret);
    return ret < 0 ? ret : -EIO;
  }

  return len + SIZE_OF_SIZE; // Total bytes read
}