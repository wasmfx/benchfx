// Bespoke implementation of stateful counting.

#include <stdint.h>

#include "parameters.h"

__attribute__((noinline))
__attribute__((export_name("count")))
int32_t count(int32_t seed, const int32_t limit) {
  for (; seed < limit; seed++);
  return seed;
}

int main(void) {
  int32_t my_count = count(0, count_to);
  return verify(my_count, count_to);
}
