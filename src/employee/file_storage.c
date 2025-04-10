/*
 *	'silent_net' File storage handling.
 *      - Used for backup when server is down
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
static void safe_file_close(struct file *filp) {
  if (filp) {
    filp_close(filp, NULL);
  }
}

void file_storage_init(void) {
  file = safe_file_open(filename, O_RDWR | O_CREAT | O_APPEND, 0644);
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
  if (!file) {
    printk(KERN_ERR "File not opened\n");
    return;
  }

  // Forward the starting point of reading
  // So we truncate the file data size
  read_pos = (read_pos + TRUNCATE_SIZE) % MAX_FILE_SIZE;
  if (safe_file_read(file, &cur_chr_read, 1, &read_pos) < 0)
    return;

  while (cur_chr_read != MSG_START) {
    read_pos = (read_pos + 1) % MAX_FILE_SIZE;
    if (safe_file_read(file, &cur_chr_read, 1, &read_pos) < 0)
      return;
  }
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

  if (!file || !buf) {
    printk(KERN_ERR "Invalid parameters for read_backup_data\n");
    return -EINVAL;
  }

  if (read_pos == write_pos) {
    printk(KERN_ERR "No data to read\n");
    return 0; // No data to read
  }

  // Read data from the file
  ret = read_circular(buf, SIZE_OF_SIZE);
  if (ret < 0) {
    printk(KERN_ERR "Failed to read data from file\n");
    return ret;
  }

  // Convert string to integer
  ret = kstrtoul(buf, 10, &len);
  if (ret < 0) {
    printk(KERN_ERR "Failed to convert string to integer\n");
    return ret;
  }

  buf += SIZE_OF_SIZE;

  ret = read_circular(buf, len);
  if (ret < 0) {
    printk(KERN_ERR "Failed to read data from file\n");
    return ret;
  }

  ret = len + SIZE_OF_SIZE;
  return ret;
}