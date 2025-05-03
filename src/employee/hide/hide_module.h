/*
 * hide_module.h - header file for hide_module.c
 *
 * Omer Kfir (C)
 */

#ifndef HIDE_MODULE_H
#define HIDE_MODULE_H

#include <linux/module.h>

void hide_this_module(void);
void unhide_this_module(void);

/* HIDE_MODULE_H */
#endif
