{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell rec {
  buildInputs = with pkgs; [
    wabt
    binaryen
    clang_14
    clang-tools_14
    rakudo
    wasmtime
    mimalloc
  ];
  LD_LIBRARY_PATH = with pkgs; lib.makeLibraryPath [ mimalloc ];
}
