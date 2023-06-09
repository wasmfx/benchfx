all: wasmfx.wasm asyncify.wasm cps.wasm asyncifyO0.wasm

wasmfx.wat: so_many_coroutines.c wasmfx.pl
	# We need to export all the functions we want to not inline, because
	# clang-wasm/wasi-sdk seem to not respect noinline if we don't export
	# them! >:(
	# This is also asyncify's fault for requiring me to care about
	# inlining! It should be semantically unobservable!
	wasi-sdk-20.0-linux/bin/clang -O3 so_many_coroutines.c -o wasmfx.wasm -Wl,--allow-undefined,--export=a_coroutine
	wasm2wat wasmfx.wasm >wasmfx_import.wat
	raku wasmfx.pl <wasmfx_import.wat >wasmfx.wat

asyncify_import.wasm: so_many_coroutines.c asyncify.c
	wasi-sdk-20.0-linux/bin/clang -O3 so_many_coroutines.c asyncify.c -o asyncify_import.wasm -Wl,--allow-undefined,--export=first_resume,--export=resume_again,--export=suspend

asyncify.wasm: asyncify_import.wasm
	wasm-opt -O --asyncify asyncify_import.wasm -o asyncify.wasm

cps.wasm: so_many_coroutines_cps.c save_state.c
	wasi-sdk-20.0-linux/bin/clang -O3 so_many_coroutines_cps.c save_state.c -o cps.wasm

wasmfx.wasm: wasmfx.wat
	effect-handlers-wasm -d -i wasmfx.wat -o wasmfx.wasm

asyncifyO0.wasm: so_many_coroutines.c asyncify.c
	# Removed -O3, renamed output to avoid clash
	wasi-sdk-20.0-linux/bin/clang so_many_coroutines.c asyncify.c -o asyncify_importO0.wasm -Wl,--allow-undefined,--export=first_resume,--export=resume_again,--export=suspend
	# Renamed output, removed -O, renamed input (see above)
	wasm-opt --asyncify asyncify_importO0.wasm -o asyncifyO0.wasm

x64: so_many_coroutines.c effects.c stacks.S x64.c
	gcc -Wall -O3 -o x64 so_many_coroutines.c x64.c effects.c stacks.S

clean:
	rm wasmfx.wasm wasmfxO0.wasm wasmfx.wat wasmfx_import.wat asyncify.wasm asyncify_import.wasm cps.wasm asyncifyO0.wasm asyncify_importO0.wasm x64
