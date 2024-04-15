// An implementation of the basic fiber interface using wasmfx continuations
#include <stdlib.h>

#include "fiber.h"
#include "wasm.h"

typedef size_t cont_table_index;
typedef void (*__funcref funcref_t)();

const size_t INITIAL_TABLE_CAPACITY = 1024;

size_t cont_table_capacity = INITIAL_TABLE_CAPACITY;
size_t cont_table_unused_size = INITIAL_TABLE_CAPACITY;

size_t* free_list = NULL;
size_t free_list_size = 0;


extern
__wasm_import("fiber_wasmfx_imports", "wasmfx_grow_cont_table")
void wasmfx_grow_cont_table(size_t);

extern
__wasm_import("fiber_wasmfx_imports", "wasmfx_indexed_cont_new")
void wasmfx_indexed_cont_new(fiber_entry_point_t, cont_table_index);

extern
__wasm_import("fiber_wasmfx_imports", "wasmfx_indexed_resume")
void* wasmfx_indexed_resume(size_t fiber_index, void *arg, fiber_result_t *result);

extern
__wasm_import("fiber_wasmfx_imports", "wasmfx_suspend")
void* wasmfx_suspend(void *arg);


size_t wasmfx_acquire_table_index() {
  size_t table_index;
  if (cont_table_unused_size > 0) {
    // There is an entry in the continuation table that has not been used so far.
    table_index = cont_table_capacity - cont_table_unused_size;
    cont_table_unused_size--;
  } else if (free_list_size > 0) {
      // We pop an element from the free list stack
      table_index = free_list[free_list_size - 1];
      free_list_size--;
  } else {
      // We have run out of table entries:
      // Ask wasm to grow the table, and we grow the free_list ourselves.
      table_index = cont_table_capacity;
      cont_table_unused_size = cont_table_capacity - 1;
      wasmfx_grow_cont_table(cont_table_capacity);
      cont_table_capacity *= 2;
      free(free_list);
      free_list = malloc(sizeof(size_t) * cont_table_capacity);
  }
  return table_index;
}

void wasmfx_release_table_index(size_t table_index) {
  free_list[free_list_size] = table_index;
  free_list_size++;
}


__wasm_export("fiber_alloc")
fiber_t fiber_alloc(fiber_entry_point_t entry) {
  size_t table_index = wasmfx_acquire_table_index();
  wasmfx_indexed_cont_new(entry, table_index);

  return (void*) table_index;
}

__wasm_export("fiber_free")
void fiber_free(fiber_t fiber) {
  size_t table_index = (size_t) fiber;

  // NOTE: Currently, fiber stacks are deallocated only when the continuation
  // returns. Thus, the only thing we can do here is releasing the table index.
  wasmfx_release_table_index(table_index);
}

__wasm_export("fiber_resume")
void* fiber_resume(fiber_t fiber, void *arg, fiber_result_t *result) {
  size_t fiber_index = (size_t) fiber;
  return wasmfx_indexed_resume(fiber_index, arg, result);
}

__wasm_export("fiber_yield")
void* fiber_yield(void *arg) {
  return wasmfx_suspend(arg);
}

__wasm_export("fiber_setup")
void fiber_setup() {
  free_list = malloc(INITIAL_TABLE_CAPACITY * sizeof(size_t));
}

__wasm_export("fiber_teardown") void fiber_teardown() {
  free(free_list);
}
