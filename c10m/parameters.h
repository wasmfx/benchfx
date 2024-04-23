#ifndef __ASYNCWL_PARAMETERS_H
#define __ASYNCWL_PARAMETERS_H

#include <stdint.h>

static const uint32_t modifier = 10;
static const uint32_t total_conn = 10 * 1000000;
#define active_conn ((uint32_t)10000)
static const uint32_t stack_kb = 32;


static const uint32_t reference = 10010000;

 __attribute__ ((unused)) static int verify(const uint32_t my_count, const uint32_t reference) {
  if (my_count == reference) return 0;
  else return 1;
}

#endif
