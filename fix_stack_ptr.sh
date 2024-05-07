#!/bin/bash

# Arguments
# $1 Input path of wat file containing stack pointer global
# $2 Path where to write patched $1

STACK_PTR_GLOBAL_REGEXP='(?<=\(global )(\$.*)(?= \(mut i32\))'

mut_global=$(grep --only-matching -P "$STACK_PTR_GLOBAL_REGEXP" "$1")
mut_globals_count=$(echo "$mut_global" | wc -l)

echo "$mut_global"

if (( mut_globals_count != 1 )); then
    echo "Did not find exactly one mutable i32 global, cannot identify stack pointer"
    exit 1
fi

sed 's/(global '"$mut_global"' (mut i32)/(global '"$mut_global"' (export "__exported_shadow_stack_pointer") (mut i32)/' "$1" > "$2"
