BENCHMARK=sieve

include ../make.generic.config

DATASET_SIZE=8000

.PHONY: dataset
dataset: P-1000000.txt
	./gendata $(DATASET_SIZE) > primes.data
