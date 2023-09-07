// Asyncify fiber-based implementation of the abstract state operations.

#include <stdlib.h>
#include <stdint.h>

#include <fiber.h>

extern
__attribute__((import_module("env"), import_name("count")))
int32_t count(const int32_t);

typedef struct cmd {
  enum { GET, PUT } op;
  int32_t value;
} cmd_t;

__attribute__((noinline))
int32_t state_get(void) {
  cmd_t get = { GET, 0 };
  return (int32_t)fiber_yield(&get);
}

__attribute__((noinline))
void state_put(int32_t value) {
  cmd_t put = { PUT, value };
  (void)fiber_yield(&put);
}

__attribute__((noinline))
int32_t handle_count(int32_t value, const int32_t limit) {
  fiber_result_t status;
  fiber_t fiber = fiber_alloc((fiber_entry_point_t)count);
  void *result = fiber_resume(fiber, (void*)((intptr_t)limit), &status);
  while (status == FIBER_YIELD) {
    cmd_t *cmd = (cmd_t*)result;
    switch (cmd->op) {
    case GET:
      result = fiber_resume(fiber, (void*)((intptr_t)value), &status);
      break;
    case PUT:
      value = cmd->value;
      result = fiber_resume(fiber, NULL, &status);
      break;
    }
  }
  fiber_free(fiber);
  return value;
}

