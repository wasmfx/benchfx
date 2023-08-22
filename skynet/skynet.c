// WasmFX implementation of the Skynet benchmark.  This implementation
// does not use any form of coroutines.

#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>

#include "parameters.h"

extern
__attribute__((import_module("env"),import_name("yield")))
void yield(uint64_t);

extern
__attribute__((import_module("env"),import_name("handle")))
uint64_t handle(uint32_t, uint64_t);

__attribute__((export_name("skynet")))
uint64_t skynet(uint32_t level, uint64_t num) {
  if (level == 0) {
    yield(num);
    return -1; // dummy value
  }
  else {
    uint64_t lb = num * children_per_level;
    uint64_t ub = lb + children_per_level;
    uint64_t sum = 0;
    level--;
    for (uint64_t i = lb; i < ub; i++)
      sum += handle(level, i);
    return sum;
  }
}

int main(void) {
  printf("%" PRIu64 "\n", skynet(num_levels, 0));
  return 0;
}
