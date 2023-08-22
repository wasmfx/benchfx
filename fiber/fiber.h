// A basic fiber library based on asyncify
#ifndef __FIBER_H
#define __FIBER_H

typedef void (*fiber_entry_point_t)(void);

typedef struct fiber* fiber_t;

fiber_t fiber_alloc(size_t stack_size, fiber_entry_point_t entry, void *local_data);
void fiber_free(fiber_t fiber);

void *fiber_get_local_data(void);
/* fiber_t fiber_self(void); */

void fiber_yield(void);
void fiber_resume(fiber_t fiber);

/* bool fiber_is_done(fiber_t); */

#endif
