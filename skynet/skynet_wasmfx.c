// Bespoke implementation of the Skynet benchmark.  This
// implementation does not use any form of coroutines.

#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>

#include "parameters.h"
#include "wasmfx_import.h"

__attribute__((export_name("skynet")))
uint64_t skynet(uint32_t level, uint64_t num) {
  if (level == 0) {
    wasmfx_yield(num);
    return -1; // dummy value
  }
  else {
    uint64_t lb = num * children_per_level;
    uint64_t ub = lb + children_per_level;
    uint64_t sum = 0;
    level--;
    for (uint64_t i = lb; i < ub; i++)
      sum += wasmfx_handle(level, i);
    return sum;
  }
}

int main(void) {
  printf("%" PRIu64 "\n", skynet(num_levels, 0));
  return 0;
}
