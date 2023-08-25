#ifndef __SKYNET_PARAMETERS_H
#define __SKYNET_PARAMETERS_H

#include <stdint.h>
/* #include <stdio.h> */
/* #include <inttypes.h> */

const uint32_t num_levels = 6;
const uint64_t children_per_level = 10;

const uint64_t reference = 499999500000;

int verify(const uint64_t my_number, const uint64_t reference) {
  //printf("result = %" PRIu64 ", reference == %" PRIu64 "\n", my_number, reference);
  if (my_number == reference) return 0;
  else return 1;
}

#endif
