#!/usr/bin/env sh
rm coroutines.wat
cp "$1" /tmp/e2e.go
wat=`cd ../../tinygo && ./e2e.sh /tmp/e2e.go`
echo "$wat" >coroutines.wat
../../effect-handlers-wasm/interpreter/wasm -d -i coroutines.wat -o coroutines.wasm
