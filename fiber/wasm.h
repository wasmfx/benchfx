/** Useful Wasm definitions. */
#ifndef __WASM_H
#define __WASM_H

#define __wasm_import(MODULE, NAME) __attribute__((import_module(MODULE),import_name(NAME)))
#define __wasm_export(NAME) __attribute__((export_name(NAME)))
#define __noinline __attribute__((noinline))

#endif
