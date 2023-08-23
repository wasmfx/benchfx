// Bespoke implementation of Sieve of Eratosthenes

#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>

#include "parameters.h"

size_t sieve(uint64_t *primes, size_t len) {
  size_t p = 0;
  uint64_t i = 2;
  while (p < len) {
    bool divisible = false;
    for (size_t j = 0; j < p; j++) {
      if (i % primes[j] == 0) {
        divisible = true;
        break;
      }
    }
    if (!divisible) {
      primes[p++] = i;
    }
    i++;
  }
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
