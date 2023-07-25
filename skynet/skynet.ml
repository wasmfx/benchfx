(* Skynet microbenchmark in OCaml *)

module Parameters = struct
  let children_per_level = 10
end

module NoControl = struct
  let rec fn_reduce :  (int -> int -> int) -> int -> int -> int -> int -> int
    = fun f p lb ub z ->
    if Int.equal lb ub then z
    else fn_reduce f p (lb+1) ub (z + f p lb)

  (* let rec spawn : int -> int -> int *)
  (*   = fun level num -> *)
  (*   if level = 0 then num *)
  (*   else let first = num * Parameters.children_per_level in *)
  (*        let last = first + Parameters.children_per_level - 1 in *)
  (*        let level = level - 1 in *)
  (*        fn_reduce (spawn level) first last 0 *)
  let rec spawn level num =
    if Int.equal level 0 then num
    else let first = num * Parameters.children_per_level in
         let last = first + Parameters.children_per_level in
         let level = level - 1 in
         fn_reduce spawn level first last 0

  let main () =
    spawn 6 0
end

module Deep = struct
  let hco =
    let open Effect.Deep in
    { retc = (fun ans -> ans)
    ; exnc = raise
    ; effc = (fun (type a) (_eff : a Effect.t) -> None) }

  let rec fn_reduce :  (int -> int -> int) -> int -> int -> int -> int -> int
    = fun f p lb ub z ->
    if Int.equal lb ub then z
    else fn_reduce f p (lb+1) ub (z + Effect.Deep.match_with (f p) lb hco)

  let rec spawn level num =
    if Int.equal level 0 then num
    else let first = num * Parameters.children_per_level in
         let last = first + Parameters.children_per_level in
         let level = level - 1 in
         fn_reduce spawn level first last 0

  let main () =
    spawn 6 0
end

module DeepYield = struct
  type _ Effect.t += Yield : int -> unit Effect.t
  exception Abort

  let hco =
    let open Effect.Deep in
    { retc = (fun ans -> ans)
    ; exnc = raise
    ; effc = (fun (type a) (eff : a Effect.t) ->
      match eff with
      | Yield num ->
         Some (fun (k : (a, _) continuation) ->
             try Effect.Deep.discontinue k Abort with
             | Abort -> num)
      | _ -> None)
    }

  let rec fn_reduce :  (int -> int -> int) -> int -> int -> int -> int -> int
    = fun f p lb ub z ->
    if Int.equal lb ub then z
    else fn_reduce f p (lb+1) ub (z + Effect.Deep.match_with (f p) lb hco)

  let rec spawn level num =
    if Int.equal level 0 then num
    else let first = num * Parameters.children_per_level in
         let last = first + Parameters.children_per_level in
         let level = level - 1 in
         fn_reduce spawn level first last 0

  let main () =
    spawn 6 0
end


module Shallow = struct

  type _ Effect.t += Yield : int -> unit Effect.t
     | Spawn : (int -> int -> int) -> unit Effect.t
  exception Abort

  let hco =
    { retc = (fun ans -> ans)
    ; exnc = raise
    ; effc = (fun (type a) (eff : a Effect.t) ->
      match eff with
      | Spawn f ->
         Some (fun (k : (a, _) continuation) ->
             Effect.Deep.continue k ())
      | Yield i ->
         Some (fun (k : (a, _) continuation) ->
             assert false)
      | _ -> None)
    }

end

(* type _ Effect.t += Spawn : (int -> int) * int -> unit Effect.t *)
(* let spawn f num = Effect.perform (Spawn (f, num)) *)

(* let rec skynet : int -> int -> int *)
(*   = fun num remaining -> *)
(*   if Int.equal remaining 1 *)
(*   then num *)
(*   else  *)
