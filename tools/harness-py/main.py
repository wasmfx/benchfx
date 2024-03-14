import argparse
import subprocess
import multiprocessing
import math
import config
import json

from typing import List, Tuple
from pathlib import Path
from dataclasses import dataclass, field
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
class Benchmark:
    name: str

    def build(self, suite_path, reference_interpreter, wasm_merge, wasm_opt):
        pass

@dataclass
class MakeWasm(Benchmark):


    def build(self, suite_path, reference_interpreter, wasm_merge, wasm_opt):
        f = self.name + ".wasm"
        run_check(["make", f] + [f"WASM_INTERP={reference_interpreter}", f"WASM_MERGE={wasm_merge}", f"WASM_OPT={wasm_opt}"], cwd = suite_path)


@dataclass
class Wat(Benchmark):
    invoke: str = field(default=None)

@dataclass
class Suite:
    path: str
    benchmarks: List[Benchmark]





class HarnessError(Exception):
    def __init__(self, msg):
        super().__init__(msg)

def check(condition, msg):
    if not condition:
        raise HarnessError(msg)

def log(msg, sep = None):
    print(msg, sep=sep)

SHOW_OUTPUT=True


def run(cmd, cwd = None) -> subprocess.CompletedProcess:
    use_shell = not isinstance(cmd, list)
    log(f"cmd is {cmd}, cwd is {cwd}")
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, shell=use_shell, text = True)
    if SHOW_OUTPUT:
        log(res.stdout, sep = "")
        log(res.stderr, sep = "")
    return res


# Like run, but checks that the command finished with non-zero exit code.
def run_check(cmd, msg = None, cwd = None):
    #use_shell = not isinstance(cmd, list)
    # if isinstance(cmd, list):
    #     cmd = map(lambda part: "'" + part + "'", cmd)
    #     cmd = " ".join(cmd)
    result = run(cmd, cwd)
    msg = msg or f"Running {cmd} in {cwd or os.getcwd()} failed"
    check(result.returncode == 0, msg + f"\nDetails:\nCommand failed: {cmd}\nStdout: {result.stdout}, Stderr: {result.stderr}")
    return result


class Binaryen:

    def __init__(self, path: Path):
        self.path = path

    def build(self):
        cpus = math.ceil(multiprocessing.cpu_count() / 2)
        run_check("cmake .", msg = "cmake for binaryen failed", cwd = self.path)
        run_check(f"make -j {cpus}", msg = "building binaryen failed", cwd = self.path)


    def wasm_merge_executable_path(self) -> str:
        return str(os.path.join(self.path, "bin", "wasm-merge"))

    def wasm_opt_executable_path(self) -> str:
        return str(os.path.join(self.path, "bin", "wasm-opt"))



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

    def executable_path(self):
        if self.release_build:
            return os.path.join(self.path, "target/release/wasmtime")
        else:
            return os.path.join(self.path, "target/debug/wasmtime")


    def build(self):
        # For the tim
        release = ["--release"] if self.release_build else []
        run_check(["cargo", "build"] + release + config.WASMTIME_CARGO_BUILD_ARGS, "Failed to build wasmtime", self.path)


    def compile_cwasm(self, input_wasm_path, output_cwasm_path):
        wasmtime = self.executable_path()
        command = "compile"
        args = config.WASMTIME_COMPILE_ARGS
        run_check([wasmtime, "compile" ] + args + [f"--output={output_cwasm_path}", input_wasm_path], f"Failed to compile {input_wasm_path} to  {output_cwasm_path}" )

    def run_cwasm_shell_command(self, cwasm_path):
        wasmtime = self.executable_path()
        command = "run"
        all  = [wasmtime , "run", "--allow-precompiled"] + config.WASMTIME_RUN_ARGS + [cwasm_path]
        all_escaped = map(lambda part: f"'{part}'", all)
        return " ".join(all_escaped)

class Hyperfine:
    @staticmethod
    def run(shell_commands, warmup_count = 3, json_export_path = None):
        args = ["hyperfine", f"--warmup={warmup_count}"]
        if json_export_path:
            args += [f"--export-json={json_export_path}"]
        run_check(args + shell_commands)




# Helper class for working at a git repo (or a working tree of a git repo) at a given path.
# This is mostly a wrapper around GitPyhton's git.Repo type
class GitRepo:
    def __init__(self, path):
        self.path = path

        check(GitRepo.is_root_of_repo_or_worktree(path),
              f"{path} is not the root of a git repository (or a worktree of a repository)")


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


# Builds the reference interpreter and binaryen
def build_common_tools():
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

   return (interpreter, binaryen)

# The run command, which just runs the benchmarks
class Run:
    def __init__(self):
        pass


    def make(self):
        pass

    @staticmethod
    def run_macro_make(args, reference_interpreter, wasm_merge, wasm_opt, cwd):
        run_check(["make"] + args + [f"WASM_INTERP={reference_interpreter}", f"WASM_MERGE={wasm_merge}", f"WASM_OPT={wasm_opt}"], cwd = cwd)

    def execute(self, args):
        print("run is running")


        (interpreter, binaryen) = build_common_tools()

        # Wasmtime setup
        wasmtime_repo_path = os.path.join(REPOS_PATH, WASMTIME_REPO1)
        log(f"wasmtime repo expected at {wasmtime_repo_path}")

        wasmtime_repo = GitRepo(wasmtime_repo_path)

        log(f"wasmtime repo dirty? {wasmtime_repo.is_dirty()}")

        wasmtime_repo.checkout(config.WASMTIME_COMMIT)

        wasmtime = Wasmtime(wasmtime_repo_path)

        wasmtime.build()

        suite_files = {}

        # Build benchmarks in each suite
        for suite in config.BENCHMARK_SUITES:
            path = Path(suite.path)
            check(path.exists(), f"Found benchmark suite with non-existing path {path}")

            # The make files may not be fully aware that various tools changed
            run_check("make clean", cwd = path)
            # TODO change this to just "make"


            benchmark_cwasm_paths = []
            for b in suite.benchmarks:
                benchmark_file = b.name + ".wasm"
                benchmark_path = path.joinpath(benchmark_file)

                benchmark_filter = args.filter
                if benchmark_filter is not None and not benchmark_path.match(benchmark_filter):
                    log(f"Skipping benchmark {benchmark_path} as it does not match filter")
                    continue


                # create .wasm file for each benchmark
                b.build(suite_path=path,
                        reference_interpreter=Path(interpreter.executable_path()).absolute(),
                        wasm_merge=Path(binaryen.wasm_merge_executable_path()).absolute(),
                        wasm_opt=Path(binaryen.wasm_opt_executable_path()).absolute())

                # Create .cwasm file for each benchmark
                benchmark_cwasm_path = path.joinpath(b.name + ".cwasm")
                wasmtime.compile_cwasm(str(benchmark_path), str(benchmark_cwasm_path))

                benchmark_cwasm_paths.append(benchmark_cwasm_path)

            if benchmark_cwasm_paths:
                suite_files[suite.path] = benchmark_cwasm_paths
            #


        # Perform actual benchmarking in each suite:
        for (suite_path, suite_cwasm_files) in suite_files.items():
            wasmtime_run_commmands = list(map(wasmtime.run_cwasm_shell_command, suite_cwasm_files))
            Hyperfine.run(wasmtime_run_commmands)


    @staticmethod
    def addSubparser(subparsers):
        parser = subparsers.add_parser("run", help = "runs benchmarks (used by default)")
        parser.add_argument("--filter", help="Only run benchmarks that match this glob pattern")
        parser.add_argument("--allow-dirty", help = "Allows the benchfx, binaryen, spec and wasmtime repos to be dirty", action = "store_true")


class CompareRevs:
    def __init__(self):
        pass

    def make(self):
        pass

    @staticmethod
    def run_macro_make(args, reference_interpreter, wasm_merge, wasm_opt, cwd):
        run_check(["make"] + args + [f"WASM_INTERP={reference_interpreter}", f"WASM_MERGE={wasm_merge}", f"WASM_OPT={wasm_opt}"], cwd = cwd)

    def prepare_wasmtime(self, repo_path, revision):

        wasmtime_repo = GitRepo(repo_path)

        log(f"wasmtime repo dirty? {wasmtime_repo.is_dirty()}")

        wasmtime_repo.checkout(revision)

        wasmtime = Wasmtime(repo_path)

        wasmtime.build()

        return wasmtime


    def execute(self, args):
        print("run is running")


        (interpreter, binaryen) = build_common_tools()

        # Wasmtime1 setup
        wasmtime1_repo_path = os.path.join(REPOS_PATH, WASMTIME_REPO1)
        wasmtime1 = self.prepare_wasmtime(wasmtime1_repo_path, args.revision1)

        # Wasmtime2 setup
        wasmtime2_repo_path = os.path.join(REPOS_PATH, WASMTIME_REPO2)
        wasmtime2 = self.prepare_wasmtime(wasmtime2_repo_path, args.revision2)

        suite_files = {}

        # Build benchmarks in each suite
        for suite in config.BENCHMARK_SUITES:
            path = Path(suite.path)
            check(path.exists(), f"Found benchmark suite with non-existing path {path}")

            # The make files may not be fully aware that various tools changed
            run_check("make clean", cwd = path)
            # TODO change this to just "make"


            benchmark_cwasm_pairs = []
            for b in suite.benchmarks:
                benchmark_file = b.name + ".wasm"
                benchmark_path = path.joinpath(benchmark_file)

                benchmark_filter = args.filter
                if benchmark_filter is not None and not benchmark_path.match(benchmark_filter):
                    log(f"Skipping benchmark {benchmark_path} as it does not match filter")
                    continue


                # create .wasm file for each benchmark
                b.build(suite_path=path,
                        reference_interpreter=Path(interpreter.executable_path()).absolute(),
                        wasm_merge=Path(binaryen.wasm_merge_executable_path()).absolute(),
                        wasm_opt=Path(binaryen.wasm_opt_executable_path()).absolute())


                # Create .cwasm file for each wasmtime version
                benchmark_cwasm_path1 = path.joinpath(b.name + ".rev1.cwasm")
                wasmtime1.compile_cwasm(str(benchmark_path), str(benchmark_cwasm_path1))

                benchmark_cwasm_path2 = path.joinpath(b.name + ".rev2.cwasm")
                wasmtime2.compile_cwasm(str(benchmark_path), str(benchmark_cwasm_path2))
                json_path = path.joinpath(b.name + ".result.json")

                benchmark_cwasm_pairs.append((b.name, [benchmark_cwasm_path1, benchmark_cwasm_path2], json_path))

            if benchmark_cwasm_pairs:
                suite_files[suite.path] = benchmark_cwasm_pairs



        # Perform actual benchmarking in each suite:
        for (suite_path, benchmark_cwasm_pairs) in suite_files.items():
            for (bench_name, cwasms, json_path) in benchmark_cwasm_pairs:
                wasmtime_run_commmands = [wasmtime1.run_cwasm_shell_command(cwasms[0]),
                                          wasmtime2.run_cwasm_shell_command(cwasms[1])]
                Hyperfine.run(wasmtime_run_commmands, json_export_path = json_path)

        # Print results from each suite
        for (suite_path, benchmark_cwasm_pairs) in suite_files.items():
            print(f"Suite: {suite_path}")
            for (bench_name, _, json_path) in benchmark_cwasm_pairs:
                with open(json_path, 'r') as f:
                    results = json.load(f)["results"]
                    rev1_mean = results[0]["mean"]
                    rev2_mean = results[1]["mean"]
                    print(f"{bench_name}: {rev1_mean / rev2_mean}")

            


    @staticmethod
    def addSubparser(subparsers):
        parser = subparsers.add_parser("compare-revs", help = "Run benchmarks using two wasmtime revisions and compare results")
        parser.add_argument("--filter", help = "Only run benchmarks that match this glob pattern")
        parser.add_argument("--allow-dirty", help = "Allows the benchfx, binaryen, spec and wasmtime repos to be dirty")
        parser.add_argument("revision1", help = "First Wasmtime revision to use in the comparison")
        parser.add_argument("revision2", help = "Second Wasmtime revision to use in the comparison")

def main():
    parser = argparse.ArgumentParser(prog='bench')

    subcommands = [Run, CompareRevs]
    subparsers = parser.add_subparsers(title = "Available subcommands", dest = "command", required = True)

    # This is supposed to make the  default command "run", but doesn't quite work
    # parser.set_defaults(command = "run")

    for sc in subcommands:
        sc.addSubparser(subparsers)

    args = parser.parse_args()
    print(args)

    match args.command:
        case "run": Run().execute(args)
        case "compare-revs": CompareRevs().execute(args)



if __name__ == "__main__":
    main()
