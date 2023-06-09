{ pkgs ? import <nixpkgs> {} }:
pkgs.dockerTools.buildLayeredImage {
  name = "bench-wasmfx";
  contents = with pkgs; [
    coreutils
    dockerTools.usrBinEnv
    dockerTools.binSh
    bash
    wabt
    binaryen
    rakudo
    mimalloc
    gnumake
    (ocamlPackages.wasm.overrideAttrs (oldAttrs: {
      version = "effect-handlers";
      src = fetchFromGitHub {
        owner = "effect-handlers";
        repo = "wasm-spec";
        rev = "b7e4ed52520945c0a2648f64e6cd019d422e534b";
        sha256 = "sha256-fBDHmgnaUt+G3/im8AYOKRavldz7Lvvzl536rFwVRGU=";
      };
      postInstall = ''
        mkdir $out/bin
        cp -L interpreter/wasm $out/bin/effect-handlers-wasm
      '';
    }))
  ];
  fakeRootCommands = ''
    mkdir /tmp
  '';
  config = {
    Env = [ "LD_LIBRARY_PATH = ${with pkgs; lib.makeLibraryPath [ mimalloc ]}" ];
    Cmd = "/bin/sh";
    Volumes = {
      "/bench-wasmfx" = {};
    };
  };
}

