#ifndef __WASMFX_IMPORT_H
#define __WASMFX_IMPORT_H

extern
__attribute__((import_module("wasmfx_import"), import_name("wasmfx_yield")))
void wasmfx_yield(uint64_t num);

extern
__attribute__((import_module("wasmfx_import"), import_name("wasmfx_handle")))
uint64_t wasmfx_handle(uint32_t level, uint64_t num);
#endif
