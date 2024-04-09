# BenchFX: a collection of benchmark programs for WasmFX

This repository contains a suite of curated benchmarks for performance
testing the WasmFX implementation in wasmtime.

## Setup

To run the benchmark suite you need the following tools:

* hyperfine
* a release build of wasmfxtime (https://github.com/wasmfx/wasmfxtime)
* the WasmFX reference interpreter (https://github.com/wasmfx/specfx)
* binaryen
* mimalloc
* WASI SDK

The script `setup.sh` attempts to download, unpack, and build the
latter five.

## Configure

Each benchmark program has its own subdirectory. The benchmark
programs share the same global configuration. In order to modify this
configuration you have to edit the files `make.config` and
`make.generic.config` in the root directory.

## Running

To run a benchmark change the current working directory to the
directory corresponding to name of the benchmark you want to run, e.g.

```shell
$ cd c10m
```

Inside the benchmark directory you can invoke the various make
commands:

```shell
# Benchmarks WasmFX against Asyncify
c10m $ make benchfx
# Benchmarks WasmFX against Asyncify and a bespoke implementation
c10m $ make bench
# Benchmarks the memory usage of WasmFX and Asyncify
c10m $ make benchfx-mem
# Benchmarks the memory usage of WasmFX, Asyncify, and the bespoke implementation
c10m $ make benchfx-mem
```

## Gotchas

* The default fiber stack size may be too small to run WASI programs. It
  is recommended to run with at least 1mb sized stacks.
* Fiber stacks are unpooled at the moment, which unfavorably skews the
  benchmark results.
* The current implementation does not reference count Wasm `cont`
  objects, so to avoid generating garbage benchmarks should be run
  with the compile time feature
  `unsafe_disable_continuation_linearity_check` which causes Wasm
  `cont` objects point directly to the underlying fiber object. This
  is unsafe in general as a continuation are supposed to provide a
  typed view of its underlying fiber stack at a particular point of
  suspension. This type may change each suspension, whereas the type
  of the fiber does not.