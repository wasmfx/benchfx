#ifndef __ASYNCIFY_IMPORT_H
#define __ASYNCIFY_IMPORT_H

extern
__attribute__((__import_module__("asyncify"), __import_name__("start_unwind")))
void asyncify_start_unwind(int);

extern
__attribute__((__import_module__("asyncify"), __import_name__("stop_unwind")))
void asyncify_stop_unwind(void);

extern
__attribute__((__import_module__("asyncify"), __import_name__("start_rewind")))
void asyncify_start_rewind(int);

extern
__attribute__((__import_module__("asyncify"), __import_name__("stop_rewind")))
void asyncify_stop_rewind(void);

static const size_t STACK_SIZE = 4096;

typedef enum { YIELD = 0, RETURN = 1 } asyncify_event_t;

typedef struct asyncify_data {
  uint8_t* stack;
  uint8_t* stack_end;
  asyncify_event_t event;
  uint64_t num;
} asyncify_data;

asyncify_data* asyncify_allocate_stack(void);
void asyncify_free_stack(asyncify_data* metadata);
#endif
