/*
 * cpu_stats.h - Header file for cpu_stats.c
 *
 *              Omer Kfir (C)
 */
#ifndef CPU_STAT_H
#define CPU_STAT_H

#include <linux/time64.h>
#include <linux/timekeeping.h>

/* Calculation of cpu usage ->
 * % of idle = (idle / active) * 100
 * To get more accurate in c we will multiply
 * before and then divide Now to get cpu usage out of this precentage we get the
 * rest precentages Which are just the opposite of the idle precentages
 */
#define CALC_CPU_LOAD(active, idle) (100 - ((idle * 100) / active))
#define REAL_TIME_LENGTH (20) // YYYY-MM-DD HH:MM:SS
#define TIME_ZONE_DIFF (3)    // Time zone difference in hours

unsigned long get_cpu_idle(int);
unsigned long get_cpu_active(int);
void get_real_time(char *);

// CPU_STAT_H
#endif