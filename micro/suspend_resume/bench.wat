(module

 (type $fp0r0 (func))
 (type $cp0r0 (cont $fp0r0))

 (tag $tr0s0)

 (global $iterations i32 (i32.const 20000000))

 (func $suspend0
   (local $i i32)
   (local.set $i (global.get $iterations))

   (loop $loop
     (suspend $tr0s0)
     (local.tee $i (i32.sub (local.get $i) (i32.const 1)))
     (br_if $loop)
   )
 )
 (elem declare func $suspend0)

 (func $resume0 (export "run")

   (cont.new $cp0r0 (ref.func $suspend0))
   (loop $loop (param (ref $cp0r0))
     (resume $cp0r0 (on $tr0s0 $loop))
     (return)
   )

 )
)
