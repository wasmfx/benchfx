import argparse
import subprocess
import multiprocessing
import math
import config
import json
import shlex

from typing import List, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass, field
import git
from pathlib import Path

# High-level file operations
import shutil

import os

from typeguard import typechecked

ExitCode = int


REPOS_PATH = "tools/repos"
SPEC_REPO = "spec"
BINARYEN_REPO = "binaryen"
MIMALLOC_REPO = "mimalloc"
WASMTIME_REPO1 = "wasmtime1"
WASMTIME_REPO2 = "wasmtime2"


@typechecked
class HarnessError(Exception):
    def __init__(self, msg):
        super().__init__(msg)


def check(condition, msg):
    if not condition:
        raise HarnessError(msg)


def log(msg, sep=None):
    print(msg, sep=sep)


SHOW_OUTPUT = True


@typechecked
@dataclass
class Benchmark:
    name: str
    file: str

    def prepare(
        self,
        suite: "Suite",
        output_dir: Path,
        mimalloc: "Mimalloc",
        reference_interpreter: "ReferenceInterpreter",
        binaryen: "Binaryen",
        wasmtime: "Wasmtime",
    ) -> str:
        raise HarnessError("Override me!")
        return "/bin/false"


@typechecked
class MakeWasm(Benchmark):
    def __init__(self, file, name=None, invoke=None):
        self.name: str = name or file
        self.file: str = file
        self.invoke: Optional[str] = invoke

    def prepare(
        self,
        suite,
        output_dir: Path,
        mimalloc,
        reference_interpreter,
        binaryen,
        wasmtime,
    ):
        wasm_file = self.file + ".wasm"
        cwasm_file = self.file + ".cwasm"
        suite_path = Path(suite.path)
        interpreter = Path(reference_interpreter.executable_path()).absolute()
        wasm_merge = Path(binaryen.wasm_merge_executable_path()).absolute()
        wasm_opt = Path(binaryen.wasm_opt_executable_path()).absolute()
        run_check(
            ["make", wasm_file]
            + [
                f"WASM_INTERP={interpreter}",
                f"WASM_MERGE={wasm_merge}",
                f"WASM_OPT={wasm_opt}",
            ],
            cwd=suite_path,
        )

        wasmtime.compile_cwasm(suite_path / wasm_file, output_dir / cwasm_file)

        run_command = wasmtime.run_cwasm_shell_command(output_dir / cwasm_file)
        return mimalloc.add_to_shell_commmand(run_command)


@typechecked
class Wat(Benchmark):
    def __init__(self, file, name=None, invoke=None):
        self.name: str = name or file
        self.file: str = file
        self.invoke: Optional[str] = invoke

    def prepare(
        self,
        suite,
        output_dir: Path,
        mimalloc,
        reference_interpreter,
        binaryen,
        wasmtime,
    ):
        suite_path = Path(suite.path)
        wat_path = suite_path / (self.file + ".wat")
        cwasm_path = output_dir / (self.file + ".cwasm")

        wasmtime.compile_cwasm(wat_path, cwasm_path)


        run_command = wasmtime.run_cwasm_shell_command(cwasm_path, invoke_function=self.invoke)

        return mimalloc.add_to_shell_commmand(run_command)


@typechecked
@dataclass
class Suite:
    path: str
    benchmarks: List[Benchmark]

    def hasMakeBenchmark(self):
        return any(map(lambda b: isinstance(b, MakeWasm), self.benchmarks))


@typechecked
def run(cmd: str | List[str], cwd=None) -> subprocess.CompletedProcess:
    if isinstance(cmd, list):
        command = shlex.join(cmd)
    else:
        command = cmd
    cwd_msg = f" in directory {cwd}" if cwd is not None else ""
    log(f"Running command{cwd_msg}:\n{command}")
    res = subprocess.run(command, cwd=cwd, capture_output=True, shell=True, text=True)
    if SHOW_OUTPUT:
        log(res.stdout, sep="")
        log(res.stderr, sep="")
    return res


# Like run, but checks that the command finished with non-zero exit code.
@typechecked
def run_check(cmd, msg=None, cwd=None):
    result = run(cmd, cwd)
    msg = msg or f"Running {cmd} in {cwd or os.getcwd()} failed"
    check(
        result.returncode == 0,
        msg
        + f"\nDetails:\nCommand failed: {cmd}\nStdout: {result.stdout}, Stderr: {result.stderr}",
    )
    return result


@typechecked
class Binaryen:

    def __init__(self, path: Path):
        self.path = path

    def build(self):
        cpus = math.ceil(multiprocessing.cpu_count() / 2)
        run_check("cmake .", msg="cmake for binaryen failed", cwd=self.path)
        run_check(f"make -j {cpus}", msg="building binaryen failed", cwd=self.path)

    def wasm_merge_executable_path(self) -> str:
        return str(os.path.join(self.path, "bin", "wasm-merge"))

    def wasm_opt_executable_path(self) -> str:
        return str(os.path.join(self.path, "bin", "wasm-opt"))


@typechecked
class Mimalloc:

    def __init__(self, path: Path):
        self.path = path

    def build(self):
        cpus = multiprocessing.cpu_count()
        run_check("mkdir -p out", cwd=self.path)
        out_dir = self.path / "out"
        run_check("cmake ..", msg="cmake for mimalloc failed", cwd=out_dir)
        run_check(f"make -j {cpus}", msg="building mimalloc failed", cwd=out_dir)

    def libmimalloc_path(self) -> Path:
        return self.path / "out" / "libmimalloc.so"

    def add_to_shell_commmand(self, shell_command: str):
        "Given a shell command, extends it with an appropriate LD_PRELOAD clause to use mimalloc"

        escaped_path = shlex.quote(str(self.libmimalloc_path()))
        return f"LD_PRELOAD={escaped_path} {shell_command}"


@typechecked
class ReferenceInterpreter:
    def __init__(self, path: Path):
        self.path = path

    def executable_path(self) -> Path:
        return self.path / "wasm"

    def build(self):
        run_check("make", "Failed to build reference interpreter", self.path)

    def compile(self, input_path: Path, output_path: Path):
        wasm = str(self.executable_path().absolute())
        input_absolute = str(input_path.absolute())
        output_absolute = str(output_path.absolute())
        run_check(f"{wasm} -d '{input_absolute}' -o '{output_absolute}'", self.path)


@dataclass
class WasmtimeConfig:
    cargo_build_args: Optional[List[str]] = None
    compile_args: Optional[List[str]] = None
    run_args: Optional[List[str]] = None

    @staticmethod
    def from_cli_namespace_object(namespace):
        cargo_build_args = (
            None
            if getattr(namespace, "cargo_build_args", None) == None
            else shlex.split(namespace.cargo_build_args)
        )
        compile_args = (
            None
            if getattr(namespace, "compile_args", None) == None
            else shlex.split(namespace.compile_args)
        )
        run_args = (
            None
            if getattr(namespace, "run_args", None) == None
            else shlex.split(namespace.run_args)
        )
        # release_build = namespace.release_build
        return WasmtimeConfig(
            cargo_build_args=cargo_build_args,
            compile_args=compile_args,
            run_args=run_args,
        )


class Wasmtime:
    def __init__(self, path: Path, config: WasmtimeConfig, release_build=True):
        self.path = path
        self.release_build = release_build
        self.config = config

    def executable_path(self):
        if self.release_build:
            return os.path.join(self.path, "target/release/wasmtime")
        else:
            return os.path.join(self.path, "target/debug/wasmtime")

    def build(self):
        # For the tim
        release = ["--release"] if self.release_build else []

        extra_args = config.WASMTIME_CARGO_BUILD_ARGS
        if self.config.cargo_build_args != None:
            extra_args = self.config.cargo_build_args
            log("Overriding cargo builds args with " + str(extra_args))

        run_check(
            ["cargo", "build"] + release + extra_args,
            "Failed to build wasmtime",
            self.path,
        )

    def compile_cwasm(self, input_wasm_path: Path, output_cwasm_path: Path):
        wasmtime = self.executable_path()
        command = "compile"
        extra_args = config.WASMTIME_COMPILE_ARGS
        if self.config.compile_args != None:
            extra_args = self.config.compile_args
            log("Overriding wasmtime compile args with " + str(extra_args))

        run_check(
            [wasmtime, "compile"]
            + extra_args
            + [
                f"--output={output_cwasm_path.absolute()}",
                str(input_wasm_path.absolute()),
            ],
            f"Failed to compile {input_wasm_path} to  {output_cwasm_path}",
        )

    def run_cwasm_shell_command(
        self,
        cwasm_path: Path,
        invoke_function=None,
    ):
        wasmtime = self.executable_path()
        command = "run"
        extra_args = config.WASMTIME_RUN_ARGS
        if self.config.run_args != None:
            extra_args = self.config.run_args
            log("Overriding wasmtime run args with " + str(extra_args))

        invoke_args = []
        if invoke_function:
            invoke_args += [f"--invoke={invoke_function}"]

        cmd = (
            [wasmtime, "run", "--allow-precompiled"]
            + extra_args
            + invoke_args
            + [str(cwasm_path.absolute())]
        )

        return shlex.join(cmd)


@typechecked
class Hyperfine:
    @staticmethod
    def run(shell_commands: List[str], warmup_count=3, json_export_path=None):
        args = ["hyperfine", f"--warmup={warmup_count}"]
        if json_export_path:
            args += [f"--export-json={json_export_path}"]
        run_check(args + shell_commands)


# Helper class for working at a git repo (or a working tree of a git repo) at a given path.
# This is mostly a wrapper around GitPyhton's git.Repo type
@typechecked
class GitRepo:
    def __init__(self, path):
        self.path = path

        check(
            GitRepo.is_root_of_repo_or_worktree(path),
            f"{path} is not the root of a git repository (or a worktree of a repository)",
        )

    @staticmethod
    def is_root_of_repo_or_worktree(path):
        res = run("git rev-parse --show-toplevel", cwd=path)
        if res.returncode != 0:
            return False
        toplevel_path = res.stdout.strip()
        return Path(toplevel_path).absolute() == Path(path).absolute()

    # This uses run_check, use only for git commands that are not allowed to fail
    def git(self, args):
        return run_check("git " + args, cwd=self.path)

    def is_dirty(self, allow_untracked=True):
        untracked_mode = "no" if allow_untracked else "normal"
        res = self.git(f"status --untracked-files={untracked_mode} --porcelain")
        # the --porcelain option makes the output stable, where no output means clean repository
        return res.stdout.strip() != ""

    # TODO Do we always need to also update submodules?
    def checkout(self, revision):
        check(
            not self.is_dirty(allow_untracked=False),
            f"Cannot checkout git repo at {self.path} to {revision} because it is dirty",
        )
        self.git(f"switch --detach {revision}")
        self.git("submodule update --init --recursive")

        # We are very strict about changed and untracked files, to avoid
        # subsequent failures: We required above that the repo is clean, not
        # even having untracked files. After checking out, we then remove all
        # newly untracked files, too.
        self.git("clean -df")


# Builds the reference interpreter and binaryen
@typechecked
def build_common_tools() -> Tuple[Mimalloc, ReferenceInterpreter, Binaryen]:
    # Mimalloc setup
    mimalloc_repo_path = Path(os.path.join(REPOS_PATH, MIMALLOC_REPO))
    mimalloc_repo = GitRepo(mimalloc_repo_path)
    mimalloc_repo.checkout(config.MIMALLOC_COMMIT)
    mimalloc = Mimalloc(mimalloc_repo_path)
    mimalloc.build()

    # Reference interpreter setup
    spec_repo_path = os.path.join(REPOS_PATH, SPEC_REPO)
    log(f"spec repo expected at {spec_repo_path}")

    spec_repo = GitRepo(spec_repo_path)

    log(f"spec repo dirty? {spec_repo.is_dirty()}")

    spec_repo.checkout(config.SPEC_COMMIT)

    interpreter_path = Path(os.path.join(spec_repo_path, "interpreter"))
    interpreter: ReferenceInterpreter = ReferenceInterpreter(interpreter_path)

    interpreter.build()

    # Binaryen setup
    binaryen_repo_path = Path(REPOS_PATH) / BINARYEN_REPO
    log(f"binaryen repo expected at {binaryen_repo_path}")

    binaryen_repo = GitRepo(binaryen_repo_path)

    log(f"binaryen repo dirty? {binaryen_repo.is_dirty()}")

    binaryen_repo.checkout(config.BINARYEN_COMMIT)

    binaryen = Binaryen(binaryen_repo_path)

    binaryen.build()

    return (mimalloc, interpreter, binaryen)


@typechecked
def add_wasmtime_args_to_subparser(
    subparser,
    namespace: argparse.Namespace,
    suffix: Optional[str] = None,
    desc: Optional[str] = None,
):
    wasmtime = "wasmtime" + ("" if suffix == None else suffix)
    desc = "wasmtime" if desc == None else desc
    subparser.add_argument(
        f"--{wasmtime}-cargo-build-args",
        help=f"Instead of config.WASMTIME_CARGO_BUILD_ARGS, use these arguments when running 'cargo build' for {desc}.",
        action=ForwardChildNamespaceAction,
        dest="cargo_build_args",
        namespace=namespace,
        forward_to=argparse._StoreAction,
    )
    subparser.add_argument(
        f"--{wasmtime}-run-args",
        help=f"Instead of config.WASMTIME_RUN_ARGS, use these arguments when executing 'wasmtime run' with {desc}. May be unsupported for certain benchmarks.",
        action=ForwardChildNamespaceAction,
        dest="run_args",
        namespace=namespace,
        forward_to=argparse._StoreAction,
    )
    subparser.add_argument(
        f"--{wasmtime}-compile-args",
        help=f"Instead of config.WASMTIME_RUN_ARGS, use these arguments when executing 'wasmtime compile' with {desc}. May be unsupported for certain benchmarks.",
        action=ForwardChildNamespaceAction,
        dest="compile_args",
        namespace=namespace,
        forward_to=argparse._StoreAction,
    )


# The run command, which just runs the benchmarks
@typechecked
class Run:
    def __init__(self):
        pass

    def make(self):
        pass

    @staticmethod
    def run_macro_make(args, reference_interpreter, wasm_merge, wasm_opt, cwd):
        run_check(
            ["make"]
            + args
            + [
                f"WASM_INTERP={reference_interpreter}",
                f"WASM_MERGE={wasm_merge}",
                f"WASM_OPT={wasm_opt}",
            ],
            cwd=cwd,
        )

    def execute(self, args):
        print("run is running")

        (mimalloc, interpreter, binaryen) = build_common_tools()

        # Wasmtime setup
        wasmtime_repo_path = Path(REPOS_PATH) / WASMTIME_REPO1
        log(f"wasmtime repo expected at {wasmtime_repo_path}")

        wasmtime_repo = GitRepo(wasmtime_repo_path)

        log(f"wasmtime repo dirty? {wasmtime_repo.is_dirty()}")

        wasmtime_repo.checkout(config.WASMTIME_COMMIT)
        wamtime_config = WasmtimeConfig.from_cli_namespace_object(args.wasmtime)
        wasmtime = Wasmtime(wasmtime_repo_path, wamtime_config)

        wasmtime.build()

        suite_shell_commands = {}

        # Build benchmarks in each suite
        for suite in config.BENCHMARK_SUITES:
            suite_path = Path(suite.path)
            check(
                suite_path.exists(),
                f"Found benchmark suite with non-existing path {suite_path}",
            )

            if suite.hasMakeBenchmark():
                # The make files may not be fully aware that various tools changed
                run_check("make clean", cwd=suite_path)

            benchmark_commands = []
            for b in suite.benchmarks:
                benchmark_pseudopath = suite_path / b.name

                benchmark_filters = args.filter
                if benchmark_filters and not any(
                    map(benchmark_pseudopath.match, benchmark_filters)
                ):
                    log(
                        f"Skipping benchmark {benchmark_pseudopath} as it does not match filter"
                    )
                    continue

                benchmark_output_dir = Path("out") / suite_path / b.name
                benchmark_output_dir.mkdir(parents=True, exist_ok=True)

                # create .wasm file for each benchmark
                benchmark_commands.append(
                    b.prepare(
                        suite,
                        benchmark_output_dir,
                        mimalloc=mimalloc,
                        reference_interpreter=interpreter,
                        binaryen=binaryen,
                        wasmtime=wasmtime,
                    )
                )

            if benchmark_commands:
                suite_shell_commands[suite.path] = benchmark_commands
            #

        # Perform actual benchmarking in each suite:
        for _suite_path, benchmark_commands in suite_shell_commands.items():
            Hyperfine.run(benchmark_commands)

    @staticmethod
    def addSubparser(subparsers, namespace):
        parser = subparsers.add_parser("run", help="runs benchmarks (used by default)")

        parser.add_argument(
            "--filter",
            help="Only run benchmarks that match this glob pattern",
            action="append",
        )
        parser.add_argument(
            "--allow-dirty",
            help="Allows the benchfx, binaryen, spec and wasmtime repos to be dirty",
            action="store_true",
        )

        namespace.wasmtime = argparse.Namespace()
        add_wasmtime_args_to_subparser(parser, namespace.wasmtime)


@typechecked
class CompareRevs:
    def __init__(self):
        pass

    def make(self):
        pass

    @staticmethod
    def run_macro_make(args, reference_interpreter, wasm_merge, wasm_opt, cwd):
        run_check(
            ["make"]
            + args
            + [
                f"WASM_INTERP={reference_interpreter}",
                f"WASM_MERGE={wasm_merge}",
                f"WASM_OPT={wasm_opt}",
            ],
            cwd=cwd,
        )

    def prepare_wasmtime(self, repo_path: Path, revision: str, config: WasmtimeConfig):

        wasmtime_repo = GitRepo(repo_path)

        log(f"wasmtime repo dirty? {wasmtime_repo.is_dirty()}")

        wasmtime_repo.checkout(revision)

        wasmtime = Wasmtime(repo_path, config)

        wasmtime.build()

        return wasmtime

    def execute(self, args):
        print("compare-revs is running")

        (mimalloc, interpreter, binaryen) = build_common_tools()

        # Wasmtime1 setup
        wasmtime1_repo_path = Path(REPOS_PATH) / WASMTIME_REPO1
        wasmtime1_config = WasmtimeConfig.from_cli_namespace_object(args.wasmtime1)
        wasmtime1 = self.prepare_wasmtime(
            wasmtime1_repo_path, args.revision1, wasmtime1_config
        )

        # Wasmtime2 setup
        wasmtime2_repo_path = Path(REPOS_PATH) / WASMTIME_REPO2
        wasmtime2_config = WasmtimeConfig.from_cli_namespace_object(args.wasmtime2)
        wasmtime2 = self.prepare_wasmtime(
            wasmtime2_repo_path, args.revision2, wasmtime2_config
        )

        suite_files = {}

        # Build benchmarks in each suite
        for suite in config.BENCHMARK_SUITES:
            suite_path = Path(suite.path)
            check(
                suite_path.exists(),
                f"Found benchmark suite with non-existing path {suite_path}",
            )

            if suite.hasMakeBenchmark():
                # The make files may not be fully aware that various tools changed
                run_check("make clean", cwd=suite_path)

            benchmark_pairs: List[Tuple[Benchmark, List[str], Path]] = []
            for b in suite.benchmarks:
                benchmark_pseudopath = suite_path / b.name

                benchmark_filters = args.filter
                if benchmark_filters and not any(
                    map(benchmark_pseudopath.match, benchmark_filters)
                ):
                    log(
                        f"Skipping benchmark {benchmark_pseudopath} as it does not match filter"
                    )
                    continue

                benchmark_output_dir = Path("out") / suite_path / b.name
                benchmark_output_dir_rev1 = benchmark_output_dir / "rev1"
                benchmark_output_dir_rev2 = benchmark_output_dir / "rev2"
                benchmark_output_dir_rev1.mkdir(parents=True, exist_ok=True)
                benchmark_output_dir_rev2.mkdir(parents=True, exist_ok=True)

                command1 = b.prepare(
                    suite,
                    benchmark_output_dir_rev1,
                    mimalloc=mimalloc,
                    reference_interpreter=interpreter,
                    binaryen=binaryen,
                    wasmtime=wasmtime1,
                )
                command2 = b.prepare(
                    suite,
                    benchmark_output_dir_rev2,
                    mimalloc=mimalloc,
                    reference_interpreter=interpreter,
                    binaryen=binaryen,
                    wasmtime=wasmtime2,
                )
                json_path = benchmark_output_dir / "results.json"

                benchmark_pairs.append((b, [command1, command2], json_path))

            if benchmark_pairs:
                suite_files[suite.path] = benchmark_pairs

        # Perform actual benchmarking in each suite:
        for suite_path, benchmark_pairs in suite_files.items():
            for bench, commands, json_path in benchmark_pairs:
                Hyperfine.run(commands, json_export_path=json_path)

        # Print results from each suite
        print(
            "Results: (for each benchmark, showing mean runtime in rev1 / mean runtime in rev2)"
        )
        for suite_path, benchmark_pairs in suite_files.items():
            print(f"Suite: {suite_path}")
            for bench, _, json_path in benchmark_pairs:
                with open(json_path, "r") as f:
                    results = json.load(f)["results"]
                    rev1_mean = results[0]["mean"]
                    rev2_mean = results[1]["mean"]
                    print(f"{bench.name}: {rev1_mean / rev2_mean}")

    @staticmethod
    def addSubparser(subparsers, namespace):
        parser = subparsers.add_parser(
            "compare-revs",
            help="Run benchmarks using two wasmtime revisions and compare results",
        )
        parser.add_argument(
            "--filter",
            help="Only run benchmarks that match this glob pattern",
            action="append",
        )
        parser.add_argument(
            "--allow-dirty",
            help="Allows the benchfx, binaryen, spec and wasmtime repos to be dirty",
        )
        parser.add_argument(
            "revision1", help="First Wasmtime revision to use in the comparison"
        )
        parser.add_argument(
            "revision2", help="Second Wasmtime revision to use in the comparison"
        )

        namespace.wasmtime1 = argparse.Namespace()
        add_wasmtime_args_to_subparser(
            parser, namespace.wasmtime1, suffix="1", desc="wasmtime revision 1"
        )

        namespace.wasmtime2 = argparse.Namespace()
        add_wasmtime_args_to_subparser(
            parser, namespace.wasmtime2, suffix="2", desc="wasmtime revision 2"
        )


class ForwardChildNamespaceAction(argparse.Action):
    def __init__(self, option_strings, dest, namespace, forward_to, *args, **kwargs):
        super(ForwardChildNamespaceAction, self).__init__(
            option_strings=option_strings, dest=dest, *args, **kwargs
        )
        self.namespace = namespace
        self.forward = forward_to(
            option_strings=option_strings, dest=dest, *args, **kwargs
        )

    def __call__(self, parser, _namespace, values, option_string=None):
        print(self.namespace)
        self.forward.__call__(parser, self.namespace, values, option_string)


def main():
    parser = argparse.ArgumentParser(prog="bench")
    namespace = argparse.Namespace()

    subcommands = [Run, CompareRevs]
    subparsers = parser.add_subparsers(
        title="Available subcommands", dest="command", required=True
    )

    # This is supposed to make the  default command "run", but doesn't quite work
    # parser.set_defaults(command = "run")

    for sc in subcommands:
        sc.addSubparser(subparsers, namespace)

    args = parser.parse_args(namespace=namespace)
    print(args)

    match args.command:
        case "run":
            Run().execute(args)
        case "compare-revs":
            CompareRevs().execute(args)


if __name__ == "__main__":
    main()
