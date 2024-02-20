//
// A collection of useful definitions for Wasmtime embedding.
//

#ifndef WASMFXTIME_HOST_UTILS_H
#define WASMFXTIME_HOST_UTILS_H

#include <stdint.h>

#include <wasm.h>
#include <wasmtime.h>

#define DECLARE_WASMTIME_HOST_BINDING(NAME) wasm_trap_t* NAME(void *env, wasmtime_caller_t *caller, \
                                                              const wasmtime_val_t *args, size_t nargs, \
                                                              wasmtime_val_t *results, size_t nresults)

__attribute__((unused))
static inline wasmtime_val_t wasmtime_val_t_of_int32_t(int32_t v) {
  return (wasmtime_val_t){ .kind = WASMTIME_I32, .of = { .i32 = v } };
}


__attribute__((unused))
static inline int32_t int32_t_of_wasmtime_val_t(wasmtime_val_t v) {
  assert(v.kind == WASMTIME_I32);
  return v.of.i32;
}

__attribute__((unused))
static inline wasmtime_val_t wasmtime_val_t_of_int64_t(int64_t v) {
  return (wasmtime_val_t){ .kind = WASMTIME_I64, .of = { .i64 = v } };
}


__attribute__((unused))
static inline int64_t int64_t_of_wasmtime_val_t(wasmtime_val_t v) {
  assert(v.kind == WASMTIME_I64);
  return v.of.i64;
}

#define WASMTIME_TRAP_NEW(CONST_MSG) wasmtime_trap_new(CONST_MSG, sizeof(CONST_MSG))

#define WASMTIME_LINKER_DEFINE(LINKER, CONTEXT, EXPORT_MODULE_NAME, EXPORT_ITEM_NAME, EXTERN_ITEM) \
  wasmtime_linker_define(LINKER, CONTEXT, EXPORT_MODULE_NAME, sizeof(EXPORT_MODULE_NAME), EXPORT_ITEM_NAME, sizeof(EXPORT_ITEM_NAME), EXTERN_ITEM)

#define WASMTIME_CALLER_EXPORT_GET(CALLER, EXPORT_NAME, EXTERN_ITEM) \
  wasmtime_caller_export_get(CALLER, EXPORT_NAME, sizeof(EXPORT_NAME), EXTERN_ITEM)

#endif
