;; WasmFX implementation of the abstract sieve operations

(module $wasmfx_import
  (type $filter  (func (param i32) (result i32)))
  (type $cfilter (cont $filter))

  ;; (func $filter (import "main" "filter") (param i32) (result i32))

  (tag $init  (result i32))
  (tag $yield (param i32) (result i32))

  (global $next_slot (mut i32) (i32.const 0))
  (table $conts 8100 (ref null $cfilter)) ;; Update size to match dataset size.

  (elem declare func $filter)

  ;; (func $filter_yield (export "filter_yield") (param $result i32) (result i32)
  ;;   (suspend $yield (local.get $result)))

  ;; The filter function
  (func $filter (export "filter") (param $my_prime i32) (result i32)
    (local $divisible i32)
    (local $candidate i32)
    (local.set $candidate (suspend $init)) ;; retrieve the first candidate number.
    (block $end
      (loop $while
        (if (i32.eq (local.get $candidate) (i32.const 0))
          (then (br $end))
          (else))
        (local.set $divisible (i32.eqz
                                  (i32.rem_u
                                    (local.get $candidate)
                                    (local.get $my_prime))))
        (local.set $candidate (suspend $yield (local.get $divisible))) ;; communicate the result and retrieve the next candidate.
        (br $while)
      ) ;; loop
    ) ;; end
    (return (i32.const 0)))
  ;; filter_spawn
  (func $filter_spawn (export "filter_spawn") (param $prime i32) (result i32)
    (local $fiber_idx i32)
    (local $fiber (ref $cfilter))
    (local.set $fiber (cont.new $cfilter (ref.func $filter)))
    (block $on_init (result (ref $cfilter))
      (resume $cfilter (tag $init $on_init)
                       (local.get $prime)
                       (local.get $fiber))
      (unreachable)
    ) ;; on_init [ (ref $cfilter) ]
    (local.set $fiber)
    ;; store new continuation
    ;; first check whether there is sufficient space left.
    (if (i32.lt_u (global.get $next_slot) (table.size $conts))
      (then)
      (else (drop ;; double the size of the table.
             (table.grow $conts (ref.null $cfilter)
                                (i32.mul (table.size $conts) (i32.const 2))))))
    (local.set $fiber_idx (global.get $next_slot))
    (table.set $conts (local.get $fiber_idx) (local.get $fiber))
    (global.set $next_slot (i32.add (global.get $next_slot) (i32.const 1)))
    (return (local.get $fiber_idx)) ;; return fiber index
  )
  ;; filter_send
  (func $filter_send (export "filter_send") (param $fiber_idx i32) (param $candidate i32) (result i32)
    (local $next_k (ref $cfilter))
    (block $on_yield (result i32 (ref $cfilter))
      (resume $cfilter (tag $yield $on_yield)
                       (local.get $candidate)
                       (table.get $conts (local.get $fiber_idx)))
      (unreachable)
    ) ;; on_yield [ i32 (ref $cfilter) ]
    (local.set $next_k)
    ;; Update the continuation
    (table.set $conts (local.get $fiber_idx) (local.get $next_k))
    (return)
  )
  ;; filter_shutdown
  (func $filter_shutdown (export "filter_shutdown") (param $fiber_idx i32)
    (resume $cfilter (i32.const 0)
                     (table.get $conts (local.get $fiber_idx)))
    (drop)
    (table.set $conts (local.get $fiber_idx) (ref.null $cfilter))
  )
)
