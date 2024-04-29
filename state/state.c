// An abstract effectful implementation of stateful counting.

#include <stdint.h>
#include <wasm.h>
#include <fiber.h>

#include "parameters.h"

extern
__wasm_import("impl", "state_get")
int32_t state_get(void);

extern
__wasm_import("impl", "state_put")
void state_put(int32_t);

extern
__wasm_import("impl", "handle_count")
int32_t handle_count(int32_t, const int32_t);

__noinline
__wasm_export("count")
int32_t count(const int32_t limit) {
  for (; state_get() < limit; state_put(state_get() + 1));
  return state_get();
}

int main(void) {
  fiber_setup();
  int32_t my_count = handle_count(0, count_to);
  int result = verify(my_count, count_to);
  fiber_teardown();
  return result;
}
