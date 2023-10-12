#!/usr/bin/env bash
#
# This script retrieves and configures binaryen, mimalloc, and the
# wasi-sdk dependencies.
#

BINARYEN_URL=https://github.com/WebAssembly/binaryen/releases/download/version_116/binaryen-version_116-x86_64-linux.tar.gz
MIMALLOC_URL=https://github.com/microsoft/mimalloc/archive/refs/tags/v2.1.2.tar.gz
WASI_SDK_URL=https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-20/wasi-sdk-20.0-linux.tar.gz

# params: dependency name, dependency url
function download_dependency()
{
    wget $2
    if [[ $? -ne 0 ]]; then
        echo "error: failed to download $1"
        exit 1
    fi
}

# params: dependency name, dependency archive name
function unpack_dependency()
{
    if [[ ! -f $2 ]]; then
        echo "error: cannot find the archive for $1 (filename: $2)"
        exit 1
    fi

    tar xvf $2

    if [[ $? -ne 0 ]]; then
        echo "error: unpacking $2 failed"
        exit 1
    fi
}

function install_binaryen()
{
    if [[ -d "binaryen-version_116" ]]; then
       echo "info: binaryen seems to be already installed... skipping..."
       return
    fi
    download_dependency "binaryen" $BINARYEN_URL
    unpack_dependency "binaryen" $(basename $BINARYEN_URL)
    rm -f $(basename $BINARYEN_URL)
}

function install_mimalloc()
{
    local instdir=mimalloc-2.1.2
    if [[ -d $instdir ]]; then
       echo "info: mimalloc seems to be already installed... skipping..."
       return
    fi
    download_dependency "mimalloc" $MIMALLOC_URL
    unpack_dependency "mimalloc" $(basename $MIMALLOC_URL)
    rm -f $(basename $MIMALLOC_URL)
    # Build mimalloc
    cd $instdir && \
    mkdir -p release/out && \
    cd release/out && \
    cmake ../.. && \
    make
    if [[ $? -ne 0 ]]; then
        echo "error: mimalloc build failed"
        exit 1
    fi
}

function install_wasi_sdk()
{
    if [[ -d "wasi-sdk-20.0" ]]; then
       echo "info: WASI SDK seems to be already installed... skipping..."
       return
    fi
    download_dependency "WASI SDK" $WASI_SDK_URL
    unpack_dependency "WASI SDK" $(basename $WASI_SDK_URL)
    rm -f $(basename $WASI_SDK_URL)
}

function install_binaryenfx()
{
    git clone git@github.com:frank-emrich/binaryen.git binaryenfx
    cd binaryenfx
    git checkout -b wasmfx-instrs -t origin/wasmfx-instrs
    git submodule init
    git submodule update
    cmake . && make
}

function main()
{
    install_binaryenfx
    install_mimalloc
    install_wasi_sdk
}

main
