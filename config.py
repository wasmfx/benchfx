from typing import List
from harness import Suite, Benchmark, MakeWasm, Wat

BENCHMARK_SUITES : List[Suite]= [
    Suite(path = "c10m",
          benchmarks = [MakeWasm(file=wasm) for wasm in ["c10m_bespoke", "c10m_asyncify", "c10m_wasmfx"]]),
    Suite(path = "sieve",
          benchmarks = [MakeWasm(file=wasm) for wasm in ["sieve_bespoke", "sieve_asyncify", "sieve_wasmfx"]]),
    Suite(path = "skynet",
          benchmarks = [MakeWasm(file=wasm) for wasm in ["skynet_bespoke", "skynet_asyncify", "skynet_wasmfx"]]),
    Suite(path = "state",
          benchmarks = [MakeWasm(file=wasm) for wasm in ["state_bespoke", "state_asyncify", "state_wasmfx"]]),

    Suite(path = "micro/suspend_resume",
          benchmarks = [Wat("bench", invoke="run")]),

    Suite(path = "micro/2resumes_same_function",
          benchmarks = [Wat("bench", invoke="run")]),
]

MIMALLOC_COMMIT = "v2.1.2"

# Binaryen main branch as of April 8, 2024
BINARYEN_COMMIT = "102c3633d2378457dae1f5e239fd63ad80eefb92"

WASMTIME_COMMIT = "4df0bc599f31f4c1c9099b1439b9751e56db0617"

SPEC_COMMIT="4f8d8c7359e6b157236f9245b2a423be9a117782"

WASMTIME_CARGO_BUILD_ARGS = ["--features=default,unsafe_disable_continuation_linearity_check"]
WASMTIME_RUN_ARGS = ["-W=exceptions,function-references,typed-continuations",
                     "-Ccache=n",
                     "-Wwasmfx-stack-size=4096",
                     "-Wwasmfx-red-zone-size=0" ]
WASMTIME_COMPILE_ARGS = [ "-W=exceptions,function-references,typed-continuations", "-Ccache=n"]


# Github repos used by setup command.
# First entry is the initial/root commit of the corresponding repo.
# List entries are of the form (github_user_name, repo_name)
GITHUB_REPOS = {
    "mimalloc": (
        "234e3a57daa9f2dadc8a57c93d90adce2bbe962e",
        [("microsoft", "mimalloc")],
    ),
    "spec": (
        "ec38c06717612db984314ceef08878838e1fd9ee",
        [("wasmfx", "specfx")]
    ),
    "binaryen": (
        "5c839bb462f43f7a356593f537edb08014d0f25f",
        [("webassembly", "binaryen")],
    ),
    "wasmtime": (
        "399be07fcf00d0974d2a83d1af55f0bee9861d54",
        [("wasmfx", "wasmfxtime"), ("bytecodealliance", "wasmtime")],
    ),
}

WASI_SDK_VERSION="20"
