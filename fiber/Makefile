CONFIG=../make.config
include ${CONFIG}

.PHONY: all
all: example.wasm

example.wasm: example.pre.wasm
	$(ASYNCIFY) -o example.wasm example.pre.wasm

example.pre.wasm: example.c fiber_asyncify.c fiber.h wasi-io.h
	$(WASICC) $(WASICC_FLAGS) fiber_asyncify.c example.c -o example.pre.wasm

.PHONY: run
run: example.wasm
	$(WASMTIME) example.wasm

.PHONY: clean
clean:
	rm -f example.wasm example.pre.wasm
