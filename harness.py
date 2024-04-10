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
        config: "Config",
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
        config,
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
        run_check("make clean", cwd=suite_path)
        run_check(
            ["make", wasm_file]
            + [
                f"WASM_INTERP={interpreter}",
                f"WASM_MERGE={wasm_merge}",
                f"WASM_OPT={wasm_opt}",
            ],
            cwd=suite_path,
        )

        wasmtime.compileWasm(config, suite_path / wasm_file, output_dir / cwasm_file)

        run_command = wasmtime.shellCommandCwasmRun(config, output_dir / cwasm_file)
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
        config,
        mimalloc,
        reference_interpreter,
        binaryen,
        wasmtime,
    ):
        suite_path = Path(suite.path)
        wat_path = suite_path / (self.file + ".wat")
        cwasm_path = output_dir / (self.file + ".cwasm")

        wasmtime.compileWasm(config, wat_path, cwasm_path)

        run_command = wasmtime.shellCommandCwasmRun(
            config, cwasm_path, invoke_function=self.invoke
        )

        return mimalloc.add_to_shell_commmand(run_command)


@typechecked
@dataclass
class Suite:
    path: str
    benchmarks: List[Benchmark]


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
        cpus = multiprocessing.cpu_count()
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
class Config:
    use_mimalloc: bool = True

    # Wasmtime specific:
    wasmtime_cargo_build_args: Optional[List[str]] = None
    wasmtime_compile_args: Optional[List[str]] = None
    wasmtime_run_args: Optional[List[str]] = None

    @staticmethod
    def fromCliNamespaceObject(namespace, revision_qualifier=None) -> "Config":
        prefix = revision_qualifier + "_" if revision_qualifier else ""

        def parseYN(attr_name: str, attr_value: str) -> bool:
            match attr_value.lower():
                case "y":
                    return True
                case "n":
                    return False
                case _:
                    raise HarnessError(
                        "Expected 'y' or 'n' for {attr_name}, got {attr_value} instead"
                    )

        def splitMultiArgumentString(_attr_name: str, attr_value: str):
            return shlex.split(attr_value)

        prop_parsers = {
            ("use_mimalloc", parseYN),
            ("wasmtime_cargo_build_args", splitMultiArgumentString),
            ("wasmtime_compile_args", splitMultiArgumentString),
            (
                "wasmtime_run_args",
                splitMultiArgumentString,
            ),
        }

        config = Config()

        for prop_name, parser in prop_parsers:
            qualified_attr_name = prefix + prop_name
            attr_val = getattr(namespace, qualified_attr_name, None)
            val = parser(qualified_attr_name, attr_val) if attr_val else None
            setattr(config, prop_name, val)

        return config

    def _getOrDefault(self, prop, default):
        return prop if prop is not None else default

    def getWasmtimeCargoBuildArgsOrDefault(self) -> List[str]:
        return self._getOrDefault(
            self.wasmtime_cargo_build_args, config.WASMTIME_CARGO_BUILD_ARGS
        )

    def getWasmtimeCompileArgsOrDefault(self) -> List[str]:
        return self._getOrDefault(
            self.wasmtime_compile_args, config.WASMTIME_COMPILE_ARGS
        )

    def getWasmtimeRunArgsOrDefault(self) -> List[str]:
        return self._getOrDefault(self.wasmtime_run_args, config.WASMTIME_RUN_ARGS)


class Wasmtime:
    def __init__(self, path: Path, release_build=True):
        self.path = path
        self.release_build = release_build
        self.config = config

    def executable_path(self):
        if self.release_build:
            return os.path.join(self.path, "target/release/wasmtime")
        else:
            return os.path.join(self.path, "target/debug/wasmtime")

    def build(self, configuration: Config):
        # For the tim
        release = ["--release"] if self.release_build else []

        if configuration.wasmtime_cargo_build_args is not None:
            log(
                "Overriding cargo builds args with "
                + str(configuration.wasmtime_cargo_build_args)
            )
        cargo_build_args = configuration.getWasmtimeCargoBuildArgsOrDefault()

        run_check(
            ["cargo", "build"] + release + cargo_build_args,
            "Failed to build wasmtime",
            self.path,
        )

    def compileWasm(
        self, configuration: Config, input_wasm_path: Path, output_cwasm_path: Path
    ):
        wasmtime = self.executable_path()
        command = "compile"

        if configuration.wasmtime_compile_args is not None:
            log(
                "Overriding wasmtime compile args with "
                + str(configuration.wasmtime_compile_args)
            )
        wasmtime_compile_args = configuration.getWasmtimeCompileArgsOrDefault()

        run_check(
            [wasmtime, "compile"]
            + wasmtime_compile_args
            + [
                f"--output={output_cwasm_path.absolute()}",
                str(input_wasm_path.absolute()),
            ],
            f"Failed to compile {input_wasm_path} to  {output_cwasm_path}",
        )

    def shellCommandCwasmRun(
        self,
        configuration: Config,
        cwasm_path: Path,
        invoke_function=None,
    ):
        wasmtime = self.executable_path()
        command = "run"

        if configuration.wasmtime_run_args is not None:
            log(
                "Overriding wasmtime run args with "
                + str(configuration.wasmtime_run_args)
            )
        wasmtime_run_args = configuration.getWasmtimeRunArgsOrDefault()

        invoke_args = []
        if invoke_function:
            invoke_args += [f"--invoke={invoke_function}"]

        cmd = (
            [wasmtime, "run", "--allow-precompiled"]
            + wasmtime_run_args
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
        check(
            path.exists(),
            f"Expecting git repo at {path}, but the folder does not exist",
        )
        check(
            GitRepo.isRootOfRepoOrWorktree(path),
            f"{path} is not the root of a git repository (or a worktree of a repository)",
        )
        self.path = path

    @staticmethod
    def initWithRemotes(path: Path, github_remotes: List[Tuple[str, str]]) -> "GitRepo":
        check(
            not path.exists(),
            f"Asked to init a git repo at {path}, but the folder exists",
        )

        run_check(f"mkdir -p '{path}'")
        run_check(f"git init '{path}'")

        repo = GitRepo(path)

        for user_name, repo_name in github_remotes:
            github_repo_url = f"https://github.com/{user_name}/{repo_name}"
            repo._git(f"remote add '{user_name}' '{github_repo_url}'")

        repo._git("fetch --all")
        return repo

    def hasRev(self, rev: str) -> bool:
        rev = rev + "^{commit}"
        res = run(f"git rev-parse --verify '{rev}'", cwd=self.path)
        return res.returncode == 0

    @staticmethod
    def isRootOfRepoOrWorktree(path):
        res = run("git rev-parse --show-toplevel", cwd=path)
        if res.returncode != 0:
            return False
        toplevel_path = res.stdout.strip()
        return Path(toplevel_path).absolute() == Path(path).absolute()

    # This uses run_check, use only for git commands that are not allowed to fail
    def _git(self, args):
        return run_check("git " + args, cwd=self.path)

    def isDirty(self, allow_untracked=True):
        untracked_mode = "no" if allow_untracked else "normal"
        res = self._git(f"status --untracked-files={untracked_mode} --porcelain")
        # the --porcelain option makes the output stable, where no output means clean repository
        return res.stdout.strip() != ""

    def checkout(self, revision):
        check(
            not self.isDirty(allow_untracked=False),
            f"Cannot checkout git repo at {self.path} to {revision} because it is dirty",
        )
        self._git(f"switch --detach {revision}")
        self._git("submodule update --init --recursive")

        # We are very strict about changed and untracked files, to avoid
        # subsequent failures: We required above that the repo is clean, not
        # even having untracked files. After checking out, we then remove all
        # newly untracked files, too.
        # NB: Need to provide --force twice in order to delete non-empty directories
        self._git("clean -d --force --force")


# Builds the reference interpreter and binaryen
@typechecked
def buildCommonTools() -> Tuple[Mimalloc, ReferenceInterpreter, Binaryen]:
    repos_path = Path(REPOS_PATH)

    # Mimalloc setup
    mimalloc_repo_path = repos_path / MIMALLOC_REPO
    mimalloc_repo = GitRepo(mimalloc_repo_path)
    mimalloc_repo.checkout(config.MIMALLOC_COMMIT)
    mimalloc = Mimalloc(mimalloc_repo_path)
    mimalloc.build()

    # Reference interpreter setup
    spec_repo_path = repos_path / SPEC_REPO
    log(f"spec repo expected at {spec_repo_path}")
    spec_repo = GitRepo(spec_repo_path)
    log(f"spec repo dirty? {spec_repo.isDirty()}")
    spec_repo.checkout(config.SPEC_COMMIT)
    interpreter_path = Path(os.path.join(spec_repo_path, "interpreter"))
    interpreter: ReferenceInterpreter = ReferenceInterpreter(interpreter_path)
    interpreter.build()

    # Binaryen setup
    binaryen_repo_path = repos_path / BINARYEN_REPO
    log(f"binaryen repo expected at {binaryen_repo_path}")
    binaryen_repo = GitRepo(binaryen_repo_path)
    log(f"binaryen repo dirty? {binaryen_repo.isDirty()}")
    binaryen_repo.checkout(config.BINARYEN_COMMIT)
    binaryen = Binaryen(binaryen_repo_path)
    binaryen.build()

    return (mimalloc, interpreter, binaryen)


@typechecked
def addRevisionSpecificArgsToSubparser(
    subparser,
    revision_qualifier: Optional[str] = None,
    desc: Optional[str] = None,
):
    # wasmtime = "wasmtime" + ("" if suffix == None else suffix)
    desc = f" for {desc}" if desc else ""
    rev_prefix = revision_qualifier + "-" if revision_qualifier else ""
    subparser.add_argument(
        f"--{rev_prefix}wasmtime-cargo-build-args",
        help=f"""Instead of config.WASMTIME_CARGO_BUILD_ARGS, use these
        arguments building wasmtime{desc}.""",
        action="store",
    )
    subparser.add_argument(
        f"--{rev_prefix}wasmtime-run-args",
        help=f"""Instead of config.WASMTIME_RUN_ARGS, use these arguments when
        executing 'wasmtime run'{desc}. May be unsupported for certain
        benchmarks.""",
        action="store",
    )
    subparser.add_argument(
        f"--{rev_prefix}wasmtime-compile-args",
        help=f"""Instead of config.WASMTIME_RUN_ARGS, use these arguments when
        executing 'wasmtime compile'{desc}. May be unsupported for certain
        benchmarks.""",
        action="store",
    )
    subparser.add_argument(
        f"--{rev_prefix}use-mimalloc",
        help=f"""Should we use mimalloc instead of standard system allocator
        when running benchmarks{desc} (allowed values: y/n, default: y)""",
        action="store",
        default="y",
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

        (mimalloc, interpreter, binaryen) = buildCommonTools()

        configuration = Config.fromCliNamespaceObject(args)

        # Wasmtime setup
        wasmtime_repo_path = Path(REPOS_PATH) / WASMTIME_REPO1
        log(f"wasmtime repo expected at {wasmtime_repo_path}")
        wasmtime_repo = GitRepo(wasmtime_repo_path)
        log(f"wasmtime repo dirty? {wasmtime_repo.isDirty()}")
        wasmtime_repo.checkout(config.WASMTIME_COMMIT)
        wasmtime = Wasmtime(wasmtime_repo_path)

        wasmtime.build(configuration)

        suite_shell_commands = {}

        # Build benchmarks in each suite
        for suite in config.BENCHMARK_SUITES:
            suite_path = Path(suite.path)
            check(
                suite_path.exists(),
                f"Found benchmark suite with non-existing path {suite_path}",
            )

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
                        configuration,
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
        addRevisionSpecificArgsToSubparser(parser)


@typechecked
class CompareRevs:
    def __init__(self):
        pass

    def prepare_wasmtime(self, repo_path: Path, revision: str, configuration: Config):
        wasmtime_repo = GitRepo(repo_path)
        log(f"wasmtime repo dirty? {wasmtime_repo.isDirty()}")
        wasmtime_repo.checkout(revision)
        wasmtime = Wasmtime(repo_path)
        wasmtime.build(configuration)
        return wasmtime

    def execute(self, args):
        print("compare-revs is running")

        (mimalloc, interpreter, binaryen) = buildCommonTools()

        rev1_config = Config.fromCliNamespaceObject(args, revision_qualifier="rev1")
        rev2_config = Config.fromCliNamespaceObject(args, revision_qualifier="rev2")

        # Wasmtime1 setup
        wasmtime1_repo_path = Path(REPOS_PATH) / WASMTIME_REPO1
        wasmtime1 = self.prepare_wasmtime(
            wasmtime1_repo_path, args.revision1, rev1_config
        )

        # Wasmtime2 setup
        wasmtime2_repo_path = Path(REPOS_PATH) / WASMTIME_REPO2
        wasmtime2 = self.prepare_wasmtime(
            wasmtime2_repo_path, args.revision2, rev2_config
        )

        suite_files = {}

        # Build benchmarks in each suite
        for suite in config.BENCHMARK_SUITES:
            suite_path = Path(suite.path)
            check(
                suite_path.exists(),
                f"Found benchmark suite with non-existing path {suite_path}",
            )

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
                    rev1_config,
                    mimalloc=mimalloc,
                    reference_interpreter=interpreter,
                    binaryen=binaryen,
                    wasmtime=wasmtime1,
                )
                command2 = b.prepare(
                    suite,
                    benchmark_output_dir_rev2,
                    rev1_config,
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

        addRevisionSpecificArgsToSubparser(
            parser, revision_qualifier="rev1", desc="revision 1"
        )
        addRevisionSpecificArgsToSubparser(
            parser, revision_qualifier="rev2", desc="revision 2"
        )


@typechecked
class Setup:
    def __init__(self):
        pass

    def make(self):
        pass

    @staticmethod
    def addSubparser(subparsers, namespace):
        parser = subparsers.add_parser(
            "setup",
            help="Sets up the repos for the dependencies used by the harness",
        )

    def execute(self, args):
        repos = [SPEC_REPO, BINARYEN_REPO, MIMALLOC_REPO]

        def setup_repo(repo_name, expected_root_commit, remotes):
            path = Path(REPOS_PATH) / repo
            if path.exists():
                r = GitRepo(path)
                check(
                    r.hasRev(expected_root_commit),
                    f"""Error while setting up {repo} repo at {path}: It exists,
                    but does not contain commit {expected_root_commit}, which we
                    expected to find there""",
                )

            else:
                GitRepo.initWithRemotes(path, remotes)

        for repo in repos:
            expected_root_commit, remotes = config.GITHUB_REPOS[repo]
            setup_repo(repo, expected_root_commit, remotes)

        # # We have multiple wasmtime repos
        wasmtime_repos = [WASMTIME_REPO1, WASMTIME_REPO2]
        wasmtime_github_repos = config.GITHUB_REPOS["wasmtime"]
        for repo in wasmtime_repos:
            expected_root_commit, remotes = wasmtime_github_repos
            setup_repo(repo, expected_root_commit, remotes)


def checkBuildToolsPresent():
    tools = ["make", "cmake", "dune"]
    for tool in tools:
        run_check(
            f"command -v {tool}",
            f"Could not find '{tool}' executable in $PATH, which this the benchmark harness requires",
        )


def main():
    checkBuildToolsPresent()

    parser = argparse.ArgumentParser(prog="bench")
    namespace = argparse.Namespace()

    subcommands = {"run": Run, "compare-revs": CompareRevs, "setup": Setup}

    subparsers = parser.add_subparsers(
        title="Available subcommands", dest="command", required=True
    )

    # This is supposed to make the  default command "run", but doesn't quite work
    # parser.set_defaults(command = "run")

    for name, class_ in subcommands.items():
        class_.addSubparser(subparsers, namespace)

    args = parser.parse_args(namespace=namespace)
    print(args)

    Class_ = subcommands[args.command]
    Class_().execute(args)


if __name__ == "__main__":
    main()
