from typing import List
from main import Suite, Benchmark, MakeWasm, Wat

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

BINARYEN_COMMIT = "30408729702df540930801708950678a54a7afe3"

WASMTIME_COMMIT = "4df0bc599f31f4c1c9099b1439b9751e56db0617"

SPEC_COMMIT="4f8d8c7359e6b157236f9245b2a423be9a117782"

WASMTIME_CARGO_BUILD_ARGS = ["--features=default,unsafe_disable_continuation_linearity_check"]
WASMTIME_RUN_ARGS = ["-W=exceptions,function-references,typed-continuations", "-Ccache=n" ]
WASMTIME_COMPILE_ARGS = [ "-W=exceptions,function-references,typed-continuations", "-Ccache=n"]
