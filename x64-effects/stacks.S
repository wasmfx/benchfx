// Adapted from wasmtime/crates/fiber/src/unix/x86_64.rs
.intel_syntax noprefix

.global stack_switch, stack_init

// We're going to support passing up to FIVE values and ignore stack-passed values
// System V amd64 ABI:
// rdi, rsi, rdx, rcx, r8, r9
// Floats (TODO): xmm0-xmm7
// Excess arguments (NOT SUPPORTED): stack
// i have no idea what a chain pointer (r10) is
// CALLEE SAVES: rbx, rsp, rbp, r12-r15
// we want to not have to save all of these, so we're going to ask cranelift to
// be smart about it, so i'm removing the old pessimistic saves

// We're not going to support multi-value return (for now)
// So return is in rax / rdx (float, TODO: xmm0 / xmm1)

// STACK MEMORY FORMAT:
// 0xb000 +-----------------------+  <- top of stack
//        | saved rsp             |  <- self when suspended, parent when running
// 0xaff8 +-----------------------+
//        | bind count            |
// 0xaff0 +-----------------------+  <- 16-byte aligned
//        | entry point           |  <- temporary until started
// 0xafe8 +-----------------------+
//        | stack_start[rip]      |  <- temporary until started
// 0xafe0 +-----------------------+  <- initial rsp
//        ~        ...            ~  <- actual native stack space to use
//        | rip WITHIN stack      |
//        +-----------------------+  <- rsp when suspended
//        | free                  |
//        ~        ...            ~
// 0x???? +-----------------------+

// A WORD OF CAUTION
//
// This entire file basically needs to be kept in sync with itself. It's not
// really possible to modify just one bit of this file without understanding
// all the other bits. Documentation tries to reference various bits here and
// there but try to make sure to read over everything before tweaking things!

// stack to switch to is in r9
// arguments to the function are in rdi, ..., r8
stack_switch:
  // Swap saved rsp from memory
  mov rax, -0x08[r9]
  mov -0x08[r9], rsp
  mov rsp, rax

  // This is not a simple return!
  // Note that the rip value on the stack corresponds to code
  // executing after/during execution of the the suspend instruction
  // By executing ret, we don't return to OUR caller, we return to THAT code
  // The initial ret value is set up by stack_init
  ret

// top of stack: rdi
// entry point: rsi
stack_init:
  // We need to initialize the stack with initial rip and rsp,
  // and our entry point for stack_start

  // Note the first 16 bytes of stack are reserved for metadata, so we start
  // storing values beneath that.
  movq -0x10[rdi], 0 // Initialize the bind count to 0

  // Entry point for stack_start
  // - Stored below initial rip
  // - Provided by caller (rsi)
  mov -0x18[rdi], rsi

  // Initial rip:
  // - Stored just below header
  // - Points to stack_start, relative to rip (??) so we can "ret" to it
  lea rax, stack_start[rip]
  mov -0x20[rdi], rax
  
  // Initial rsp:
  // - Stored just below top of stack
  // - Points just below saved rip (same address stored above)
  lea rax, -0x20[rdi]
  mov -0x08[rdi], rax

  // This is a normal return as this is a fairly normal function
  ret

// TODO: DWARF nonsense!
// From old code:
// If you're curious a decent introduction to CFI things and unwinding is at
// https://www.imperialviolet.org/2017/01/18/cfi.html

// This is a pretty special function that has no real signature. Its use is to
// be the "base" function of all stacks. This entrypoint is used in
// `stack_init` to bootstrap the execution of a new stack.
stack_start:
  // The `stack_init` routine arranged the various values to be
  // materialized into the registers used here. Our job is to then move
  // the values into the ABI-defined registers and call the entry-point.
  pop rax
  call rax

  // When we return we need to switch back to our parent! We signal return with
  // a sentinel value
  // rsp is currently immediately after stack_start, because we popped our
  // saved entry point and the call returned
  // stack_switch expects stack in r9
  mov rsp, 0x08[rsp]
  mov rax, 0xc05193

  // Stacks are one-shot, so this is now dead!
  ret

