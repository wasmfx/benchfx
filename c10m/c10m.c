// Asynchronous workload simulation

//#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
//#include <inttypes.h>

#include <wasm.h>

#include "parameters.h"

extern
__wasm_import("env", "async_worker_yield")
uint32_t async_worker_yield(uint32_t);

extern
__wasm_import("env", "alloc_async_worker")
void alloc_async_worker(uint32_t);

extern
__wasm_import("env", "resume_async_worker")
uint32_t resume_async_worker(uint32_t, uint32_t);

extern
__wasm_import("env", "free_async_worker")
void free_async_worker(uint32_t);


static
__noinline
void* as_stack_address(void* p) {
  return p;
}

static
__noinline
void* get_stack_top(void) {
  void* top = NULL;
  return as_stack_address(&top);
}

static
__noinline
void stack_use(long totalkb) {
  uint8_t* sp = (uint8_t*)get_stack_top();
  size_t page_size = 4096;
  size_t total_pages = ((size_t)totalkb*1024 + page_size - 1) / page_size;
  for (size_t i = 0; i < total_pages; i++) {
    volatile uint8_t b = *(sp - (i * page_size));
  }
}

__noinline
__wasm_export("async_worker")
void* async_worker(void *arg) {
  uint32_t kb = async_worker_yield((uint32_t)arg);
  stack_use(kb);
  return (void*)((intptr_t)1);
}

static
__noinline
uint32_t async_wl(void) {
  //printf("async_test1M set up...\n");
  //opaque_t* rs = (opaque_t*)malloc(sizeof(opaque_t) * active_conn);
  for (size_t i = 0; i < active_conn; i++) {
    alloc_async_worker((uint32_t)i);
  }

  //printf("run %" PRIu32 "M connections with %" PRIu32 " active at a time, each using %" PRIu32 "kb stack...\n", total_conn / 1000000, active_conn, stack_kb);
  uint32_t count = 0;
  for (size_t i = 0; i < total_conn; i++) {
    size_t j = i % active_conn;
    (void)resume_async_worker(j, stack_kb);  // TODO(dhil): soundness check: is the argument yielded?
    count += resume_async_worker(j, stack_kb); // do the work
    free_async_worker(j);
    alloc_async_worker(j); // and create a new one
  }
  for (size_t j = 0; j < active_conn; j++) {
    (void)resume_async_worker(j, stack_kb);  // TODO(dhil): soundness check: is the argument yielded?
    count += resume_async_worker(j, stack_kb); // do the work
    free_async_worker(j);
  }
  size_t total_kb = total_conn * stack_kb;
  double total_mb = (double)(total_conn * stack_kb) / 1024.0;
  //printf("total stack used: %.3fmb, count=%" PRIu32 "\n", total_mb, count);
  return count;
}

int main(void) {
  return verify(async_wl(), reference);
}

