/*
 * cpu_stats.c - Handles CPU usage calculations
 *
 *              Omer Kfir (C)
 */

#include "cpu_stats.h"
#include "headers.h"

// Get total idle time of cpu core
unsigned long get_cpu_idle(int core) {
  struct kernel_cpustat *kcs = &kcpustat_cpu(core);
  return kcs->cpustat[CPUTIME_IDLE];
}

// Get total active time of cpu core
// To be clear - active time also includes idle time
// Active time is the total time the cpu core has done any state it can be in
unsigned long get_cpu_active(int core) {
  unsigned long total_active = 0;
  struct kernel_cpustat *kcs = &kcpustat_cpu(core);

  int i;
  for (i = 0; i < NR_STATS; i++) // Iterate through all states
    total_active += kcs->cpustat[i];

  return total_active;
}