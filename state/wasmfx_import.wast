;; WasmFX backend implementation of the effectful state operations

(module $wasmfx_import
  (type $init (func (param i32) (result i32)))
  (type $cinit (cont $init))

  (type $get (func (param i32) (result i32)))
  (type $cget (cont $get))
  (type $put (func (result i32)))
  (type $cput (cont $put))

  (type $ft (func (result i32)))
  (type $kt (cont $ft))

  (func $count (import "main" "count") (param i32) (result i32))
  (elem declare func $count)

  (tag $get (result i32))
  (tag $put (param i32))

  (func $handle_count (export "handle_count") (param $state i32) (param $limit i32) (result i32)
    (local $k (ref $kt))
    (local $kget (ref $cget))
    (local.set $k
       (cont.bind $cinit $kt
          (local.get $limit)
          (cont.new $cinit (ref.func $count))))
    (loop $while (result i32)
      (block $on_done (result i32)
        (block $on_put (result i32 (ref $cput))
          (block $on_get (result (ref $cget))
            (resume $kt (on $get $on_get) (on $put $on_put) (local.get $k))
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

  ;; version without using cont.bind
  (func $handle_count_nobind (export "handle_count_nobind") (param $state i32) (param $limit i32) (result i32)
    (local $kput (ref null $cput))
    (local $kget (ref null $cget))
    (block $on_done (result i32)
      ;; we handle the initial continuation application specially
      (block $continue
        (block $on_put1 (result i32 (ref $cput))
          (block $on_get1 (result (ref $cget))
            (resume $cinit (on $get $on_get1) (on $put $on_put1)
              (local.get $limit)
              (cont.new $cinit (ref.func $count)))
            (br $on_done)
          ) ;; on_get1 [ (ref $cget) ]
          (local.set $kget)
          (br $continue)
        ) ;; on_put1 [ i32 (ref $cput) ]
        (local.set $kput)
        (local.set $state)
      ) ;; after $continue
      ;; main loop
      (loop $while (result i32)
        (block $on_put (result i32 (ref $cput))
          (block $on_get (result (ref $cget))
            (block $handle_put
              (block $handle_get (result (ref $cget))
                ;; the trick is to null-test $kget; if it is non-null,
                ;; then the previous command was `get` otherwise it
                ;; must have been `put`.
                (br_on_null $handle_put (local.get $kget))
              ) ;; $handle_get
              (resume $cget (on $get $on_get) (on $put $on_put)
                (local.get $state) (local.get $kget))
              (br $on_done)
            ) ;; $handle_put
            (resume $cput (on $get $on_get) (on $put $on_put)
              (local.get $kput))
            (br $on_done)
          ) ;; $on_get [ (ref $cget) ]
          (local.set $kget)
          (br $while)
        ) ;; $on_put [ i32 (ref $cput) ]
        (local.set $kput)
        (local.set $state)
        (local.set $kget (ref.null $cget))
        (br $while)
      ) ;; after $while
    ) ;; on_done [ i32 ]
    (return)
  )

  (func $state_get (export "state_get") (result i32)
    (suspend $get))

  (func $state_put (export "state_put") (param $value i32)
    (suspend $put (local.get $value))
  )
)