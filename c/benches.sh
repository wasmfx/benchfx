#!/usr/bin/env sh

function bench() {
  rexprtime="median("
  rexprmem="median("
  for i in {1..5}; do
    num=`{ LD_PRELOAD=/nix/store/2mdm8h49raiwd2fl3h05a5v76bs9drjd-mimalloc-2.0.7/lib/libmimalloc.so.2 time -f '%e %M' $@ >/dev/null; } 2>&1`
    echo $num
    tm=`echo "$num" | cut -f1 -d' '`
    mm=`echo "$num" | cut -f2 -d' '`
    rexprtime="$rexprtime$tm,"
    rexprmem="$rexprmem$mm,"
  done
  echo "$rexprtime)" >>benches.r
  echo "$rexprmem)" >>benches.r
}

echo >benches.r
make all >/dev/null 2>/dev/null
echo "custom opt"
echo "# custom opt" >> benches.r
bench wasmfx cps.wasm
echo "asyncify opt"
echo "# asyncify opt" >> benches.r
bench wasmfx asyncify.wasm
echo "asyncify no opt"
echo "# asyncify no opt" >> benches.r
bench wasmfx asyncifyO0.wasm
echo "wasmfx opt"
echo "# wasmfx opt" >> benches.r
bench wasmfx --wasm-features all wasmfx.wasm
echo "x64 stacks"
echo "# x64 stacks" >> benches.r
bench ./x64

