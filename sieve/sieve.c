// An implementation of Sieve of Eratosthenes using fibers.

#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>

#include <wasm.h>

#include "parameters.h"

typedef void* filter_t;

extern
__wasm_import("impl", "filter_yield")
uint32_t filter_yield(bool);
extern
__wasm_import("impl", "filter_spawn")
filter_t filter_spawn(uint32_t prime);
extern
__wasm_import("impl", "filter_send")
bool filter_send(filter_t receiver, uint32_t candidate);
extern
__wasm_import("impl", "filter_shutdown")
void filter_shutdown(filter_t receiver);

__wasm_export("print_i32")
void print_i32(uint32_t i) {
  printf("%" PRIu32 "\n", i);
}

__wasm_export("print_cont")
void print_cont(void* i) {
  printf("%p\n", i);
}

__noinline
__wasm_export("filter")
void* filter(void *prime) {
  uint32_t my_prime = (uint32_t)(intptr_t)prime;
  printf("%" PRIu32 ": my prime\n", my_prime);
  uint32_t candidate = filter_yield(false);
  printf("%" PRIu32 ": C: %" PRIu32 "\n", my_prime, candidate);
  while (candidate != 0) {
    bool result = candidate % my_prime == 0 ? true : false;
    printf("%" PRIu32 ": divisible? %s\n", my_prime, result ? "true" : "false");
    candidate = filter_yield(result);
    printf("%" PRIu32 ": New candidate: %" PRIu32 "\n", my_prime, candidate);
  }
  return NULL;
}

__noinline
size_t sieve(uint32_t *primes, const size_t len) {
  size_t p = 0;
  uint32_t i = 2;
  filter_t *filters = malloc(sizeof(filter_t) * len);

  while (p < len) {
    bool divisible = false;
    for (size_t j = 0; j < p; j++) {
      printf("Sending %" PRIu32 ", %zu -> %d\n", i, j, (int)filters[j]);
      divisible = filter_send(filters[j], i);
      if (divisible) break;
    }
    if (!divisible) {
      primes[p] = i;
      printf("Spawning %" PRIu32 "\n", i);
      filter_t f = filter_spawn(i);
      printf("filter: %d\n", (int)f);
      filters[p++] = f;
    }
    i++;
  }

  // Clean up
  for (size_t i = 0; i < len; i++)
    filter_shutdown(filters[i]);
  free(filters);
  return p;
}

int main(void) {
  const size_t primes_len = sizeof(reference) / sizeof(uint32_t);
  uint32_t primes[primes_len];
  size_t num_primes = sieve(primes, primes_len);

  print_primes(primes, num_primes);
  int exit_code = verify(primes, num_primes, reference, primes_len);
  return exit_code;
}
