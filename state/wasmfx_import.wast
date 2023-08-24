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

  (tag $get (result i32))
  (tag $put (param i32))

  (elem declare func $count) ;; NOTE(dhil): Remove this from the assembled file!

  (func $count (param i32) (result i32) ;; NOTE(dhil): Remove this from the assembled file
    (unreachable))

  (func $handle_count (param $value i32) (param $limit i32) (result i32)
    (local $state i32)
    (local $k (ref $kt))
    (local $kget (ref $cget))
    (local.set $state (local.get $value))
    (local.set $k
       (cont.bind $cinit $kt
          (local.get $limit)
          (cont.new $cinit (ref.func $count)))) ;; NOTE(dhil): Substitute $count for the actual index!
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
)