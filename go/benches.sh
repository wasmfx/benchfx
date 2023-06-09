function bench() {
  rexpr="median("
  for i in {1..1}; do
    time -o 'omg' -f '%e' "$@" >/dev/null 2>/dev/null;
    num=`cat omg`
    echo $num
    rexpr="$rexprtime$tm,"
  done
  echo "$rexpr)" >>benches.r
}

echo >benches.r
echo "main-kjp.go wasmfx"
echo "# main-kjp.go wasmfx" >> benches.r
bench ./e2e.sh main-kjp.go
echo "main-kjp.go asyncify"
echo "# main-kjp.go asyncify" >> benches.r
bench tinygo build -target wasi -o coroutines.wasm main-kjp.go
echo "coroutines.go wasmfx"
echo "# coroutines.go wasmfx" >> benches.r
bench ./e2e.sh coroutines.go
echo "coroutines.go asyncify"
echo "# coroutines.go asyncify" >> benches.r
bench tinygo build -target wasi -o coroutines.wasm coroutines.go
