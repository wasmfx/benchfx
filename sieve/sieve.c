// An implementation of Sieve of Eratosthenes using fibers.

#include <stdlib.h>
#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>

#include "parameters.h"

typedef void* filter_t;

extern filter_t filter_spawn(uint64_t prime);
extern bool filter_send(filter_t receiver, uint64_t candidate);
extern void filter_shutdown(filter_t receiver);

size_t sieve(uint64_t *primes, const size_t len) {
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
  const size_t primes_len = sizeof(reference) / sizeof(uint64_t);
  uint64_t primes[primes_len];
  size_t num_primes = sieve(primes, primes_len);

  print_primes(primes, num_primes);
  int exit_code = verify(primes, num_primes, reference, primes_len);
  return exit_code;
}
