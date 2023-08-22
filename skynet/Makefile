CONFIG=../make.config
include ${CONFIG}

.PHONY: all
all: skynet_bespoke.cwasm skynet_asyncify.cwasm skynet_wasmfx.cwasm

skynet_bespoke.wasm: skynet_bespoke.c
	$(WASICC) $(WASICC_FLAGS) -o skynet_bespoke.wasm skynet_bespoke.c

skynet_bespoke.cwasm: skynet_bespoke.wasm
	$(WASMTIME) compile -o skynet_bespoke.cwasm skynet_bespoke.wasm

skynet_asyncify.wasm: skynet.c asyncify.c
	$(WASICC) $(WASICC_FLAGS) -o skynet_asyncify.pre.wasm asyncify.c skynet.c
	$(WASM_OPT) -O --asyncify skynet_asyncify.pre.wasm -o skynet_asyncify.wasm

skynet_asyncify.cwasm: skynet_asyncify.wasm
	$(WASMTIME) compile -o skynet_asyncify.cwasm skynet_asyncify.wasm

## TODO(dhil): Currently skynet_wasmfx.wast is assembled by hand. We
## should have a tool do the assembling.
skynet_wasmfx.wasm: skynet_wasmfx.wast
	$(WASM_INTERP) -d -i skynet_wasmfx.wast -o skynet_wasmfx.wasm
	chmod +x skynet_wasmfx.wasm

skynet_wasmfx.cwasm: skynet_wasmfx.wasm
	$(WASMTIME) compile --wasm-features=exceptions,function-references,typed-continuations -o skynet_wasmfx.cwasm skynet_wasmfx.wasm

.PHONY: clean
clean:
	rm -f skynet_asyncify.pre.wasm skynet_asyncify.wasm skynet_bespoke.wasm skynet_wasmfx.wasm
	rm -f skynet_asyncify.cwasm skynet_bespoke.cwasm skynet_wasmfx.cwasm
