// fiber.h-based generic implementation of the abstract skynet operations.

#include <stdlib.h>
#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>

#include <fiber.h>

//#include <wasi-io.h>
#include <wasm.h>

// We cannot fit the result into a void* on wasm32; asyncify appears
// to be a bit bittle when passing stack addresses. So instead we use
// a global variable to pass the result.
static uint64_t result_slot;

__noinline
__wasm_export("yield")
void yield(uint64_t value) {
  result_slot = value;
  fiber_yield(NULL);
  //wasi_print("\0"); // TODO(dhil): This statement seemingly prevents
                      // asyncify from corrupting its own state.
                      // Doesn't seem to be necessary anymore since
                      // binaryen version 116 (more testing
                      // required). Removing this significantly alters
                      // the generated code.
}

extern
__noinline
__wasm_import("benchmark", "skynet")
uint64_t skynet(uint32_t, uint64_t);

struct skynet_args {
  uint32_t level;
  uint64_t num;
  uint64_t result;
};

static void* run_skynet(struct skynet_args *args) {
  result_slot = skynet(args->level, args->num);
  return NULL;
}

__noinline
__wasm_export("handle")
uint64_t handle(uint32_t level, uint64_t num) {
  uint64_t result;
  fiber_result_t status;
  fiber_t fiber = fiber_alloc((fiber_entry_point_t)run_skynet);
  struct skynet_args args = { level, num, (uint64_t)0 };

  (void)fiber_resume(fiber, &args, &status);
  result = result_slot;
  // If yield was invoked, finish the residual fiber computation.
  if (status == FIBER_YIELD)
    (void)fiber_resume(fiber, NULL, &status); // discards the dummy value
  fiber_free(fiber);
  return result;
}
