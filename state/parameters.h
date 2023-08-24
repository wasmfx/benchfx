#ifndef __STATE_PARAMETERS_H
#define __STATE_PARAMETERS_H

#include <stdint.h>

const uint32_t count_to = 10000000;

int verify(const uint32_t count, const uint32_t reference) {
  if (count == reference) return 0;
  else return 1;
}

#endif
