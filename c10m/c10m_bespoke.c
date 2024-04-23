// Asynchronous workload simulation

//#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
//#include <inttypes.h>

#include "parameters.h"

typedef struct sm {
  enum { NORMAL, YIELDING } state;
  uint32_t arg;
  uint32_t value;
} sm_t;

static sm_t workers[active_conn];
static sm_t *active_worker;

void* async_worker(void *);

uint32_t async_worker_yield(uint32_t arg) {
  switch (active_worker->state) {
  case 0:
    active_worker->value = arg;
    active_worker->state = YIELDING;
    return 0;
  case 1:
    active_worker->state = NORMAL;
    return active_worker->value;
  }
}

__attribute__((import_module("env"), import_name("alloc_async_worker")))
void alloc_async_worker(uint32_t key) {
  workers[key] = (struct sm){ NORMAL, 0, 0 };
}

extern
__attribute__((import_module("env"), import_name("resume_async_worker")))
uint32_t resume_async_worker(uint32_t key, uint32_t value) {
  active_worker = &workers[key];
  if (active_worker->state == YIELDING)
    active_worker->value = value;
  else
    active_worker->arg = value;

  uint32_t result = (uint32_t)async_worker((void*)((intptr_t)active_worker->arg));
  return active_worker->state == NORMAL ? result : active_worker->value;
}

extern
__attribute__((import_module("env"), import_name("free_async_worker")))
void free_async_worker(__attribute__ ((unused)) uint32_t _unused) {}

static
__attribute__((noinline))
void* as_stack_address(void* p) {
  return p;
}

static
__attribute__((noinline))
void* get_stack_top(void) {
  void* top = NULL;
  return as_stack_address(&top);
}

static
__attribute__((noinline))
void stack_use(long totalkb) {
  uint8_t* sp = (uint8_t*)get_stack_top();
  size_t page_size = 4096;
  size_t total_pages = ((size_t)totalkb*1024 + page_size - 1) / page_size;
  for (size_t i = 0; i < total_pages; i++) {
     __attribute__ ((unused)) volatile uint8_t b = *(sp - (i * page_size));
  }
}

__attribute__((noinline))
__attribute__((export_name("async_worker")))
void* async_worker(void *arg) {
  uint32_t kb;
  switch (active_worker->state) {
  case 0:
    kb = async_worker_yield((uint32_t)arg);
    if (active_worker->state == 1) return NULL;
  case 1:
    kb = async_worker_yield((uint32_t)arg);
    if (active_worker->state == 0) {
      stack_use(kb);
      return (void*)((intptr_t)1);
    }
  default:
    return NULL;
  }
}

static
__attribute__((noinline))
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
   __attribute__ ((unused)) size_t total_kb = total_conn * stack_kb;
   __attribute__ ((unused)) double total_mb = (double)(total_conn * stack_kb) / 1024.0;
  //printf("total stack used: %.3fmb, count=%" PRIu32 "\n", total_mb, count);
  return (uint32_t)count;
}

int main(void) {
  return verify(async_wl(), reference);
  return 0;
}

