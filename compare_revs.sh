#!/bin/bash
#

#source make.config

REPOA=../repos_benchfx/repo_a
REPOB=../repos_benchfx/repo_b

BENCHMARKS=("c10m" "sieve" "skynet" "state")
#BENCHMARKS=("c10m")

WASMTIME_CARGO_FLAGS="--features=default,unsafe_disable_continuation_linearity_check"

WASMTIME_REL_PATH="./target/release/wasmtime"
WASMTIMEFX_FLAGS="-W=exceptions,function-references,typed-continuations"

MIMALLOC=../dependencies/mimalloc-2.1.2/release/out/libmimalloc.so

HYPERFINE="hyperfine --warmup 3"

function error {
  local msg=$1
  echo "error: $msg"
  exit 1
}


function checkout() {
  local dir=$1
  local commit=$2

  pushd "$dir" || error

  git checkout "$commit" || error "could not checkout $commit in $dir"
  git submodule update --init --recursive || error "submodule update failed"

  popd
}

function build() {
  local dir=$1

  pushd "$dir" || error

  echo "building in $dir"
  cargo build $WASMTIME_CARGO_FLAGS --release &> /dev/null || error "build failure in $dir"

  popd
}

function build_benchmark_wasm() {
  local bench=$1
  pushd "./$bench"

  rm "${bench}_wasmfx.wasm"
  make "${bench}_wasmfx.wasm" || error "Could not create ${bench}_wasmfx.wasm"

  popd
}

function build_benchmark_cwasm() {
  local repo=$1
  local rev_name=$2
  local bench=$3

  mkdir -p out
  WASMFXTIMEC="$repo/$WASMTIME_REL_PATH compile"

  $WASMFXTIMEC $WASMTIMEFX_FLAGS -o out/${bench}_${rev_name}_wasmfx.cwasm ./${bench}/${bench}_wasmfx.wasm || error "could not build cwasm file for benchmark $bench for repo $1"

}

function run_benchmark() {
  local bench=$1

  WASMTIME_A="LD_PRELOAD=${MIMALLOC} ${REPOA}/${WASMTIME_REL_PATH} $WASMTIMEFX_FLAGS"
  WASMTIME_B="LD_PRELOAD=${MIMALLOC} ${REPOB}/${WASMTIME_REL_PATH} $WASMTIMEFX_FLAGS"
  run_a="$WASMTIME_A --allow-precompiled out/${bench}_A_wasmfx.cwasm"
  run_b="$WASMTIME_B --allow-precompiled out/${bench}_B_wasmfx.cwasm"

  $HYPERFINE --style=basic --shell=bash --command-name="rev A" --command-name="rev B" --export-json=out/${bench}.json \
      "$run_a" "$run_b" || error "hyperfine failed on bench $bench"
}

function print_result() {
  local bench=$1

  echo -n "$bench: "
  jq '(.results[0].mean) / (.results[1].mean)'  out/${bench}.json || error "jq failed on bench $bench"
}


pushd "$REPOA"
commit_a=$(git rev-parse --verify $1)
commit_b=$(git rev-parse --verify $2)
popd


checkout "$REPOA" "$commit_a"
checkout "$REPOB" "$commit_b"

build "$REPOA"
build "$REPOB"


for bench in "${BENCHMARKS[@]}" ; do
    echo $bench
    build_benchmark_wasm $bench

    build_benchmark_cwasm "$REPOA" A "$bench"
    build_benchmark_cwasm "$REPOB" B "$bench"
done

for bench in "${BENCHMARKS[@]}" ; do
    run_benchmark "$bench"
done

echo "Results: rev A / rev B"
for bench in "${BENCHMARKS[@]}" ; do
    print_result "$bench"
done
