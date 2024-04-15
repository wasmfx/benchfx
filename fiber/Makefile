CONFIG=../make.config
include ${CONFIG}

.PHONY: all
all: example.wasm

example.wasm: example.pre.wasm
	$(ASYNCIFY) -o example.wasm example.pre.wasm

example.pre.wasm: example.c fiber_asyncify.c fiber.h wasi-io.h
	$(WASICC) $(WASICC_FLAGS) fiber_asyncify.c example.c -o example.pre.wasm

out/fiber_wasmfx.opt.wasm: fiber_wasmfx.c
	$(WASM_INTERP) -d -i fiber_wasmfx_imports.wat -o out/fiber_wasmfx_imports.wasm
	$(WASICC) $(WASICC_FLAGS) fiber_wasmfx.c -o out/fiber_wasmfx.pre.wasm
	$(WASM_INTERP) -u -d -i out/fiber_wasmfx.pre.wasm -o out/fiber_wasmfx.pre.wat

	$(WASMFX_MERGE) out/fiber_wasmfx_imports.wasm "fiber_wasmfx_imports" out/fiber_wasmfx.pre.wasm "fiber_wasmfx_pre" -S -o out/fiber_wasmfx.merged.wat
	$(WASMFX_AS) out/fiber_wasmfx.merged.wat -o out/fiber_wasmfx.merged.wasm
    # Check that merged .wasm validates
	$(WASM_INTERP) -d -i out/fiber_wasmfx.merged.wasm


	$(WASMFX_OPT) out/fiber_wasmfx.merged.wasm -S -o out/fiber_wasmfx.opt.wat
	$(WASMFX_AS) out/fiber_wasmfx.opt.wat -o out/fiber_wasmfx.opt.wasm
    # Check that optimized .wasm validates
	$(WASM_INTERP) -d -i out/fiber_wasmfx.opt.wasm

.PHONY: run
run: example.wasm
	$(WASMTIME) example.wasm

.PHONY: clean
clean:
	rm -f example.wasm example.pre.wasm fiber_wasmfx.wasm out/*.wasm out/.wat
