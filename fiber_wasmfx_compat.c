// This file is used to make the existing _wasmfx benchmark implementations
// (using handwritten .wast files) compatible with the fiber.h-based wasmfx
// benchmark implementations.

// When compiling the existing _wasmfx benchmarks, the setup
// and teardown functions are not required to do anything.
void fiber_init() {}
void fiber_finalize() {}
