CONFIG=../make.config
include ${CONFIG}

.PHONY: all
all: example.wasm

example.wasm: example.pre.wasm
	$(WASM_OPT) -O --asyncify -o example.wasm example.pre.wasm

example.pre.wasm: example.c fiber.c fiber.h wasi-io.h
	$(WASICC) $(WASICC_FLAGS) fiber.c example.c -o example.pre.wasm

.PHONY: run
run: example.wasm
	$(WASMTIME) example.wasm

.PHONY: clean
clean:
	rm -f example.wasm example.pre.wasm

