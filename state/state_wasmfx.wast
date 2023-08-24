(module
  (type $0 (func (param i32)))
  (type $1 (func (result i32)))
  (type $2 (func (param i32 i32) (result i32)))
  (type $3 (func))
  (type $4 (func (param i32) (result i32)))

  (type $init (func (param i32) (result i32)))
  (type $cinit (cont $init))

  (type $get (func (param i32) (result i32)))
  (type $cget (cont $get))
  (type $put (func (result i32)))
  (type $cput (cont $put))

  (type $ft (func (result i32)))
  (type $kt (cont $ft))

  ;; (import "env" "state_get" (func $0 (type 1)))
  ;; (import "env" "state_put" (func $1 (type 0)))
  ;; (import "env" "handle_count" (func $2 (type 2)))
  (import "wasi_snapshot_preview1" "proc_exit" (func $0 (type 0)))
  (import "wasi_snapshot_preview1" "proc_exit" (func $1 (type 0)))
  (import "wasi_snapshot_preview1" "proc_exit" (func $2 (type 0)))

  (import "wasi_snapshot_preview1" "proc_exit" (func $3 (type 0)))

  (tag $get (result i32))
  (tag $put (param i32))

  (memory $0 2)
  (func $4
    (type 3)
    (local i32)
    (block
      (i32.const 1_024)
      (i32.load)
      (i32.eqz)
      (if
        (then
          (i32.const 1_024)
          (i32.const 1)
          (i32.store)
          (i32.const 0)
          (i32.const 10_000_000)
          (call $handle_count)
          (i32.const 10_000_000)
          (i32.ne)
          (local.tee 0)
          (br_if 1)
          (return)
        )
        (else)
      )
      (unreachable)
    )
    (local.get 0)
    (call 3)
    (unreachable)
  )
  (func $5
    (type 4)
    (call $state_get)
    (local.get 0)
    (i32.lt_s)
    (if
      (then
        (loop
          (call $state_get)
          (i32.const 1)
          (i32.add)
          (call $state_put)
          (call $state_get)
          (local.get 0)
          (i32.lt_s)
          (br_if 0)
        )
      )
      (else)
    )
    (call $state_get)
  )

  (func $handle_count (param $value i32) (param $limit i32) (result i32)
    (local $state i32)
    (local $k (ref $kt))
    (local $kget (ref $cget))
    (local.set $state (local.get $value))
    (local.set $k
       (cont.bind $cinit $kt
          (local.get $limit)
          (cont.new $cinit (ref.func $5)))) ;; NOTE(dhil): Substitute $count for the actual index!
    (loop $while (result i32)
      (block $on_done (result i32)
        (block $on_put (result i32 (ref $cput))
          (block $on_get (result (ref $cget))
            (resume $kt (tag $get $on_get) (tag $put $on_put) (local.get $k))
            (br $on_done)
          ) ;; on_get [ (ref $cget) ]
          (local.set $kget)
          (local.set $k (cont.bind $cget $kt (local.get $state) (local.get $kget)))
          (br $while)
        ) ;; on_put [ i32 (ref $cput) ]
        (local.set $k)
        (local.set $state)
        (br $while)
      ) ;; on_done [ i32 ]
    ) ;; after while [ i32 ]
    (return)
  )

  (func $state_get (result i32)
    (suspend $get))

  (func $state_put (param $value i32)
    (suspend $put (local.get $value))
  )

  (export "memory" (memory 0))
  (export "_start" (func 4))
  (export "count" (func 5))
)
