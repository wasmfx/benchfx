import argparse
import subprocess

import config

from typing import List, Tuple
from pathlib import Path
from dataclasses import dataclass
import git
from pathlib import Path
import os

ExitCode = int


REPOS_PATH="tools/repos"
SPEC_REPO="spec"


@dataclass
class Entry:
    path: str
    alternatives: List[str]


# def runProcess(cmd : str) -> tuple[ExitCode, str, str]:
#     cp = subprocess.run(cmd, capture_output=True)
#     return (cp.returncode, cp.stdout.decode('utf-8'), cp.stderr.decode('utf-8'))


class HarnessError(Exception):
    def __init__(self, msg):
        super().__init__(msg)

def check(condition, msg):
    if not condition:
        raise HarnessError(msg)

def log(msg):
    print(msg)

# def run_args(cmd, cwd=None) -> Tuple[int, str, str]:
#     completed = subprocess.run(cmd, cwd=cwd, capture_output=True, shell=True)
#     return (completed.returncode, completed.stdout.decode('utf-8'), completed.stderr.decode('utf-8'))

def run(cmd, cwd = None):
    completed = subprocess.run(cmd, cwd=cwd, capture_output=True, shell=True)
    return (completed.returncode, completed.stdout.decode('utf-8'), completed.stderr.decode('utf-8'))



def run_check(cmd, msg, cwd = None):
    print(f"cmd is {cmd}, cwd is {cwd}")
    result = run(cmd, cwd)
    check(result[0] == 0, msg + f"Details:\nCommand failed: {cmd}\nStdout: {result[1]}, Stderr: {result[2]}")


class Binaryen:
    def __init__(self, path: Path):
        self.path = Path


class RefeferenceInterpreter:
    def __init__(self, path : Path):
        self.path = path

    def build(self):
        run_check("make", "Failed to build reference interpreter", self.path)

    def assemble(self, input_wast_path, output_wasm_path):
        run_check(f"wasm -d '{input_wast_file}' -o '{output_wasm_path}'", self.path)







# Helper class for working at a git repo (or a working tree of a git repo) at a given path.
# This is mostly a wrapper around GitPyhton's git.Repo type
class GitRepo:
    def __init__(self, path):
        self.path = path
        self.repo = git.Repo(path)

    def git(self, args):
        return run_args("git", args.split(), cwd=self.path)


    def is_dirty(self):
        return self.repo.is_dirty()


    def checkout(self, revision):
        check(not self.repo.is_dirty(), f"Cannot checkout git repo at {self.path} to {revision} because it is dirty")
        self.repo.git.checkout(revision)



# The run command, which just runs the benchmarks
class Run:
    def __init__(self, path : Path, alternatives: List[str]):
        self.path = path


    def make(self):
        pass

    @staticmethod
    def execute(args):
        print("run is running")

        spec_repo_path = os.path.join(REPOS_PATH, SPEC_REPO)
        log(f"spec repo expected at {spec_repo_path}")

        spec_repo = GitRepo(spec_repo_path)

        log(f"spec repo dirty? {spec_repo.is_dirty()}")

        spec_repo.checkout(config.SPEC_COMMIT)

        interpreter_path = os.path.join(spec_repo_path, "interpreter")
        interpreter = RefeferenceInterpreter(interpreter_path)

        interpreter.build()



    @staticmethod
    def addSubparser(subparsers):
        parser = subparsers.add_parser("run", help = "runs benchmarks (used by default)")
        parser.add_argument("--filter", help = "Only run benchmarks that match this glob pattern")
        parser.add_argument("--allow-dirty", help = "Allows the benchfx, binaryen, spec and wasmtime repos to be dirty")


class Compare:
    def __init__(self, path : Path, alternatives: List[str]):
        self.path = path


    def make(self):
        pass

    @staticmethod
    def execute(args):
        pass


    @staticmethod
    def addSubparser(subparsers):
        parser = subparsers.add_parser("compare", help = "compare two wasmtime revisions")
        parser.add_argument("--filter", help = "Only run benchmarks that match this glob pattern")
        parser.add_argument("--commit1", help = "First Wasmtime commit/version to use in the comparison")
        parser.add_argument("--commit2", help = "Second Wasmtime commit/version to use in the comparison")
        parser.add_argument("--allow-dirty", help = "Allows the benchfx, binaryen, spec and wasmtime repos to be dirty")

def main():
    parser = argparse.ArgumentParser(prog='bench')

    subcommands = [Run, Compare]
    subparsers = parser.add_subparsers(title = "Available subcommands", dest = "command")

    # The default command is "run"
    parser.set_defaults(command = "run")

    for sc in subcommands:
        sc.addSubparser(subparsers)

    args = parser.parse_args()
    print(args)

    match args.command:
        case "run": Run.execute(args)
        case "compare": Compare.execute(args)



if __name__ == "__main__":
    main()
