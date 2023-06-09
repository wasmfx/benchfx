{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell rec {
  buildInputs = with pkgs; [
    wabt
    binaryen
    # TODO: Figure out how to do with clang
    gcc
    # clang_14
    # clang-tools_14
    mimalloc
  ];
  LD_LIBRARY_PATH = with pkgs; lib.makeLibraryPath [ mimalloc ];
}

