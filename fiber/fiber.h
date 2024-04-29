/** A basic fiber interface. **/
#ifndef __FIBER_H
#define __FIBER_H

#include "wasm.h"

/** The signature of a fiber entry point. **/
typedef void* (*fiber_entry_point_t)(void*);

/** The abstract type of a fiber object. **/
typedef struct fiber* fiber_t;

/** Allocates a new fiber with the default stack size. **/
extern
fiber_t fiber_alloc(fiber_entry_point_t entry);
/** Reclaims the memory occupied by a fiber object. **/
extern
void fiber_free(fiber_t fiber);

/** Yields control to its parent context. This function must be called
    from within a fiber context. **/
extern
void* fiber_yield(void *arg);

/** Possible status codes for `fiber_resume`. **/
typedef enum { FIBER_OK = 0, FIBER_YIELD = 1, FIBER_ERROR = 2 } fiber_result_t;

/** Resumes a given `fiber` with argument `arg`. **/
extern
void* fiber_resume(fiber_t fiber, void *arg, fiber_result_t *result);


/** Initializes fiber support. Must be called exactly once before using any of
    the other fiber_* functions. **/
extern
void fiber_setup();

/** Un-initializes fiber support. If fiber_initialize has ever beed called, then
    fiber_uninitialize must called prior to exiting the program. **/
extern
void fiber_teardown();

#endif
