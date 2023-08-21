#include <stdlib.h>
#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>

extern
__attribute__((__import_module__("asyncify"), __import_name__("start_unwind")))
void asyncify_start_unwind(int);

extern
__attribute__((__import_module__("asyncify"), __import_name__("stop_unwind")))
void asyncify_stop_unwind(void);

extern
__attribute__((__import_module__("asyncify"), __import_name__("start_rewind")))
void asyncify_start_rewind(int);

extern
__attribute__((__import_module__("asyncify"), __import_name__("stop_rewind")))
void asyncify_stop_rewind(void);

extern uint64_t skynet(uint32_t, uint64_t);

static const size_t STACK_SIZE = 4096;

typedef struct asyncify_stack {
  uint8_t* stack;
  uint8_t* stack_end;
  bool is_yielding;
  uint64_t yield_value;
} asyncify_stack;

static volatile asyncify_stack* unwind_stack = NULL;

asyncify_stack* asyncify_allocate_stack(void) {
  uint8_t* stack = (uint8_t*)malloc(sizeof(uint8_t) * STACK_SIZE);
  uint8_t* stack_end = stack + STACK_SIZE;
  asyncify_stack* metadata = malloc(sizeof(asyncify_stack));
  *metadata = (asyncify_stack) {
    stack,
    stack_end,
    false,
    0,
  };
  return metadata;
}

void asyncify_free_stack(asyncify_stack* metadata) {
  free(metadata->stack);
  free(metadata);
}

__attribute__((noinline))
void yield(uint64_t value) {
  if (!unwind_stack->is_yielding) {
    unwind_stack->is_yielding = true;
    unwind_stack->yield_value = value;
    asyncify_start_unwind((int)unwind_stack);
  } else {
    unwind_stack->is_yielding = false;
    unwind_stack->yield_value = 0;
    asyncify_stop_rewind();
  }
}

__attribute__((noinline))
uint64_t handle(uint32_t level, uint64_t num) {
  uint64_t result = 0;
  volatile asyncify_stack *prev = unwind_stack;
  asyncify_stack *my_stack = asyncify_allocate_stack();
  unwind_stack = my_stack;

  result = skynet(level, num);
  asyncify_stop_unwind();
  while (my_stack->is_yielding) {
    result += my_stack->yield_value;
    asyncify_start_rewind((int)my_stack);
    skynet(level, num); // Discard dummy value.
  }

  asyncify_free_stack(my_stack);
  unwind_stack = prev;
  return result;
}
