// An implementation of Sieve of Eratosthenes using fibers.

#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>

#include <wasm.h>
#include <fiber.h>

#include "parameters.h"

typedef void* filter_t;

extern
__wasm_import("impl", "filter_spawn")
filter_t filter_spawn(uint32_t prime);
extern
__wasm_import("impl", "filter_send")
bool filter_send(filter_t receiver, uint32_t candidate);
extern
__wasm_import("impl", "filter_shutdown")
void filter_shutdown(filter_t receiver);

/* __noinline */
/* __wasm_export("filter") */
/* void* filter(void *prime) { */
/*   uint32_t my_prime = *((uint32_t*)prime); */
/*   printf("HERE\n"); */
/*   uint32_t candidate = filter_yield(false); */
/*   printf("THERE\n"); */
/*   while (candidate != 0) { */
/*     bool result = candidate % my_prime == 0 ? true : false; */
/*     printf("BOO\n"); */
/*     candidate = filter_yield(result); */
/*     printf("BAH\n"); */
/*   } */
/*   return NULL; */
/* } */

__noinline
size_t sieve(uint32_t *primes, const size_t len) {
  size_t p = 0;
  uint64_t i = 2;
  filter_t *filters = malloc(sizeof(filter_t) * len);

  while (p < len) {
    bool divisible = false;
    for (size_t j = 0; j < p; j++) {
      divisible = filter_send(filters[j], i);
      if (divisible) break;
    }
    if (!divisible) {
      primes[p] = i;
      filters[p++] = filter_spawn(i);
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
  fiber_setup();
  const size_t primes_len = sizeof(reference) / sizeof(uint32_t);
  uint32_t primes[primes_len];
  size_t num_primes = sieve(primes, primes_len);

  print_primes(primes, num_primes);
  int exit_code = verify(primes, num_primes, reference, primes_len);
  fiber_teardown();
  return exit_code;
}
