Using our patched tinygo, build a program:

```sh
../tinygo/tinygo build -target wasm coroutines.go
```

Running the program with a reference interpreter
------------------------------------------------

First, edit harness.wast to import the file you want (first line). Now, for
example, let me use my wasmfx that's next to this directory:

```sh
../effect-handlers-wasm/interpreter/wasm harness.wast
```

Files:
------------

coroutines.go <- a program that prints 1-10 using coroutines  
coroutines.wat <- the program, compiled for wasmfx using the below instructions  
effect-handlers.patch <- if you slightly modify coroutines.go, you may be able to get away with using this instead of manually "compiling"  
harness.wast <- for use with reference interpreter. currently runs coroutines.wat  
README.md <- you're reading me :)  
shell.nix <- if you use nix, run `nix-shell`. Otherwise, install the things listed in that file  
wasm_exec.js <- copied this from `../tinygo/targets/wasm_exec.js`  

How to compile patched-tinygo-wasm to wasmfx
============================================

My compiler is written in markdown. It runs on the "human" architecture only.

Remove JS/WASI dependencies:
----------------------------

Your program must use a dummy function to print:

```go
//go:noinline
func wrappedPrint(thething int32) {
    println(thething)
}
```

It has to actually print to prevent optimization. In the generated wat replace
$main.wrappedPrint with

```wat
  (func $main.wrappedPrint (param i32)
    (call $spectest_print (local.get 0)))
```

Remove the fd_write import and add

```wat
  (import "spectest" "print_i32" (func $spectest_print (param i32)))
```

And replace the fd_write call (in panic stuff) with unreachable

Use effect handlers to schedule!
--------------------------------

Remove the asyncify imports. Replace them with needed type declarations and
tags:

```wat
  (type $asyncify_resume_cont (cont REPLACE_EMPTY))
  (type $asyncify_call_indirect_cont (cont REPLACE_I32_I32))
  (tag $asyncify_effect)
```

Replace `REPLACE_EMPTY` with the index for (func) and `REPLACE_I32_I32` with
the index for (i32, i32) -> ().

Copy in this table-queueing implementation i've copied from the proposal. It
has to go after the current (table ...) definition!

```wat
  ;; Table as simple queue (keeping it simple, no ring buffer)
  (table $queue 0 (ref null $asyncify_resume_cont))
  (global $qdelta i32 (i32.const 10))
  (global $qback (mut i32) (i32.const 0))
  (global $qfront (mut i32) (i32.const 0))

  (func $queue-empty (result i32)
    (i32.eq (global.get $qfront) (global.get $qback))
  )

  (func $dequeue (result (ref null $asyncify_resume_cont))
    (local $i i32)
    (if (call $queue-empty)
      (then (return (ref.null $asyncify_resume_cont)))
    )
    (local.set $i (global.get $qfront))
    (global.set $qfront (i32.add (local.get $i) (i32.const 1)))
    (table.get $queue (local.get $i))
  )

  (func $enqueue (param $k (ref $asyncify_resume_cont))
    ;; Check if queue is full
    (if (i32.eq (global.get $qback) (table.size $queue))
      (then
        ;; Check if there is enough space in the front to compact
        (if (i32.lt_u (global.get $qfront) (global.get $qdelta))
          (then
            ;; Space is below threshold, grow table instead
            (drop (table.grow $queue (ref.null $asyncify_resume_cont) (global.get $qdelta)))
          )
          (else
            ;; Enough space, move entries up to head of table
            (global.set $qback (i32.sub (global.get $qback) (global.get $qfront)))
            (table.copy $queue $queue
              (i32.const 0)         ;; dest = new front = 0
              (global.get $qfront)  ;; src = old front
              (global.get $qback)   ;; len = new back = old back - old front
            )
            (table.fill $queue      ;; null out old entries to avoid leaks
              (global.get $qback)   ;; start = new back
              (ref.null $asyncify_resume_cont)      ;; init value
              (global.get $qfront)  ;; len = old front = old front - new front
            )
            (global.set $qfront (i32.const 0))
          )
        )
      )
    )
    (table.set $queue (global.get $qback) (local.get $k))
    (global.set $qback (i32.add (global.get $qback) (i32.const 1)))
  )
```

Use this queue for the scheduler:

```wat
  (func $runtime.scheduler
    (local i32)
    block  ;; label = @1
      loop  ;; label = @2
        i32.const 0
        i32.load8_u offset=65973
        ;; check schedulerDone (which gets set at end of main)
        br_if 1 (;@1;)
        ;; pop the queue and resume the continuation
        call $dequeue
        br_on_null 1
        (block $coroutine_suspend (param (ref $asyncify_resume_cont)) (result (ref $asyncify_resume_cont))
          (resume
            (tag $asyncify_effect $coroutine_suspend))
          ;; it suspended, so continue without re-enqueuing
          br 1)
        ;; re-enqeue the coroutine. tinygo makes this the coroutine's job, but
        ;; we make it the scheduler's job
        call $enqueue
        br 0 (;@2;)
      end
      unreachable
    end)
```

There's two identical schedulers. Call the first from the second:

```wat
  (func $runtime.minSched
    call $runtime.scheduler)
```

Replace the existing queue:

```wat
  (func $_*internal/task.Queue_.Pop (result i32) unreachable)
  (func $_*internal/task.Queue_.Push (param i32))
```

Delete `$_*internal/task.Task_.Resume`. Delete `tinygo_unwind`,
`tinygo_launch`, `tinygo_rewind` (all next to each other).

Replace Pause with a simple suspend:

```wat
  (func $internal/task.Pause
    suspend $asyncify_effect)
```

Find $internal/task.start. Starting with call `$enqueue_fn_args`, we *replace*
the call and the rest of the function with this code:

```wat
    (cont.new (type $asyncify_call_indirect_cont) (ref.func $asyncify_call_indirect))
    (cont.bind (type $asyncify_resume_cont))
    call $enqueue
```

This depends on a function that reifies call_indirect:

```wat
  (func $asyncify_call_indirect (param i32) (param i32)
    (call_indirect (type REPLACE_TYPE) (local.get 1) (local.get 0)))
```

Above we reference (type REPLACE_TYPE). Replace with the index of the (i32) ->
() from the top of the file.

Now you need to add the new `$asyncify_call_indirect` function to the elements
(elem ...) at the very bottom. To accomodate the new entry, expand the table
size, (table ...) just above it, in this case from 6 to 7 (adjust both numbers).

Running the result
------------------

Use the "Running the program with a reference interpreter" technique, and
import the wat directly (convenience and better error messages).
