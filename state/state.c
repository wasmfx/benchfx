// An abstract effectful implementation of stateful counting.

#include <stdint.h>
#include <fiber.h>

#include "../wasm_utils.h"
#include "parameters.h"


extern
__wasm_import__("impl", "state_get")
int32_t state_get(void);

extern
__wasm_import__("impl", "state_put")
void state_put(int32_t);

extern
__wasm_import__("impl", "handle_count")
int32_t handle_count(int32_t, const int32_t);

__noinline
__wasm_export__("count")
int32_t count(const int32_t limit) {
  for (; state_get() < limit; state_put(state_get() + 1));
  return state_get();
}

int main(void) {
  fiber_init();
  int32_t my_count = handle_count(0, count_to);
  int result = verify(my_count, count_to);
  fiber_finalize();
  return result;
}
