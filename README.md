# BenchFX: a collection of benchmark programs for WasmFX

This repository contains a suite of curated benchmarks for performance
testing the WasmFX implementation in wasmtime.

## Setup

To run the benchmark suite you need the following tools:

* hyperfine
* a release build of wasmfxtime (https://github.com/wasmfx/wasmfxtime)
* binaryen
* mimalloc
* WASI SDK

The script `setup.sh` attempts to download, unpack, and build the
latter three.

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
