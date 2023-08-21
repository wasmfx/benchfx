// Asyncify implementation of the Skynet benchmark.  This implementation
// does not use any form of coroutines.

#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>

#include "parameters.h"
#include "asyncify_import.h"

static volatile asyncify_data *stack = NULL;

uint64_t skynet(uint32_t level, uint64_t num);

__attribute__((noinline))
uint64_t asyncify_handle(uint32_t level, uint64_t num) {
  uint64_t result = 0;
  volatile asyncify_data *prev = stack;
  asyncify_data *my_stack = asyncify_allocate_stack();
  stack = my_stack;

  result = skynet(level, num);
  asyncify_stop_unwind();
  while (my_stack->event == YIELD) {
    result += my_stack->num;
    my_stack->num = 0;
    asyncify_start_rewind((int)my_stack);
    skynet(level, num); // Discard dummy value.
  }

  asyncify_free_stack(my_stack);
  stack = prev;
  return result;
}

__attribute__((noinline))
void asyncify_yield(uint64_t value) {
  static bool is_yielding = false;
  if (!is_yielding) {
    is_yielding = true;
    stack->num = value;
    stack->event = 0;
    asyncify_start_unwind((int)stack);
  } else {
    is_yielding = false;
    stack->num = 0;
    stack->event = 1;
    asyncify_stop_rewind();
  }
}

__attribute__((export_name("skynet")))
uint64_t skynet(uint32_t level, uint64_t num) {
  if (level == 0) {
    asyncify_yield(num);
    return -1; // dummy value
  }
  else {
    uint64_t lb = num * children_per_level;
    uint64_t ub = lb + children_per_level;
    uint64_t sum = 0;
    level--;
    for (uint64_t i = lb; i < ub; i++)
      sum += asyncify_handle(level, i);
    return sum;
  }
}

int main(void) {
  printf("%" PRIu64 "\n", skynet(num_levels, 0));
  return 0;
}
