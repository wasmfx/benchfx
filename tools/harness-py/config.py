from typing import List
from main import Entry

BENCHMARKS : List[Entry]= [
    Entry(path = "macro/c10m",
          alternatives = ["c10m_wasmfx"])
]

BINARYEN_COMMIT = "30408729702df540930801708950678a54a7afe3"

WASMTIME_COMMIT = "123"

SPEC_COMMIT="4f8d8c7359e6b157236f9245b2a423be9a117782"
