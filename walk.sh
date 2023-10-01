
init=7b96d37d3a3162c8b1ebe3388910345edd3952e1
cur=$init

count=5

for i in $(seq 1 $count) ; do
    pushd ../repos_benchfx/repo_a
    pred=$(git rev-parse --verify "${cur}^1")
    popd
    echo "$cur $pred"

    ./compare_revs.sh $pred $cur > out/results_$i_$cur.txt

    cur=$pred
done
