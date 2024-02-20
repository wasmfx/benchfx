//
// Host socket bindings for an embedded Wasmtime guest.
//

#ifndef WASMFXTIME_HOST_SOCKET_H
#define WASMFXTIME_HOST_SOCKET_H

#include <host/wasmtime_utils.h>
#include <wasmtime.h>

#define WASMTIME_MAX_GUEST_SOCKETS 10000

DECLARE_WASMTIME_HOST_BINDING(host_tcp_stream_socket);
DECLARE_WASMTIME_HOST_BINDING(host_listen);
DECLARE_WASMTIME_HOST_BINDING(host_accept);
DECLARE_WASMTIME_HOST_BINDING(host_recv);
DECLARE_WASMTIME_HOST_BINDING(host_send);

wasmtime_error_t* wasmtime_socket_linker_define(wasmtime_linker_t *linker, wasmtime_context_t *context);
void wasmtime_socket_teardown(void);

#endif
