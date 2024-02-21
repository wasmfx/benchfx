from typing import List
from main import Suite

BENCHMARK_SUITES : List[Suite]= [
    Suite(path = "c10m",
          benchmarks = ["c10m_wasmfx"])
]

BINARYEN_COMMIT = "30408729702df540930801708950678a54a7afe3"

WASMTIME_COMMIT = "4df0bc599f31f4c1c9099b1439b9751e56db0617"

SPEC_COMMIT="4f8d8c7359e6b157236f9245b2a423be9a117782"

WASMTIME_CARGO_BUILD_ARGS = ["--features=default,unsafe_disable_continuation_linearity_check"]
WASMTIME_RUN_ARGS = []
WASMTIME_COMPILE_ARGS = []
