;; Implementation of the WasmFX stubs

(module $wasmfx_import
  (type $f (func (param i32 i64) (result i64)))
  (type $ct (cont $f))
  (type $fyield (func (result i64)))
  (type $cyield (cont $fyield))

  (func $skynet (import "main" "skynet") (param i32 i64) (result i64))
  (elem declare func $skynet)

  (tag $yield (param i64))

  (func $wasmfx_yield (export "yield") (param $i i64)
    (suspend $yield (local.get $i)))

  (func $wasmfx_handle (export "handle")
    (param $level i32)
    (param $num i64)
    (result i64)
      (block $on_yield (result i64 (ref $cyield))
        (resume $ct (on $yield $on_yield)
          (local.get $level)
          (local.get $num)
          (cont.new $ct (ref.func $skynet)))
        (return)
      ) ;; on_yield, stack is [ i64, ref $cyield ]
      (resume $cyield) ;; clean-up the stack, discard the dummy value
      (drop) ;; discard the dummy value
      ;; return the i64 provided by yield.
  )
)