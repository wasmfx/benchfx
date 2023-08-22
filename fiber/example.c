#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>
#include <string.h>

#include "fiber.h"

extern volatile int n;
volatile int k;

void* hello(void *arg) {
  printf("Hello %s\n", (char*)arg);
  //int num = 40;
  printf("Yielding\n");
  fiber_yield();
  printf("Resumed again\n");
  //printf("%d + %d = %d\n", num, *answer, num + *answer);
  return NULL;
}
__attribute__((noinline))
void hello_world(void) {
  volatile int m = n;
  if (n > 1) {
    printf("Hello World\n");
  } else {
    k = m;
  }
  fiber_yield();
  printf("Bye!\n");
}

int main(void) {
  char *world = "World";
  /* fiber_t fiber = fiber_alloc(4096, hello, NULL); */
  /* printf("Resuming fiber\n"); */
  /* fiber_resume(fiber, world); */
  /* printf("Fiber yielded\n"); */
  /* //printf("Received num = %" PRIu32 "\n", num); */
  /* //int my_num = 2; */
  /* //printf("Resuming fiber again\n"); */
  /* //fiber_resume(fiber, NULL); */

  /* if (!fiber_is_done(fiber)) { */
  /*   printf("Fiber is not finished!\n"); */
  /* } */
  /* fiber_free(fiber); */
  /* return 0; */

  fiber_t fiber = fiber_alloc(4096, hello_world, world);
  printf("Starting fiber.\n");
  fiber_resume(fiber);
  printf("Fiber yielded\n");
  fiber_resume(fiber);

  fiber_free(fiber);
  printf("%d\n", k);

  return 0;
}
