/*
 * cpu_stats.h - Header file for cpu_stats.c
 *
 *              Omer Kfir (C)
 */

/* Calculation of cpu usage ->
 * % of idle = (idle / active) * 100
 * To get more accurate in c we will multiply
 * before and then divide Now to get cpu usage out of this precentage we get the
 * rest precentages Which are just the opposite of the idle precentages
 */
#define CALC_CPU_LOAD(active, idle) (100 - ((idle * 100) / active))

unsigned long get_cpu_idle(int);
unsigned long get_cpu_active(int);