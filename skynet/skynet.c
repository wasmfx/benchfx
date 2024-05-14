// WasmFX implementation of the Skynet benchmark.  This implementation
// does not use any form of coroutines.

#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>

#include <fiber.h>

#include "../lib/inc/wasm_utils.h"
#include "parameters.h"

extern
__wasm_import("impl", "yield")
void yield(uint64_t);

extern
__wasm_import("impl", "handle")
uint64_t handle(uint32_t, uint64_t);

__noinline
__wasm_export("skynet")
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
  fiber_init();
  int64_t my_number = skynet(6, 0);
  // printf("%" PRIu64 "\n", my_number);
  int result = verify(my_number, reference);
  fiber_finalize();
  return result;
}
