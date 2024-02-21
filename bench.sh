if [[  ! $(echo "import git" | python3 - &> /dev/null) ]] ;  then
	echo "This test harness requires the GitPython module (consider running 'pip install GitPython')"
	#exit 1
fi

python3 tools/harness-py/main.py "$@"
