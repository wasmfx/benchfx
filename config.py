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
# WebAssembly/binaryen#main as of February 26, 2025
BINARYEN_REVISION = "609bcec0c1c321d2b4805e341a558679ae710e99"
# wasmfx/wasmfxtime#main as of February 26, 2025
WASMTIME_REVISION = "21540296f1c262188636fe0fb373cd2a9600d764"
# wasmfx/specfx#main as of February 26, 2025
SPEC_REVISION = "54d6657b16b7bf134808064e4f77845a2b7c4fcc"

WASMTIME_CARGO_BUILD_ARGS = [
    "--features=default"
]
WASMTIME_RUN_ARGS = [
    "-W=exceptions,function-references,stack-switching",
    "-Ccache=n",
    "-Wwasmfx-stack-size=4096",
    "-Wwasmfx-red-zone-size=0",
]
WASMTIME_COMPILE_ARGS = [
    "-W=exceptions,function-references,stack-switching",
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
