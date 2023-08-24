// Bespoke implementation of Sieve of Eratosthenes

#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>

#include "parameters.h"

size_t sieve(uint32_t *primes, size_t len) {
  size_t p = 0;
  uint32_t i = 2;
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
  const size_t primes_len = sizeof(reference) / sizeof(uint32_t);
  uint32_t primes[primes_len];
  size_t num_primes = sieve(primes, primes_len);

  print_primes(primes, num_primes);
  int exit_code = verify(primes, num_primes, reference, primes_len);
  return exit_code;
}
