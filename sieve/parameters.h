#ifndef __SIEVE_PARAMETERS_H
#define __SIEVE_PARAMETERS_H

#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>

//#include <wasi-io.h>

// Generate data set with
// cat P-1000000.txt | awk -F "\"*,\"*" '{print $2}' | sed 's/$/\,/' > primes.data

const uint32_t reference[] = {
#include "primes.data"
};

int verify(const uint32_t *primes, size_t len, const uint32_t *primes_ref, size_t len_ref) {
  if (len != len_ref) {
    //printf("sizes differ (%lu != %lu)\n", len, len_ref);
    //wasi_print("sizes differ\n");
    return -1;
  }
  for (size_t i = 0; i < len; i++) {
    if (primes[i] != primes_ref[i]) {
      //printf("%" PRIu64 " != %" PRIu64 " (primes[%lu] != primes_ref[%lu])\n", primes[i], primes_ref[i], i, i);
      //wasi_print("Prime disagreement!\n");
      return -1;
    }
  }
  return 0;

}

#ifndef PRINT_PRIMES
#define PRINT_PRIMES 0
#endif

#if PRINT_PRIMES == 1
#define print_primes(primes, len) { \
  for (size_t i = 0; i < len; i++) \
    printf("%" PRIu64 " ", primes[i]); \
  printf("\n"); \
  }
#else
#define print_primes(_primes, _len) {}
#endif

#endif
