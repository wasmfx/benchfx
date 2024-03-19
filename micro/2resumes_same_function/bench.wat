(module

 (type $ft (func))
 (type $ct (cont $ft))

 (tag $t)

 (global $iterations i32 (i32.const 100000000))

 (func $suspend0
   (local $i i32)
   (local.set $i (global.get $iterations))

   (loop $loop
     (suspend $t)
     (local.tee $i (i32.sub (local.get $i) (i32.const 1)))
     (br_if $loop)
   )
 )
 (elem declare func $suspend0)

 (func $resume0 (export "run")
   (cont.new $ct (ref.func $suspend0))
   (loop $loop (param (ref $ct))
     (block $inner (param (ref $ct)) (result (ref $ct))
       (resume $ct (tag $t $inner))
       (return)
     )
     (resume $ct (tag $t $loop))
     (return)
   )
 )
)
