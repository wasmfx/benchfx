// A basic fiber library based on asyncify

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>

#include "fiber.h"

// Asyncify imports
extern
__attribute__((__import_module__("asyncify"), __import_name__("start_unwind")))
void asyncify_start_unwind(void*);

extern
__attribute__((__import_module__("asyncify"), __import_name__("stop_unwind")))
void asyncify_stop_unwind(void);

extern
__attribute__((__import_module__("asyncify"), __import_name__("start_rewind")))
void asyncify_start_rewind(void*);

extern
__attribute__((__import_module__("asyncify"), __import_name__("stop_rewind")))
void asyncify_stop_rewind(void);

static volatile fiber_t active_fiber = NULL;

typedef enum { ACTIVE, YIELDING, DONE } fiber_state_t;

struct fiber_stack {
  uintptr_t *top;
  uintptr_t *end;
  //char *asyncify_buffer;
};
static_assert(sizeof(struct fiber_stack) == 8, "No padding allowed");

struct fiber {
  struct fiber_stack *stack;
  // Fiber state.
  fiber_state_t state;
  // Initial function to run on the fiber.
  fiber_entry_point_t fn;
  // Argument buffer
  /* void *arg; */
  // Fiber local data
  void *data;
};

static struct fiber_stack* fiber_stack_alloc(size_t stack_size) {
  //char *asyncify_buffer = malloc(sizeof(char) * stack_size);
  struct fiber_stack *stack = malloc(sizeof(struct fiber_stack));
  void *top = malloc(sizeof(uintptr_t) * stack_size);//&asyncify_buffer[0];
  void *end = ((char*)top) + stack_size;//&asyncify_buffer[stack_size];
  *stack = (struct fiber_stack) { top, end, /* asyncify_buffer */ };
  return stack;
}

fiber_t fiber_alloc(size_t stack_size, fiber_entry_point_t fn, void *local_data) {
  /* void* stack_start = (void*)malloc(sizeof(uintptr_t) * stack_size); */
  /* void* stack_end = stack_start + stack_size; */

  fiber_t fiber = (fiber_t)malloc(sizeof(struct fiber));
  fiber->stack = fiber_stack_alloc(stack_size);
  /* fiber->stack_start = stack_start; */
  /* fiber->stack_end = stack_end; */
  fiber->state = ACTIVE;
  fiber->fn = fn;
  /* fiber->arg = NULL; */
  fiber->data = local_data;
  return fiber;
}

void fiber_free(fiber_t fiber) {
  free((void*)fiber->stack->top);
  free((void*)fiber->stack);
  free(fiber);
}

volatile int n = 42;

__attribute__((always_inline))
void *fiber_get_local_data() {
  return active_fiber->data;
}

/* __attribute__((always_inline)) */
/* fiber_t fiber_self(void) { */
/*   return active_fiber; */
/* } */

__attribute__((noinline))
/* __attribute__((export_name("fiber_yield"))) */
void fiber_yield() {
  /* printf("Invoked yield\n"); */
  /* if (active_fiber->state != YIELDING) { */
  /*   /\* active_fiber->arg = arg; *\/ */
  /*   active_fiber->state = YIELDING; */
  /*   printf(">>> start unwinding\n"); */
  /*   if (active_fiber == NULL) { */
  /*     printf("active fiber is NULL!\n"); */
  /*   } */
  /*   asyncify_start_unwind(active_fiber->stack_start); */
  /*   printf(">>> not here"); */
  /*   //return NULL; // Dummy value */
  /* } else { */
  /*   printf("Returning\n"); */
  /*   /\* void *response = active_fiber->arg; *\/ */
  /*   /\* active_fiber->arg = NULL; *\/ */
  /*   active_fiber->state = ACTIVE; */
  /*   asyncify_stop_rewind(); */
  /*   return; */
  /* } */
  if (active_fiber->state == YIELDING) {
    asyncify_stop_rewind();
    active_fiber->state = ACTIVE;
  } else {
    printf("Start unwinding %p\n", active_fiber);
    active_fiber->state = YIELDING;
    asyncify_start_unwind(&active_fiber->stack);
  }
}


__attribute__((noinline))
/* __attribute__((export_name("fiber_resume"))) */
void fiber_resume(fiber_t fiber) {
  /* //volatile fiber_t prev = active_fiber; */
  /* active_fiber = fiber; */
  /* //void *result = NULL; */

  /* if (fiber->state == INIT) { */
  /*   printf(">>> init resume\n"); */
  /*   fiber->state = ACTIVE; */
  /*   fiber->fn(arg); */
  /*   fiber->state = DONE; */
  /*   //asyncify_stop_unwind(); */
  /*   //if (fiber->state == YIELDING) result = fiber->arg; */
  /*   //if (fiber->state == YIELDING) printf(">>> fiber yielded\n"); */
  /*   //else printf(">>> fiber finished\n"); */
  /* } else if (fiber->state == YIELDING || fiber->state == ACTIVE) { */
  /*   printf(">>> resuming\n"); */
  /*   asyncify_start_rewind(fiber->stack_start); */
  /*   fiber->fn(arg); */
  /*   fiber->state = DONE; */
  /*   //asyncify_stop_unwind(); */
  /*   //if (fiber->state == YIELDING) result = fiber->arg; */
  /* } else { */
  /*   printf(">>> FIBER IS FINISHED\n"); */
  /*   //result = NULL; */
  /* } */

  /* printf("HERE\n"); */

  /* asyncify_stop_unwind(); */

  /* //active_fiber = prev; */
  /* return NULL; */
  /* //return result; */

  if (fiber->state == DONE) return;

  volatile fiber_t prev = active_fiber;
  active_fiber = fiber;
  printf("Resuming %p\n", active_fiber);

  if (fiber->state == YIELDING)
    asyncify_start_rewind(&fiber->stack);

  fiber->fn();

  asyncify_stop_unwind();
  printf("After unwind\n");
  active_fiber = prev;
  /* return NULL; */
}

/* bool fiber_is_done(fiber_t fiber) { */
/*   return fiber->state == DONE; */
/* } */
