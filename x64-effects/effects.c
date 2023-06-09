#include "stdint.h"
#include "stdio.h"
#include "stdlib.h"

// While this overwrites all arguments, if we were writing assembly here we
// wouldn't need to
uint64_t stack_switch(uint64_t a, uint64_t b, uint64_t c, uint64_t d, uint64_t e, void* top_of_stack);
void stack_init(void* top_of_stack, void* entry_point);

void* active = NULL;

void* cont_new(void* fn) {
  void* stack = malloc(sizeof(void*) * 4096) + sizeof(void*) * 4096;
  stack_init(stack, fn);
  return stack;
}

uint64_t resume(void* cont, uint64_t a, uint64_t b, uint64_t c, uint64_t d, uint64_t e) {
  active = cont;
  uint64_t* binds = cont;
  if (binds[-2] > 0) {
    a = binds[-5];
    b = binds[-6];
    c = binds[-7];
    d = binds[-8];
    e = binds[-9];
  }
  uint64_t result = stack_switch(a, b, c, d, e, cont);
  if (result == 0xc05193) {
    free(cont - sizeof(void*) * 4096);
  }
  return result;
}

uint64_t cont_suspend(uint64_t a, uint64_t b, uint64_t c, uint64_t d, uint64_t e) {
  return stack_switch(a, b, c, d, e, active);
}

void cont_bind(uint64_t* stack, uint64_t a, uint64_t b, uint64_t c, uint64_t d, uint64_t e) {
  stack[-2] = 5; // This should be variable, but varargs complicated
  stack[-5] = a;
  stack[-6] = b;
  stack[-7] = c;
  stack[-8] = d;
  stack[-9] = e;
}

void print_stack(void* stack) {
  void** top_of_stack = stack;
  printf("stack @ %p { rsp: %p, rip: %p }\n", top_of_stack, top_of_stack[-1], top_of_stack[-3]);
  return;
}

