#ifndef BENCHFX_WASM_UTILS_H
#define BENCHFX_WASM_UTILS_H

#define __noinline __attribute__((noinline))
#define __wasm_import(MODULE, NAME) __attribute__((import_module(MODULE),import_name(NAME)))
#define __wasm_export(NAME) __attribute__((export_name(NAME)))


#endif
