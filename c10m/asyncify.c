// Fiber-based implementation of the primitive operations.

#include <stdlib.h>
#include <stdint.h>
#include <fiber.h>
#include <wasm.h>

#include "parameters.h"

static fiber_t store[active_conn];

extern
__wasm_import("benchmark", "async_worker")
void* async_worker(void*);

__noinline
__wasm_export("alloc_async_worker")
void alloc_async_worker(uint32_t key) {
  store[key] = fiber_alloc(async_worker);
}

__noinline
__wasm_export("resume_async_worker")
uint32_t resume_async_worker(uint32_t key, uint32_t arg) {
  fiber_result_t status;
  return (uint32_t)fiber_resume(store[key], (void*)((intptr_t)arg), &status);
}

__noinline
__wasm_export("async_worker_yield")
uint32_t async_worker_yield(uint32_t arg) {
  return (uint32_t)fiber_yield((void*)((intptr_t)arg));
}

__noinline
__wasm_export("free_async_worker")
void free_async_worker(uint32_t key) {
  fiber_free(store[key]);
}
