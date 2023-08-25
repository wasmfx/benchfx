// Bespoke implementation of the Skynet benchmark.  This
// implementation does not use any form of coroutines.

#include <stdint.h>
#include <inttypes.h>

#include "parameters.h"

uint64_t skynet(int level, uint64_t num) {
  if (level == 0) return num;
  else {
    uint64_t lb = num * children_per_level;
    uint64_t ub = lb + children_per_level;
    uint64_t sum = 0;
    level--;
    for (uint64_t i = lb; i < ub; i++)
      sum += skynet(level, i);
    return sum;
  }
}

int main(void) {
  return verify(skynet(num_levels, 0), reference);
}
