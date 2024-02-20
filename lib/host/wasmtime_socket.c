//
// Host socket bindings for an embedded Wasmtime guest.
//

#include <assert.h>
#include <errno.h>
#include <netinet/in.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdint.h>
#include <strings.h>
#include <sys/socket.h>
#include <unistd.h>

#include <wasm.h>
#include <wasmtime.h>
#include <host/wasmtime_socket.h>
#include <host/wasmtime_utils.h>

#define WRITE_ERRNO(CALLER, ERRNO_ARG) {                           \
  int32_t err_offset = int32_t_of_wasmtime_val_t(ERRNO_ARG);      \
  int64_t err = errno;                                                  \
  wasmtime_extern_t memory_extern = { .kind = WASMTIME_EXTERN_MEMORY }; \
  if (!WASMTIME_CALLER_EXPORT_GET(caller, "memory", &memory_extern))    \
    return WASMTIME_TRAP_NEW("[" CALLER "] cannot load memory");       \
  uint8_t *mem_ptr = wasmtime_memory_data(wasmtime_caller_context(caller), &memory_extern.of.memory); \
  *(mem_ptr+err_offset) = err; /* TODO(dhil): Bounds checking? */ \
}

// Link state.
static bool initialised = false;

// Signatures, functions, and externs
static wasm_functype_t *tcp_stream_socket_sig = NULL;
static wasmtime_func_t tcp_stream_socket_func;
static wasmtime_extern_t tcp_stream_socket_extern;

static wasm_functype_t *listen_sig = NULL;
static wasmtime_func_t listen_func;
static wasmtime_extern_t listen_extern;

static wasm_functype_t *accept_sig = NULL;
static wasmtime_func_t accept_func;
static wasmtime_extern_t accept_extern;

static wasm_functype_t *recv_sig = NULL;
static wasmtime_func_t recv_func;
static wasmtime_extern_t recv_extern;

static wasm_functype_t *send_sig = NULL;
static wasmtime_func_t send_func;
static wasmtime_extern_t send_extern;

static wasm_functype_t *close_sig = NULL;
static wasmtime_func_t close_func;
static wasmtime_extern_t close_extern;

// Free list
#define BITMAP_LEN (WASMTIME_MAX_GUEST_SOCKETS / sizeof(int) + 1)
static int bitmap[BITMAP_LEN];

static inline int32_t freelist_pop(void) {
  int ans;
  for (int i = 0; i < BITMAP_LEN; i++) {
    ans = ffs(~bitmap[i]);
    if (ans == 0) continue;
    else {
      ans -= 1;
      bitmap[i] = bitmap[i] ^ (1 << ans);
      int res = ans + i * sizeof(int);
      if (res < WASMTIME_MAX_GUEST_SOCKETS)
        return (int32_t)res;
      else
        return -2;
    }
  }
  return -1;
}

static inline void freelist_push(int32_t i) {
  int n = (int)i;
  int idx = n / sizeof(int);
  bitmap[idx] = bitmap[idx] ^ (1 << n);
}

// Guest sockets
struct guest_socket {
  int host_fd;
  struct sockaddr_in addr;
};

static struct guest_socket guest_sockets[WASMTIME_MAX_GUEST_SOCKETS];
static int32_t next = 0;

static inline int get_guest_socket(int32_t n, struct guest_socket *out) {
  if (n < 0 || n >= next) return -1;

  out = &guest_sockets[n];
  return 0;
}

static inline int32_t alloc_guest_socket(struct guest_socket sock) {
  int free_slot = freelist_pop();
  if (free_slot == -1) {
    free_slot = next++;
  } else if (free_slot == -2) {
    return -1;
  } else {
    // OK
  }

  guest_sockets[free_slot] = sock;
  return 0;
}

// sig : i32 -> i32
wasm_trap_t* host_tcp_stream_socket(void *env, wasmtime_caller_t *caller,
                                    const wasmtime_val_t *args, size_t nargs,
                                    wasmtime_val_t *results, size_t nresults) {
  assert(nargs == 2);
  assert(nresults == 1);

  // Unpack the argument.
  int32_t port = int32_t_of_wasmtime_val_t(args[0]);

  // Create the host TCP socket.
  struct guest_socket sock;

  sock.host_fd = socket(AF_INET, SOCK_STREAM, 0);
  if (sock.host_fd < 0) return WASMTIME_TRAP_NEW("Could not create socket");

  sock.addr.sin_family = AF_INET;
  sock.addr.sin_port = htons(port);
  sock.addr.sin_addr.s_addr = htonl(INADDR_ANY);

  int opt_val = 1;
  setsockopt(sock.host_fd, SOL_SOCKET, SO_REUSEADDR, &opt_val, sizeof(opt_val));

  // Attempt to bind the socket.
  if (bind(sock.host_fd, (struct sockaddr *) &sock.addr, sizeof(sock.addr)) < 0)
    return WASMTIME_TRAP_NEW("Could not bind socket");

  // Create guest file descriptor.
  int32_t guest_fd = alloc_guest_socket(sock);
  if (guest_fd < 0)
    return WASMTIME_TRAP_NEW("Could not allocate guest socket");

  // Pack and return the result.
  results[0] = wasmtime_val_t_of_int32_t(guest_fd);
  return NULL;
}

// sig : i32 i32 (out i32) -> i32
wasm_trap_t* host_listen(void *env, wasmtime_caller_t *caller,
                         const wasmtime_val_t *args, size_t nargs,
                         wasmtime_val_t *results, size_t nresults) {
  assert(nargs == 3);
  assert(nresults == 1);

  // Unpack the arguments.
  int32_t guest_fd = int32_t_of_wasmtime_val_t(args[0]);
  int32_t backlog = int32_t_of_wasmtime_val_t(args[1]);

  // Get host socket.
  struct guest_socket sock;
  if (!get_guest_socket(guest_fd, &sock))
    return WASMTIME_TRAP_NEW("Invalid socket file descriptor");

  // Perform the system call.
  int ans = listen(sock.host_fd, (int)backlog);
  if (ans < 0) {
    WRITE_ERRNO("host_listen", args[2]);
  }

  // Pack and return the result.
  results[0] = wasmtime_val_t_of_int32_t((int32_t)ans);
  return NULL;
}

// sig : i32 (out i32) -> i32
wasm_trap_t* host_accept(void *env, wasmtime_caller_t *caller,
                         const wasmtime_val_t *args, size_t nargs,
                         wasmtime_val_t *results, size_t nresults) {
  assert(nargs == 2);
  assert(nresults == 1);

  // Unpack the argument.
  int32_t guest_fd = int32_t_of_wasmtime_val_t(args[0]);

  // Get host socket.
  struct guest_socket sock;
  if (!get_guest_socket(guest_fd, &sock))
    return WASMTIME_TRAP_NEW("Invalid guest file descriptor");

  // Perform the system call.
  struct sockaddr_in client_addr;
  socklen_t client_len = sizeof(client_addr);
  int ans = accept(sock.host_fd, (struct sockaddr *)&client_addr, &client_len);

  if (ans < 0) {
    // Error
    // Pack and return the result.
    WRITE_ERRNO("host_accept", args[1]);
    results[0] = wasmtime_val_t_of_int32_t((int32_t)ans);
    return NULL;
  } else {
    // Success
    // Allocate a new guest socket.
    struct guest_socket client_sock = { .host_fd = ans, .addr = client_addr };
    int32_t res = alloc_guest_socket(client_sock);
    if (res < 0) return WASMTIME_TRAP_NEW("Failed to allocate guest socket");
    results[0] = wasmtime_val_t_of_int32_t(res);
    return NULL;
  }
}

// sig : i32 i32 i32 i32 -> i32
wasm_trap_t* host_recv(void *env, wasmtime_caller_t *caller,
                       const wasmtime_val_t *args, size_t nargs,
                       wasmtime_val_t *results, size_t nresults) {
  return WASMTIME_TRAP_NEW("TODO");
}

// sig : i32 i32 i32 i32 -> i32
wasm_trap_t* host_send(void *env, wasmtime_caller_t *caller,
                       const wasmtime_val_t *args, size_t nargs,
                       wasmtime_val_t *results, size_t nresults) {
  return WASMTIME_TRAP_NEW("TODO");
}

// sig : i32 -> i32
wasm_trap_t* host_close(void *env, wasmtime_caller_t *caller,
                       const wasmtime_val_t *args, size_t nargs,
                       wasmtime_val_t *results, size_t nresults) {
  assert(nargs == 1);
  assert(nresults == 1);

  // Unpack the argument.
  int32_t guest_fd = int32_t_of_wasmtime_val_t(args[0]);

  // Get the guest descriptor.
  struct guest_socket sock;
  if (get_guest_socket(guest_fd, &sock) < 0)
    return WASMTIME_TRAP_NEW("[host_close] invalid guest file descriptor");

  // Perform the system call.
  int ans = close(sock.host_fd);

  // Pack and return the result.
  results[0] = wasmtime_val_t_of_int32_t((int32_t)ans);
  return NULL;
}

static inline wasm_functype_t* wasm_functype_new_4_1( wasm_valtype_t *arg1
                                                    , wasm_valtype_t *arg2
                                                    , wasm_valtype_t *arg3
                                                    , wasm_valtype_t *arg4
                                                    , wasm_valtype_t *res ) {
  wasm_valtype_t* ps[4] = {arg1, arg2, arg3, arg4};
  wasm_valtype_t* rs[1] = {res};
  wasm_valtype_vec_t params, results;
  wasm_valtype_vec_new(&params, 4, ps);
  wasm_valtype_vec_new(&results, 1, rs);
  return wasm_functype_new(&params, &results);
}

wasmtime_error_t* wasmtime_socket_linker_define(wasmtime_linker_t *linker, wasmtime_context_t *context) {
  assert(!initialised);
  wasmtime_error_t *error = NULL;

  tcp_stream_socket_sig = wasm_functype_new_1_1(wasm_valtype_new_i32(), wasm_valtype_new_i32());
  wasmtime_func_new(context, tcp_stream_socket_sig, host_tcp_stream_socket, NULL, NULL, &tcp_stream_socket_func);
  tcp_stream_socket_extern = (wasmtime_extern_t){ .kind = WASMTIME_EXTERN_FUNC, .of = { .func = tcp_stream_socket_func } };
  error = WASMTIME_LINKER_DEFINE(linker, context, "socket", "tcp_stream_socket", &tcp_stream_socket_extern);
  if (error != NULL) return error;

  listen_sig = wasm_functype_new_3_1(wasm_valtype_new_i32(), wasm_valtype_new_i32(), wasm_valtype_new_i32(), wasm_valtype_new_i32());
  wasmtime_func_new(context, listen_sig, host_listen, NULL, NULL, &listen_func);
  listen_extern = (wasmtime_extern_t){ .kind = WASMTIME_EXTERN_FUNC, .of = { .func = listen_func } };
  error = WASMTIME_LINKER_DEFINE(linker, context, "socket", "listen", &listen_extern);
  if (error != NULL) return error;

  accept_sig = wasm_functype_new_1_1(wasm_valtype_new_i32(), wasm_valtype_new_i32());
  wasmtime_func_new(context, accept_sig, host_accept, NULL, NULL, &accept_func);
  accept_extern = (wasmtime_extern_t){ .kind = WASMTIME_EXTERN_FUNC, .of = { .func = accept_func } };
  error = WASMTIME_LINKER_DEFINE(linker, context, "socket", "accept", &accept_extern);
  if (error != NULL) return error;

  recv_sig = wasm_functype_new_4_1(wasm_valtype_new_i32(), wasm_valtype_new_i32(), wasm_valtype_new_i32(), wasm_valtype_new_i32(), wasm_valtype_new_i32());
  wasmtime_func_new(context, recv_sig, host_recv, NULL, NULL, &recv_func);
  recv_extern = (wasmtime_extern_t){ .kind = WASMTIME_EXTERN_FUNC, .of = { .func = recv_func } };
  error = WASMTIME_LINKER_DEFINE(linker, context, "socket", "recv", &recv_extern);
  if (error != NULL) return error;

  send_sig = wasm_functype_new_4_1(wasm_valtype_new_i32(), wasm_valtype_new_i32(), wasm_valtype_new_i32(), wasm_valtype_new_i32(), wasm_valtype_new_i32());
  wasmtime_func_new(context, send_sig, host_send, NULL, NULL, &send_func);
  send_extern = (wasmtime_extern_t){ .kind = WASMTIME_EXTERN_FUNC, .of = { .func = send_func } };
  error = WASMTIME_LINKER_DEFINE(linker, context, "socket", "send", &send_extern);
  if (error != NULL) return error;

  close_sig = wasm_functype_new_1_1(wasm_valtype_new_i32(), wasm_valtype_new_i32());
  wasmtime_func_new(context, send_sig, host_send, NULL, NULL, &send_func);
  close_extern = (wasmtime_extern_t){ .kind = WASMTIME_EXTERN_FUNC, .of = { .func = close_func } };
  error = WASMTIME_LINKER_DEFINE(linker, context, "socket", "close", &send_extern);
  if (error != NULL) return error;

  initialised = true;
  return NULL;
}

void wasmtime_socket_teardown(void) {
  assert(initialised);
  wasm_functype_delete(tcp_stream_socket_sig);
  wasm_functype_delete(listen_sig);
  wasm_functype_delete(accept_sig);
  wasm_functype_delete(recv_sig);
  wasm_functype_delete(send_sig);
  wasm_functype_delete(close_sig);
  initialised = false;
}
