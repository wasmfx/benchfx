CC=clang-17
CFLAGS=--std=c17 -Wall -I ../include -I ../../wasmtime/crates/c-api/include -I ../../wasmtime/crates/c-api/wasm-c-api/include ../../wasmtime/target/release/libwasmtime.a -lpthread -ldl -lm -O3

.PHONY: all
all: ../lib/host/wasmtime_socket.c
	$(CC) ../lib/host/wasmtime_socket.c driver.c $(CFLAGS) -o driver

.PHONY: clean
clean:
	rm -f *.o
	rm -f driver
