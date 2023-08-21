#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>

#include "asyncify_import.h"

static asyncify_data* unwind_stack = NULL;

asyncify_data* asyncify_allocate_stack(void) {
  uint8_t* stack = (uint8_t*)malloc(sizeof(uint8_t) * STACK_SIZE);
  uint8_t* stack_end = stack + STACK_SIZE;
  asyncify_data* metadata = malloc(sizeof(asyncify_data));
  *metadata = (asyncify_data) {
    stack,
    stack_end,
    1,
    0,
  };
  return metadata;
}

void asyncify_free_stack(asyncify_data* metadata) {
  free(metadata->stack);
  free(metadata);
}

/* __attribute__((noinline)) */
/* void asyncify_yield(void) { */
/*   if (unwind_stack->suspended) { */
/*     asyncify_stop_rewind(); */
/*   } else { */
/*     asyncify_start_unwind((int)unwind_stack); */
/*   } */
/* } */
