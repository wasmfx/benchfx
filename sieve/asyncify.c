#include <stdlib.h>
#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>

#include <fiber.h>

static void* filter(void *prime) {
  uint64_t my_prime = *((uint64_t*)prime);
  uint64_t *candidate = (uint64_t*)fiber_yield(NULL);
  while (*candidate != 0) {
    bool result = *candidate % my_prime == 0 ? true : false;
    candidate = (uint64_t*)fiber_yield((void*)result);
  }
  return NULL;
}

fiber_t filter_spawn(uint64_t prime) {
  fiber_result_t status;
  fiber_t fiber = fiber_alloc((fiber_entry_point_t)filter, NULL);
  fiber_resume(fiber, &prime, &status); // Discard NULL result.
  return fiber;
}

bool filter_send(fiber_t receiver, uint64_t candidate) {
  fiber_result_t status;
  return (bool)fiber_resume(receiver, &candidate, &status);
}

void filter_shutdown(fiber_t receiver) {
  fiber_result_t status;
  uint64_t z = 0;
  fiber_resume(receiver, &z, &status);
  fiber_free(receiver);
}
