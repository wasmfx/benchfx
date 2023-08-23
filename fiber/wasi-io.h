#ifndef __WASI_IO_H
#define __WASI_IO_H

#include <stdint.h>
#include <wasi/api.h>
#include <unistd.h>

#define wasi_print(msg) do { \
    const uint8_t *msg_start = (uint8_t *)msg; \
    const uint8_t *msg_end = msg_start; \
    for (; *msg_end != '\0'; msg_end++) {} \
    __wasi_ciovec_t iov = {.buf = msg_start, .buf_len = msg_end - msg_start}; \
    size_t nwritten; \
    (void)__wasi_fd_write(STDOUT_FILENO, &iov, 1, &nwritten);   \
} while (0)
#define wasi_print_debug(msg) \
    wasi_print(__FILE__ ":" STRINGIZE(__LINE__) ": " msg "\n")
#endif
