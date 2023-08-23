#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>
#include <assert.h>
#include <string.h>

#include "fiber.h"
#include "wasi-io.h"

// "Hello world" example.
__attribute__((noinline))
void* knock_knock(void *msg) {
  wasi_print((char*)msg);
  msg = fiber_yield("Who's there?");
  char who[] = "XXXX who?";
  strncpy(who, (char*)msg, 4);
  wasi_print((char*)msg);
  msg = fiber_yield("Wasm who?");
  wasi_print((char*)msg);
  return NULL;
}

// Calculator example.
typedef enum { INIT, ADD, MUL, ANS } calc_op_t;

typedef struct calc_command {
  calc_op_t op;
  uint32_t number;
} calc_cmd_t;

__attribute__((noinline))
void* calc(void *init_cmd) {
  uint32_t result = 0;
  calc_cmd_t *cmd = (calc_cmd_t*)init_cmd;
  while (true) {
    switch (cmd->op) {
    case INIT:
      result = cmd->number;
      break;
    case ADD:
      result += cmd->number;
      break;
    case MUL:
      result *= cmd->number;
      break;
    case ANS:
      return (void*)result;
    }
    cmd = (calc_cmd_t*)fiber_yield((void*)result);
  }
}

// Main entry point.
int main(void) {
  fiber_result_t status;

  // Run "hello world" example.
  char *response;
  fiber_t door = fiber_alloc(knock_knock, NULL);
  char *responses[] = { "Knock! Knock!\n", "Wasm\n", "WebAssembly!\n" };

  for (int i = 0; i < sizeof(responses) / sizeof(char**); i++) {
    response = (char*)fiber_resume(door, responses[i], &status);
    assert(status == FIBER_OK);
    printf("%s\n", response);
  }

  response = (char*)fiber_resume(door, NULL, &status);
  assert(status == FIBER_ERROR);

  fiber_free(door);

  // Run calculator example.
  fiber_t calculator = fiber_alloc(calc, NULL);

  calc_op_t ops[] = {INIT, MUL, MUL, ADD, ADD, ANS};
  uint32_t numbers[] = {1, 4, 4, 32, 16, 0};
  uint32_t result = 0;

  for (int i = 0; i < sizeof(numbers) / sizeof(uint32_t); i++) {
    calc_cmd_t cmd = { .op = ops[i], .number = numbers[i] };
    result = (uint32_t)fiber_resume(calculator, &cmd, &status);
    switch (status) {
    case FIBER_OK:
      switch (ops[i]) {
      case INIT:
        printf("> %" PRIu32, result);
        break;
      case ADD:
        printf(" + %" PRIu32 "\n", numbers[i]);
        printf("> %" PRIu32 "", result);
        break;
      case MUL:
        printf(" * %" PRIu32 "\n", numbers[i]);
        printf("> %" PRIu32 "", result);
        break;
      case ANS:
        printf(" ans\n");
        break;
      }
      break;
    case FIBER_ERROR:
      printf("\n> fiber error!\n");
      fiber_free(calculator);
      return -1;
    }
  }

  fiber_free(calculator);

  return 0;
}
