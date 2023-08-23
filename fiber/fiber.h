/** A basic fiber interface. **/
#ifndef __FIBER_H
#define __FIBER_H

/** The signature of a fiber entry point. **/
typedef void* (*fiber_entry_point_t)(void*);

/** The abstract type of a fiber object. **/
typedef struct fiber* fiber_t;

/** The default stack size is 4096 bytes. **/
#define FIBER_DEFAULT_STACK_SIZE ((size_t)4096)

/** Allocates a new fiber object, whose underlying stack has size
    `stack_size`, and with entry point `entry`, and fiber local data
    `local_data`. **/
fiber_t fiber_sized_alloc(size_t stack_size, fiber_entry_point_t entry, void *local_data);
/** Allocates a new fiber with the default stack size. **/
fiber_t fiber_alloc(fiber_entry_point_t entry, void *local_data);
/** Reclaims the memory occupied by a fiber object. **/
void fiber_free(fiber_t fiber);

/** Retrieves a pointer to the fiber local data. This function must be
    called from within a fiber context. */
void *fiber_get_local_data(void);

/** Yields control to its parent context. This function must be called
    from within a fiber context. **/
void* fiber_yield(void *arg);

/** Possible status codes for `fiber_resume`. **/
typedef enum { FIBER_OK, FIBER_ERROR } fiber_result_t;

/** Resumes a given `fiber` with argument `arg`. **/
void* fiber_resume(fiber_t fiber, void *arg, fiber_result_t *result);

/** Checks whether a given fiber is done. **/
bool fiber_is_done(fiber_t);
#endif
