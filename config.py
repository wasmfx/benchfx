from typing import List
from harness import Suite, Benchmark, MakeWasm, Wat

BENCHMARK_SUITES: List[Suite] = [
    Suite(
        path="c10m",
        benchmarks=[
            MakeWasm(file=wasm)
            for wasm in ["c10m_bespoke", "c10m_asyncify", "c10m_wasmfx", "c10m_wasmfx_fiber"]
        ],
    ),
    Suite(
        path="sieve",
        benchmarks=[
            MakeWasm(file=wasm)
            for wasm in ["sieve_bespoke", "sieve_asyncify", "sieve_wasmfx",  "sieve_wasmfx_fiber"]
        ],
    ),
    Suite(
        path="skynet",
        benchmarks=[
            MakeWasm(file=wasm)
            for wasm in ["skynet_bespoke", "skynet_asyncify", "skynet_wasmfx", "skynet_wasmfx_fiber"]
        ],
    ),
    Suite(
        path="state",
        benchmarks=[
            MakeWasm(file=wasm)
            for wasm in ["state_bespoke", "state_asyncify", "state_wasmfx", "state_wasmfx_fiber"]
        ],
    ),
    Suite(path="micro/suspend_resume", benchmarks=[Wat("bench", invoke="run")]),
    Suite(path="micro/2resumes_same_function", benchmarks=[Wat("bench", invoke="run")]),
]

MIMALLOC_REVISION = "v2.1.2"
# WebAssembly/binaryen#main as of April 8, 2024
BINARYEN_REVISION = "102c3633d2378457dae1f5e239fd63ad80eefb92"
# wasmfx/wasmfx#main as of April 9, 2024
WASMTIME_REVISION = "7f63b553c3d2c91d7fe3ef0902ed1543f2fd1821"
# wasmfx/specfx#main as of April 10, 2024
SPEC_REVISION = "0af205c2c6a5569046274173d8c0388a3272087f"

WASMTIME_CARGO_BUILD_ARGS = [
    "--features=default,unsafe_disable_continuation_linearity_check"
]
WASMTIME_RUN_ARGS = [
    "-W=exceptions,function-references,typed-continuations",
    "-Ccache=n",
    "-Wwasmfx-stack-size=4096",
    "-Wwasmfx-red-zone-size=0",
]
WASMTIME_COMPILE_ARGS = [
    "-W=exceptions,function-references,typed-continuations",
    "-Ccache=n",
]


# Github repos used by setup command.
# First entry is the initial/root commit of the corresponding repo.
# List entries are of the form (github_user_name, repo_name)
GITHUB_REPOS = {
    "mimalloc": (
        "234e3a57daa9f2dadc8a57c93d90adce2bbe962e",
        [("microsoft", "mimalloc")],
    ),
    "spec": ("ec38c06717612db984314ceef08878838e1fd9ee", [("wasmfx", "specfx")]),
    "binaryen": (
        "5c839bb462f43f7a356593f537edb08014d0f25f",
        [("webassembly", "binaryen")],
    ),
    "wasmtime": (
        "399be07fcf00d0974d2a83d1af55f0bee9861d54",
        [("wasmfx", "wasmfxtime"), ("bytecodealliance", "wasmtime")],
    ),
}

WASI_SDK_VERSION = "22"
