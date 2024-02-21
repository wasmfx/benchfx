import argparse
import subprocess
import multiprocessing
import math
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
BINARYEN_REPO="binaryen"
WASMTIME_REPO1="wasmtime1"
WASMTIME_REPO2="wasmtime2"


@dataclass
class Suite:
    path: str
    benchmarks: List[str]


# def runProcess(cmd : str) -> tuple[ExitCode, str, str]:
#     cp = subprocess.run(cmd, capture_output=True)
#     return (cp.returncode, cp.stdout.decode('utf-8'), cp.stderr.decode('utf-8'))


class HarnessError(Exception):
    def __init__(self, msg):
        super().__init__(msg)

def check(condition, msg):
    if not condition:
        raise HarnessError(msg)

def log(msg, sep = None):
    print(msg, sep=sep)

SHOW_OUTPUT=True

# def run_args(cmd, cwd=None) -> Tuple[int, str, str]:
#     completed = subprocess.run(cmd, cwd=cwd, capture_output=True, shell=True)
#     return (completed.returncode, completed.stdout.decode('utf-8'), completed.stderr.decode('utf-8'))

# class ProcessOutput:
#     def __init__(self, cp : subprocess.CompletedProcess):
#         self.returncode = cp.returncode
#         self.stdout =

def run(cmd, cwd = None) -> subprocess.CompletedProcess:
    log(f"cmd is {cmd}, cwd is {cwd}")
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, shell=True, text = True)
    if SHOW_OUTPUT:
        log(res.stdout, sep = "")
        log(res.stderr, sep = "")
    return res


# Like run, but checks that the command finished with non-zero exit code.
def run_check(cmd, msg = None, cwd = None):
    if isinstance(cmd, list):
        cmd = map(lambda part: "'" + part + "'", cmd)
        cmd = " ".join(cmd)
    result = run(cmd, cwd)
    msg = msg or f"Running {cmd} in {cwd or os.getcwd()} failed"
    check(result.returncode == 0, msg + f"\nDetails:\nCommand failed: {cmd}\nStdout: {result.stdout}, Stderr: {result.stderr}")
    return result


class Binaryen:

    def __init__(self, path: Path):
        self.path = path

    def build(self):
        cpus = math.ceil(multiprocessing.cpu_count() / 2)
        pass


        #run_check("mkdir -p out", cwd = selfpath)
        run_check("cmake .", msg = "cmake for binaryen failed", cwd = self.path)
        run_check(f"make -j {cpus}", msg = "building binaryen failed", cwd = self.path)


    def wasm_merge_executable_path(self) -> str:
        return str(os.path.join(self.path, "bin", "wasm-merge"))



class RefeferenceInterpreter:
    def __init__(self, path : Path):
        self.path = path

    def executable_path(self):
        return os.path.join(self.path, "wasm")

    def build(self):
        run_check("make", "Failed to build reference interpreter", self.path)

    def compile(self, input_path, output_path):
        run_check(f"wasm -d '{input_path}' -o '{output_path}'", self.path)



class Wasmtime:
    def __init__(self, path : Path, release_build = True):
        self.path = path
        self.release_build = release_build

    def wasmtime_executable_path(self):
        if self.release_build:
            return os.path.join(self.path + "target/release/wasmtime")
        else:
            return os.path.join(self.path + "target/debug/wasmtime")


    def build(self):
        # For the tim
        release = ["--release"] if self.release_build else []
        run_check(["cargo", "build"] + release + config.WASMTIME_CARGO_BUILD_ARGS, "Failed to build wasmtime", self.path)



# Helper class for working at a git repo (or a working tree of a git repo) at a given path.
# This is mostly a wrapper around GitPyhton's git.Repo type
class GitRepo:
    def __init__(self, path):
        self.path = path

        check(GitRepo.is_root_of_repo_or_worktree(path),
              f"{path} is not the root of a git repository (or a worktree of a repository)")

        self.repo = git.Repo(path)


    @staticmethod
    def is_root_of_repo_or_worktree(path):
        res = run("git rev-parse --show-toplevel", cwd = path)
        if res.returncode != 0:
            return False
        toplevel_path = res.stdout.strip()
        return Path(toplevel_path).absolute() == Path(path).absolute()


    # This uses run_check, use only for git commands that are not allowed to fail
    def git(self, args):
        return run_check("git " + args, cwd=self.path)


    def is_dirty(self, allow_untracked = True):
        untracked_mode = "no" if allow_untracked else "normal"
        res = self.git(f"status --untracked-files={untracked_mode} --porcelain")
        # the --porcelain option makes the output stable, where no output means clean repository
        return res.stdout.strip() != ""


    # TODO Do we always need to also update submodules?
    def checkout(self, revision):
        check(not self.is_dirty(), f"Cannot checkout git repo at {self.path} to {revision} because it is dirty")
        self.git(f"switch --detach {revision}")
        self.git("submodule update --init --recursive")



# The run command, which just runs the benchmarks
class Run:
    def __init__(self, path : Path, alternatives: List[str]):
        self.path = path


    def make(self):
        pass

    @staticmethod
    def run_macro_make(args, reference_interpreter, wasm_merge, cwd):
        run_check(["make"] + args + [f"WASM_INTERP={reference_interpreter}", f"WASM_MERGE={wasm_merge}"], cwd = cwd)

    @staticmethod
    def execute(args):
        print("run is running")

        # Reference interpreter setup

        spec_repo_path = os.path.join(REPOS_PATH, SPEC_REPO)
        log(f"spec repo expected at {spec_repo_path}")

        spec_repo = GitRepo(spec_repo_path)

        log(f"spec repo dirty? {spec_repo.is_dirty()}")

        spec_repo.checkout(config.SPEC_COMMIT)

        interpreter_path = os.path.join(spec_repo_path, "interpreter")
        interpreter = RefeferenceInterpreter(interpreter_path)

        interpreter.build()


        # Binaryen setup
        binaryen_repo_path = os.path.join(REPOS_PATH, BINARYEN_REPO)
        log(f"binaryen repo expected at {binaryen_repo_path}")

        binaryen_repo = GitRepo(binaryen_repo_path)

        log(f"binaryen repo dirty? {binaryen_repo.is_dirty()}")

        binaryen_repo.checkout(config.BINARYEN_COMMIT)

        binaryen = Binaryen(binaryen_repo_path)

        binaryen.build()


        # Wasmtime setup
        wasmtime_repo_path = os.path.join(REPOS_PATH, WASMTIME_REPO1)
        log(f"wasmtime repo expected at {wasmtime_repo_path}")

        wasmtime_repo = GitRepo(wasmtime_repo_path)

        log(f"wasmtime repo dirty? {wasmtime_repo.is_dirty()}")

        wasmtime_repo.checkout(config.WASMTIME_COMMIT)

        wasmtime = Wasmtime(wasmtime_repo_path)

        wasmtime.build()

        # Build benchmarks in each suite
        for suite in config.BENCHMARK_SUITES:
            path = suite.path
            check(Path(path).exists(), f"Found benchmark suite with non-existing path {path}")

            # The make files may not be fully aware that various tools changed
            run_check("make clean", cwd = path)
            # TODO change this to just "make"
            benches = [ b + ".wasm" for b in suite.benchmarks ]
            Run.run_macro_make(benches, Path(interpreter.executable_path()).absolute(), Path(binaryen.wasm_merge_executable_path()).absolute(), cwd = path)


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
