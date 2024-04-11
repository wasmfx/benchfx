# BenchFX: a collection of benchmark programs for WasmFX

This repository contains a suite of curated benchmarks for performance
testing the WasmFX implementation in wasmtime.

## Using the benchmark harness 

The benchmark harness is invoked by running `harness.py`, its user-facing
configuration resides in `config.py`.

The harness has 3 subcommands, determining its mode of operation.

The simplest way of running all the benchmarks is as follows:
 ```shell
./harness setup # required only once
./harness run 
 ```

Note that both the toplevel harness and the individual subcommand each have `--help` options:
```shell
./harness              --help
./harness setup        --help
./harness run          --help
./harness compare-revs --help
 ```


All benchmarks are listed in `config.py`. Each benchmark is part of a
_benchmark suite_, which is uniquely identified by a subfolder inside the benchfx
repository and contains logically related benchmarks (e.g., different
implementations of the same program to compare their performance).

The harness is designed such that all dependencies (including wasmtime) are
built from source at fixed commits or a specific version is downloaded.
In other words, invoking `./harness.py` with the same options at the same
revision of the `benchfx` repository (and therefore the same definitions in
`config.py`), should uniquely determine the exact versions of all dependencies as well as the
flags they are built and run with.

## `setup` subcommand

The benchmark harness uses and controls the following repositories as subfolders
in `tools/repos`:
* `mimalloc`
* `binaryen`
* `spec`, containing the wasm reference interpreter
* Two versions of wasmtime, called `wasmtime1` and `wasmtime2`

Before each benchmark run, the harness checks out and builds the requested
revision of each tool (determined either in `config.py` or overridden with a
command line flag) before running benchmarks. 

When running `./harness.py setup`, the harness checks that these repositories
exist and if not, clones them from Github appropriately.

The harness also uses the WASI SDK, running `./harness.py setup` checks that the
version configured in `config.py` exists in the `tools` subdirectory and
downloads it otherwise. 


In addition, the harness requires a few standard tools (`hyperfine, `cmake`,
`make`, `dune`, ... ) and will report and error if these are not found in
`$PATH`. These must be installed manually by the user.

### Using your own development repository of wasmtime

Since the benchmarks will be executed by checking out and building a specific
commit of wasmtime, it can be handy not to use a Github repository, but to use
commits only available in a local development repository. 

The `setup` subcommand therefore allows that instead of checking out `wasmtime`
from Github, it creates two [`git
worktrees`](https://git-scm.com/docs/git-worktree) inside `tools/repos/`, which
are connected to your development repository elsewhere.
This can be achieved as follows:

``` shell
./harness.py setup \
  --wasmtime-create-worktree-from-development-repo ~/path/to/my-wasmtime-devel-repository
```

This effectively means that `tools/repos/wasmtime1` and `tools/repos/wasmtime2`
are not independent git repositories, but share the `.git` folder with the
development repository and can see all commits therein.


## `run` subcommand

This is the main way to perform actual benchmarking.
In this mode, for each benchmark suite defined in `config.py`, the benchmarks of
that suite are compared against each other.

The subcommand has multiple options to override for example how wasmtime is
built and run, see `./harness.py run --help` for a full list of options.

### Filtering benchmarks

The `--filter` option can be used to run only a subset of the benchmarks.

Filters are ordinary glob patterns that are matched against a pseudo-path identifying each
benchmark, of the form `<suite's path>/<benchmark name>`. For example
the suite with path `c10m` contains a benchmark called `c10m_wasmfx`. It is
selected if the glob filter matches the pseudo-path `c10m/c10m_wasmfx`.

The `--filter` option can be used multiple times, and the harness will run a
benchmark if it matches _any_ of the filters.


## `compare-revs` subcommand

This subcommand can be used to compare two revisions of wasmtime, _rev1_ and
_rev2_ against each other. Unlike the `run` subcommand, benchmarks are not
compare against the others in the same suite. Instead, for each suite _s_ and
each benchmark _b_ in _s_, we compare _b_ executed by wasmtime _rev1_ against
_b_ executed wasmtime _rev2_.


The two revisions are provided to the subcommand directly as positional arguments:
``` shell
./harness.py compare-revs main my-feature-branch
```


Filtering works the same as for the `run` subcommand.

Most other options available for the `run` subcommand are also available, but
are prefixed with `rev1-` and `rev2-` now. 

As a result, `compare-revs` can actually compare different _configurations_
rather than just revision: By using the same argument for the revision to use,
but varying the other options, we can determine their influence.

 
``` shell
./harness.py compare-revs --filter="*/*wasmfx*" \
  --rev1-wasmtime-run-args="-W=exceptions,function-references,typed-continuations -Wwasmfx-stack-size=4096 -Wwasmfx-red-zone-size=0" \
  --rev2-wasmtime-run-args="-W=exceptions,function-references,typed-continuations -Wwasmfx-stack-size=8192 -Wwasmfx-red-zone-size=0" \
  my-branch my-branch 
```


## Examples

Within each suite, only compare the `wasmfx` implementations against `asyncify`:
``` shell
./harness.py run --filter="*/*wasmfx*" --filter="*/*asyncify*"
```

Running benchmarks using a particular wasmtime commit 
``` shell
./harness.py run my-special-feature-branch
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
