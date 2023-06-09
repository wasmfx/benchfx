#include "stdint.h"
#include "stdio.h"
#include "stdlib.h"

void* cont_new(void* fn);
uint64_t resume(void* cont, uint64_t a, uint64_t b, uint64_t c, uint64_t d, uint64_t e);
uint64_t cont_suspend(uint64_t a, uint64_t b, uint64_t c, uint64_t d, uint64_t e);
void cont_bind(uint64_t* stack, uint64_t a, uint64_t b, uint64_t c, uint64_t d, uint64_t e);

volatile int x = 2;

void my_subsequent(void) {
  uint64_t result = cont_suspend(0, 0, 0, 0, 0);
  printf("SHOULDN'T SEE THIS! %lx\n", result);
  x = 17;
  return;
}

void accepts_args(uint64_t a, uint64_t b, uint64_t c) {
  printf("got %ld %ld %ld\n", a, b, c);
}

void my_entry_point(void) {
  x = 13;
  void* child = cont_new(my_subsequent);
  uint64_t result = resume(child, 0, 0, 0, 0, 0);
  printf("(child) resume returned %lx\n", result);
  void* args = cont_new(accepts_args);
  cont_bind(args, 7, 8, 9, 0, 0);
  result = resume(args, 0, 0, 0, 0, 0);
  printf("(args) resume returned %lx\n", result);
  return;
}

uint64_t main(uint64_t argc, char** argv) {
  void* s = cont_new(my_entry_point);
  uint64_t result = resume(s, 0, 0, 0, 0, 0);
  printf("(main) resume returned %lx\n", result);
  void* t = cont_new(my_subsequent);
  result = resume(t, 0, 0, 0, 0, 0);
  printf("(suspends to main) resume returned %lx\n", result);
  printf("x = %d (should be 13)\n", x);
  return 0;
}
