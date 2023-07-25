CC=wasi-sdk-20.0-linux/bin/clang -O3
WT=../../wasmtime/target/release/wasmtime

all: wasmfx.cwasm asyncify.cwasm cps.cwasm

wasmfx.wat: so_many_coroutines.c wasmfx.pl
	# We need to export all the functions we want to not inline, because
	# clang-wasm/wasi-sdk seem to not respect noinline if we don't export
	# them! >:(
	# This is also asyncify's fault for requiring me to care about
	# inlining! It should be semantically unobservable!
	$(CC) so_many_coroutines.c -o wasmfx.wasm -Wl,--allow-undefined,--export=a_coroutine
	wasm2wat wasmfx.wasm >wasmfx_import.wat
	raku wasmfx.pl <wasmfx_import.wat >wasmfx.wat

asyncify_import.wasm: so_many_coroutines.c asyncify.c
	$(CC) so_many_coroutines.c asyncify.c -o asyncify_import.wasm -Wl,--allow-undefined,--export=first_resume,--export=resume_again,--export=suspend

asyncify.wasm: asyncify_import.wasm
	wasm-opt -O --asyncify asyncify_import.wasm -o asyncify.wasm

asyncify.cwasm: asyncify.wasm
	$(WT) compile asyncify.wasm

cps.wasm: so_many_coroutines_cps.c save_state.c
	$(CC) so_many_coroutines_cps.c save_state.c -o cps.wasm

cps.cwasm: cps.wasm
	$(WT) compile cps.wasm

wasmfx.wasm: wasmfx.wat
	../../spec/interpreter/wasm -d -i wasmfx.wat -o wasmfx.wasm

wasmfx.cwasm: wasmfx.wasm
	$(WT) compile --wasm-features exceptions,function-references,typed-continuations wasmfx.wasm

asyncifyO0.wasm: so_many_coroutines.c asyncify.c
	# Removed -O3, renamed output to avoid clash
	wasi-sdk-20.0-linux/bin/clang so_many_coroutines.c asyncify.c -o asyncify_importO0.wasm -Wl,--allow-undefined,--export=first_resume,--export=resume_again,--export=suspend
	# Renamed output, removed -O, renamed input (see above)
	wasm-opt --asyncify asyncify_importO0.wasm -o asyncifyO0.wasm

x64: so_many_coroutines.c effects.c stacks.S x64.c
	gcc -Wall -O3 -o x64 so_many_coroutines.c x64.c effects.c stacks.S

.PHONY: time-all
time-all: asyncify.cwasm cps.cwasm wasmfx.cwasm
	./time-all.sh

clean:
	rm -f wasmfx.cwasm wasmfx.wasm wasmfxO0.wasm wasmfx.wat wasmfx_import.wat asyncify.cwasm asyncify.wasm asyncify_import.wasm cps.cwasm cps.wasm asyncifyO0.wasm asyncify_importO0.wasm x64
