#include "stdint.h"
#include "stdio.h"
#include "stdlib.h"
#include "string.h"

void* cont_new(void* fn);
uint64_t resume(void* cont, uint64_t a, uint64_t b, uint64_t c, uint64_t d, uint64_t e);
uint64_t cont_suspend(uint64_t a, uint64_t b, uint64_t c, uint64_t d, uint64_t e);
void cont_bind(uint64_t* stack, uint64_t a, uint64_t b, uint64_t c, uint64_t d, uint64_t e);
void print_stack(void* stack);

void a_coroutine(void);

// Queue exactly matching queue from wasmfx
void** queue = NULL;
unsigned int qsize = 0;
unsigned int qfront = 0;
unsigned int qback = 0;
const unsigned int qdelta = 1000000;

void* dequeue(void) {
    if (qfront == qback) {
        return NULL;
    } else {
        unsigned int i = qfront;
        qfront = i + 1;
        return queue[i];
    }
}

void enqueue(void* stack) {
    if (qback == qsize) {
        if (qfront < qdelta) {
            // Space is below threshold, grow table instead
            qsize += 10;
            queue = realloc(queue, sizeof(void*) * qsize);
        } else {
            // Enough space, move entries up to head of table
            qback = qback - qfront;
            memmove(queue, queue + qfront, sizeof(void*) * qback);
            qfront = 0;
        }
    }
    queue[qback] = stack;
    qback += 1;
}

// Enqueues a_coroutine to the queue and returns the number of currently
// enqueued routines
unsigned int enqueue_a_coroutine(void) {
    void* cont = cont_new(a_coroutine);
    enqueue(cont);
    return qback - qfront;
}
// Pop a coroutine off of the queue, resume it, assume it returns, and return
// the number of currently enqueued routines
unsigned int pop_and_resume(void) {
    void* cont = dequeue();
    int result = resume(cont, 0, 0, 0, 0, 0);
    if (result == 0xC05193) {
    } else {
        // This has more work to do, put it at the end of the queue
        enqueue(cont);
    }
    return qback - qfront;
}
// Suspend to the coroutine tag with no values
void suspend(void) {
    cont_suspend(0, 0, 0, 0, 0);
}
