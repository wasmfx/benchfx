#!/usr/bin/env python3

import argparse
import config
import json
import multiprocessing
import os
import shlex
import subprocess
import sys
import traceback

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional


WASI_SDK_BASE_PATH = Path("tools/wasi-sdk")
REPOS_PATH = Path("tools/repos")

SPEC_REPO = "spec"
BINARYEN_REPO = "binaryen"
MIMALLOC_REPO = "mimalloc"
WASMTIME_REPO1 = "wasmtime1"
WASMTIME_REPO2 = "wasmtime2"


class HarnessError(Exception):
    def __init__(self, msg):
        super().__init__(msg)


def check(condition, msg):
    if not condition:
        raise HarnessError(msg)


logLevel = 0


def logProcessOutput(msg, sep=None):
    if logLevel > 1:
        print(msg, sep=sep)


def logMsg(msg, sep=None):
    if logLevel > 0:
        print(msg, sep=sep)


@dataclass
class Suite:
    """A suite is a collection of logically related benchmarks.

    It is uniquely identified by the path to a subfolder within the benchfx
    directory.

    Each suite's benchmarks will be compared against each other when using the
    'run' subcommand of the benchnmark harness.
    """

    path: str
    benchmarks: List["Benchmark"]


@dataclass
class Benchmark:
    """Definition of a benchmark.

    Each benchmark within a `Suite` must have a unique `name`.

    The subclasses of `Benchmark` represent how a benchmark is actually built
    and run, by overriding the `prepare` method.
    """

    name: str

    def prepare(
        self,
        suite: Suite,
        output_dir: Path,
        config: "Config",
        mimalloc: "Mimalloc",
        wasi_sdk: "WasiSdk",
        reference_interpreter: "ReferenceInterpreter",
        binaryen: "Binaryen",
        wasmtime: "Wasmtime",
    ) -> str:
        """Perform all necessary preparation work, then return a shell command for actually running the benchmark.

        Some benchmarks may require some preparation work before actually being
        executed, such as running a Makefile or performing any other kind of
        compilation work specific to that particular benchmark.
        All tools (binaryen, wasmtime, etc) are already compiled at this point
        and may be used.

        For each such "kind" of benchmark, we have a separate subclass of
        `Benchmark`, whose main differentiation is their implementation of this
        method.

        Each call to `prepare` receives a fresh, empty `output_dir`, where built
        artifacts (compiled wasm or cwasm files, etc) may be stored.
        The function then returns a single shell command. This shell command
        denotes how to run the benchmark, and will be fed into hyperfine
        verbatim.
        """

        raise HarnessError("Override me!")

    def pseudoPath(self, enclosing_suite) -> Path:
        """Returns a "pseudo-path" for this benchmark for filtering purposes.

        It is obtained by using the benchmark's name as a file name, appearing
        in the suite's directory,
        """

        return Path(enclosing_suite.path) / self.name

    def matchesAnyFilter(self, enclosing_suite: Suite, filter_globs: List[str]) -> bool:
        pseudo_path = self.pseudoPath(enclosing_suite)
        return any(map(pseudo_path.match, filter_globs))


class MakeWasm(Benchmark):
    """Benchmarks that use the make.generic.config Makefile

    Attributes
    ----------
    file : str
        The file in the suite folder to call the Makefile on, without its
        extension
    invoke : Optional[str]
        If given, name of function in final module to invoke
    """

    def __init__(
        self, file: str, name: Optional[str] = None, invoke: Optional[str] = None
    ):
        self.file = file
        self.invoke = invoke
        super().__init__(name or file)

    def prepare(
        self,
        suite,
        output_dir: Path,
        config,
        mimalloc,
        wasi_sdk,
        reference_interpreter,
        binaryen,
        wasmtime,
    ):
        wasm_file = self.file + ".wasm"
        cwasm_file = self.file + ".cwasm"
        suite_path = Path(suite.path)
        interpreter = Path(reference_interpreter.executablePath()).absolute()
        wasi_cc = wasi_sdk.clangPath().absolute()
        wasm_merge = binaryen.wasmMergeExecutablePath().absolute()
        wasm_opt = binaryen.wasmOptExecutablePath().absolute()
        runCheck("make clean", cwd=suite_path)
        runCheck(
            ["make", wasm_file]
            + [
                f"WASICC={wasi_cc}",
                f"WASM_INTERP={interpreter}",
                f"WASM_MERGE={wasm_merge}",
                f"WASM_OPT={wasm_opt}",
            ],
            cwd=suite_path,
        )

        wasmtime.compileWasm(config, suite_path / wasm_file, output_dir / cwasm_file)

        run_command = wasmtime.shellCommandCwasmRun(config, output_dir / cwasm_file)
        return mimalloc.addToShellCommmand(run_command)


class Wat(Benchmark):
    """Benchmarks that simply run a dedicated function in a wat file

    Attributes
    ----------
    file : str
        The file in the suite folder to run, without its extension
    invoke : Optional[str]
        If given, name of function in final module to invoke
    """

    def __init__(self, file, name=None, invoke=None):
        self.file: str = file
        self.invoke: Optional[str] = invoke
        super().__init__(name or file)

    def prepare(
        self,
        suite,
        output_dir: Path,
        config,
        mimalloc,
        wasi_sdk,
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

        return mimalloc.addToShellCommmand(run_command)


def run(cmd: str | List[str], cwd=None) -> subprocess.CompletedProcess:
    if isinstance(cmd, list):
        command = shlex.join(cmd)
    else:
        command = cmd
    cwd_msg = f" in directory {cwd}" if cwd is not None else ""
    logMsg(f"Running command{cwd_msg}:\n{command}")
    res = subprocess.run(command, cwd=cwd, capture_output=True, shell=True, text=True)
    logProcessOutput("STDOUT:\n" + res.stdout, sep="")
    logProcessOutput("STDERR:\n" + res.stderr, sep="")
    return res


# Like run, but checks that the command finished with non-zero exit code.
def runCheck(cmd, msg=None, cwd=None):
    result = run(cmd, cwd)
    msg = msg or f"Running {cmd} in {cwd or os.getcwd()} failed"
    check(
        result.returncode == 0,
        msg
        + f"\nDetails:\nFailed command: {cmd}\nStdout:\n{result.stdout}\nStderr:\n{result.stderr}",
    )
    return result


@dataclass
class Binaryen:
    path: Path

    def build(self):
        cpus = multiprocessing.cpu_count()
        runCheck("cmake .", msg="cmake for binaryen failed", cwd=self.path)
        runCheck(f"make -j {cpus}", msg="building binaryen failed", cwd=self.path)

    def wasmMergeExecutablePath(self) -> Path:
        return self.path / "bin" / "wasm-merge"

    def wasmOptExecutablePath(self) -> Path:
        return self.path / "bin" / "wasm-opt"


class Mimalloc:
    def __init__(self, path: Path):
        self.path = path

    def build(self):
        cpus = multiprocessing.cpu_count()
        runCheck("mkdir -p out", cwd=self.path)
        out_dir = self.path / "out"
        runCheck("cmake ..", msg="cmake for mimalloc failed", cwd=out_dir)
        runCheck(f"make -j {cpus}", msg="building mimalloc failed", cwd=out_dir)

    def libmimallocPath(self) -> Path:
        return self.path / "out" / "libmimalloc.so"

    def addToShellCommmand(self, shell_command: str):
        "Given a shell command, extends it with an appropriate LD_PRELOAD clause to use mimalloc"

        escaped_path = shlex.quote(str(self.libmimallocPath()))
        return f"LD_PRELOAD={escaped_path} {shell_command}"


@dataclass
class ReferenceInterpreter:
    path: Path

    def executablePath(self) -> Path:
        return self.path / "wasm"

    def build(self):
        runCheck("make", "Failed to build reference interpreter", self.path)

    def compile(self, input_path: Path, output_path: Path):
        wasm = str(self.executablePath().absolute())
        input_absolute = str(input_path.absolute())
        output_absolute = str(output_path.absolute())
        runCheck(f"{wasm} -d '{input_absolute}' -o '{output_absolute}'", self.path)


@dataclass
class Config:
    """Configuration of various tools for each benchmark run.

    This serves two purposes:
    1. A more structured representation of the most important CLI config
    options, showing how they should be parsed and getting their defaults.

    2. For those options that exist twice for 'compare-revs' command, implements
    extracting one `Config` object for each of the two revisions.
    """

    use_mimalloc: bool = True

    # Wasmtime specific:
    wasmtime_cargo_build_args: Optional[List[str]] = None
    wasmtime_compile_args: Optional[List[str]] = None
    wasmtime_run_args: Optional[List[str]] = None

    @staticmethod
    def fromCliArgs(cli_args: argparse.Namespace, revision_qualifier=None) -> "Config":
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
            attr_val = getattr(cli_args, qualified_attr_name, None)
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

    def executablePath(self) -> Path:
        if self.release_build:
            return self.path / "target/release/wasmtime"
        else:
            return self.path / "target/debug/wasmtime"

    def build(self, configuration: Config):
        # For the tim
        release = ["--release"] if self.release_build else []

        if configuration.wasmtime_cargo_build_args is not None:
            logMsg(
                "Overriding cargo builds args with "
                + str(configuration.wasmtime_cargo_build_args)
            )
        cargo_build_args = configuration.getWasmtimeCargoBuildArgsOrDefault()

        runCheck(
            ["cargo", "build"] + release + cargo_build_args,
            "Failed to build wasmtime",
            self.path,
        )

    def compileWasm(
        self, configuration: Config, input_wasm_path: Path, output_cwasm_path: Path
    ):
        wasmtime = str(self.executablePath())
        command = "compile"

        if configuration.wasmtime_compile_args is not None:
            logMsg(
                "Overriding wasmtime compile args with "
                + str(configuration.wasmtime_compile_args)
            )
        wasmtime_compile_args = configuration.getWasmtimeCompileArgsOrDefault()

        runCheck(
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
        wasmtime = str(self.executablePath())
        command = "run"

        if configuration.wasmtime_run_args is not None:
            logMsg(
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


class Hyperfine:
    @staticmethod
    def run(
        shell_commands: List[str],
        print_stdout=False,
        warmup_count=3,
        json_export_path=None,
    ):
        args = ["hyperfine", f"--warmup={warmup_count}"]
        if json_export_path:
            args += [f"--export-json={json_export_path}"]
        result = runCheck(args + shell_commands)

        if print_stdout:
            global logLevel
            # Don't print if we are already printing all process output anyway
            if logLevel <= 1:
                print(result.stdout)


@dataclass
class WasiSdk:
    path: Path
    wasi_version: str

    RELEASE_DOWNLOAD_FOLDER_TEMPLATE = "https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-{wasi_version}/"
    RELEASE_ARCHIVE_NAME_TEMPLATE = "wasi-sdk-{wasi_version_full}-linux.tar.gz"

    @staticmethod
    def forVersion(wasi_version: str, base_folder: Path) -> "WasiSdk":
        wasi_version_full = WasiSdk._fullVersion(wasi_version)
        untared_folder = f"wasi-sdk-{wasi_version_full}"

        return WasiSdk(base_folder / untared_folder, wasi_version)

    @staticmethod
    def _fullVersion(wasi_version: str):
        return f"{wasi_version}.0"

    @staticmethod
    def _release_tar_file_name(wasi_version: str) -> str:
        wasi_version_full = WasiSdk._fullVersion(wasi_version)
        return WasiSdk.RELEASE_ARCHIVE_NAME_TEMPLATE.format(
            wasi_version=wasi_version, wasi_version_full=wasi_version_full
        )

    @staticmethod
    def download(wasi_version, base_folder: Path):
        wasi_version_full = WasiSdk._fullVersion(wasi_version)
        base_url = folder_url = WasiSdk.RELEASE_DOWNLOAD_FOLDER_TEMPLATE.format(
            wasi_version=wasi_version, wasi_version_full=wasi_version_full
        )
        file_name = WasiSdk._release_tar_file_name(wasi_version)

        full_url = folder_url + file_name

        runCheck(f"mkdir -p '{base_folder}'")
        runCheck(
            f"wget '{full_url}'",
            cwd=base_folder,
            msg="Failed to download WASI SDK from {full_url}",
        )
        runCheck(f"tar xvf '{file_name}'", cwd=base_folder)

    def clangPath(self) -> Path:
        return self.path / "bin" / "clang"

    @staticmethod
    def isVersionInstalled(wasi_version: str, base_folder: Path) -> bool:
        return WasiSdk.forVersion(wasi_version, base_folder).clangPath().exists()


# Helper class for working at a git repo (or a working tree of a git repo) at a given path.
# This is mostly a wrapper around GitPyhton's git.Repo type
class GitRepo:
    def __init__(self, path: Path):
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

        runCheck(f"mkdir -p '{path}'")
        runCheck(f"git init '{path}'")

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
        return runCheck("git " + args, cwd=self.path)

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

    def addWorktree(self, newWorktreePath: Path):
        check(
            not newWorktreePath.exists(),
            "Cannot create new git worktree at {newWorktreePath}, path exists",
        )
        self._git(f"worktree add --detach '{str(newWorktreePath.absolute())}'")


def prepareCommonTools() -> Tuple[WasiSdk, Mimalloc, ReferenceInterpreter, Binaryen]:
    "Prepares almost all the external tools EXCEPT wasmtime, which we compile elsewhere."

    # We should have already checked that the WASI SDK binaries have been
    # downloaded
    check(
        WasiSdk.isVersionInstalled(config.WASI_SDK_VERSION, WASI_SDK_BASE_PATH),
        "Wasi SDK missing",
    )
    wasi_sdk = WasiSdk.forVersion(config.WASI_SDK_VERSION, WASI_SDK_BASE_PATH)

    # Mimalloc setup
    mimalloc_repo_path = REPOS_PATH / MIMALLOC_REPO
    mimalloc_repo = GitRepo(mimalloc_repo_path)
    mimalloc_repo.checkout(config.MIMALLOC_COMMIT)
    mimalloc = Mimalloc(mimalloc_repo_path)
    mimalloc.build()

    # Reference interpreter setup
    spec_repo_path = REPOS_PATH / SPEC_REPO
    logMsg(f"spec repo expected at {spec_repo_path}")
    spec_repo = GitRepo(spec_repo_path)
    logMsg(f"spec repo dirty? {spec_repo.isDirty()}")
    spec_repo.checkout(config.SPEC_COMMIT)
    interpreter_path = Path(os.path.join(spec_repo_path, "interpreter"))
    interpreter: ReferenceInterpreter = ReferenceInterpreter(interpreter_path)
    interpreter.build()

    # Binaryen setup
    binaryen_repo_path = REPOS_PATH / BINARYEN_REPO
    logMsg(f"binaryen repo expected at {binaryen_repo_path}")
    binaryen_repo = GitRepo(binaryen_repo_path)
    logMsg(f"binaryen repo dirty? {binaryen_repo.isDirty()}")
    binaryen_repo.checkout(config.BINARYEN_COMMIT)
    binaryen = Binaryen(binaryen_repo_path)
    binaryen.build()

    return (wasi_sdk, mimalloc, interpreter, binaryen)


def addRevisionSpecificArgsToSubparser(
    subparser,
    revision_qualifier: Optional[str] = None,
    desc: Optional[str] = None,
):
    """Adds a set of arguments to the CLI parser that exist once for the 'run' subcommand but twice for 'compare-revs'.

    In the former case, `revision_qualifier` and `desc` should be None.
    Otherwise, `revision_qualifier` is something like `rev1` and the final name
    of each CLI argument will be prefixed with it. `desc` is then something like
    "revision 1` and gets spliced into the help string of each argument.
    """

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


def checkBenchFxRepoClean():
    benchfx_repo = GitRepo(Path(__file__).parent)
    check(
        not benchfx_repo.isDirty(),
        "Cannot run benchmarks while benchfx repo is dirty. Consider passing --allow-dirty flag.",
    )


def checkDependenciesPresent(need_second_wasmtime_repo):
    def checkExternalToolsPresent():
        tools = ["make", "cmake", "dune", "hyperfine"]
        for tool in tools:
            runCheck(
                f"command -v {tool}",
                f"Could not find '{tool}' executable in $PATH, which this the benchmark harness requires",
            )

    def checkToolReposPresent(need_second_wasmtime_repo):
        def checkRepo(repo_name, expected_root_commit):
            path = REPOS_PATH / repo
            check(
                path.exists(),
                f"Expecting {repo_name} repository at {str(path)}, but the folder does not exist. Consider running 'setup' subcommand.",
            )
            r = GitRepo(path)
            check(
                r.hasRev(expected_root_commit),
                f"Repo {repo}  at {path} exists, but does not contain commit {expected_root_commit}, which we expected to find there. Consider running 'setup' subcommand.",
            )

        repos = [SPEC_REPO, BINARYEN_REPO, MIMALLOC_REPO]

        for repo in repos:
            expected_root_commit, remotes = config.GITHUB_REPOS[repo]
            checkRepo(repo, expected_root_commit)

        wasmtime_repos = (
            [WASMTIME_REPO1, WASMTIME_REPO2]
            if need_second_wasmtime_repo
            else [WASMTIME_REPO1]
        )
        wasmtime_root_commit = config.GITHUB_REPOS["wasmtime"][0]
        for repo in wasmtime_repos:
            checkRepo(repo, wasmtime_root_commit)

    check(
        WasiSdk.isVersionInstalled(config.WASI_SDK_VERSION, WASI_SDK_BASE_PATH),
        f"WASI SDK version {config.WASI_SDK_VERSION} not installed. Consider running 'setup' subcommand.",
    )
    checkExternalToolsPresent()
    checkToolReposPresent(need_second_wasmtime_repo)


# The run command, which just runs the benchmarks
class SubcommandRun:
    """Implements the 'run' subcommand.

    Compares the benchmarks within each suite against each other.
    """

    @staticmethod
    def addSubparser(subparsers):
        parser = subparsers.add_parser("run", help="runs benchmarks (used by default)")

        parser.add_argument(
            "--filter",
            help="Only run benchmarks that match this glob pattern",
            action="append",
        )
        parser.add_argument(
            "--allow-dirty",
            help="Allows the benchfx repo to be dirty when running benchmarks",
            action="store_true",
            default=False,
        )

        addRevisionSpecificArgsToSubparser(parser)

    def execute(self, cli_args: argparse.Namespace):
        if not cli_args.allow_dirty:
            checkBenchFxRepoClean()

        checkDependenciesPresent(need_second_wasmtime_repo=False)

        (wasi_sdk, mimalloc, interpreter, binaryen) = prepareCommonTools()

        configuration = Config.fromCliArgs(cli_args)

        # Wasmtime setup
        wasmtime_repo_path = REPOS_PATH / WASMTIME_REPO1
        logMsg(f"wasmtime repo expected at {wasmtime_repo_path}")
        wasmtime_repo = GitRepo(wasmtime_repo_path)
        logMsg(f"wasmtime repo dirty? {wasmtime_repo.isDirty()}")
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
                benchmark_filters = cli_args.filter
                if benchmark_filters and not b.matchesAnyFilter(
                    suite, benchmark_filters
                ):
                    logMsg(
                        f"Skipping benchmark {b.pseudoPath(suite)} as it does not match filter"
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
                        wasi_sdk=wasi_sdk,
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
            Hyperfine.run(benchmark_commands, print_stdout=True)


class SubcommandCompareRevs:
    """Implements the 'compare-revs' subcommand.

    For each suite s and each benchmark b in s, benchmarks b executed by first
    wasmtime revision against b executed by second revision.
    """

    @staticmethod
    def addSubparser(subparsers):
        parser = subparsers.add_parser(
            "compare-revs",
            help="""For each individual benchmark, compares runtime when using
            first revision of wasmtime against second one""",
        )
        parser.add_argument(
            "--filter",
            help="Only run benchmarks that match this glob pattern",
            action="append",
        )
        parser.add_argument(
            "--allow-dirty",
            help="Allows the benchfx repo to be dirty when running benchmarks",
            action="store_true",
            default=False,
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

    def prepare_wasmtime(self, repo_path: Path, revision: str, configuration: Config):
        wasmtime_repo = GitRepo(repo_path)
        logMsg(f"wasmtime repo dirty? {wasmtime_repo.isDirty()}")
        wasmtime_repo.checkout(revision)
        wasmtime = Wasmtime(repo_path)
        wasmtime.build(configuration)
        return wasmtime

    def execute(self, cli_args: argparse.Namespace):
        if not cli_args.allow_dirty:
            checkBenchFxRepoClean()

        checkDependenciesPresent(need_second_wasmtime_repo=True)

        (wasi_sdk, mimalloc, interpreter, binaryen) = prepareCommonTools()

        rev1_config = Config.fromCliArgs(cli_args, revision_qualifier="rev1")
        rev2_config = Config.fromCliArgs(cli_args, revision_qualifier="rev2")

        # Wasmtime1 setup
        wasmtime1_repo_path = REPOS_PATH / WASMTIME_REPO1
        wasmtime1 = self.prepare_wasmtime(
            wasmtime1_repo_path, cli_args.revision1, rev1_config
        )

        # Wasmtime2 setup
        wasmtime2_repo_path = REPOS_PATH / WASMTIME_REPO2
        wasmtime2 = self.prepare_wasmtime(
            wasmtime2_repo_path, cli_args.revision2, rev2_config
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
                benchmark_filters = cli_args.filter
                if benchmark_filters and not b.matchesAnyFilter(
                    suite, benchmark_filters
                ):
                    logMsg(
                        f"Skipping benchmark {b.pseudoPath(suite)} as it does not match filter"
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
                    wasi_sdk=wasi_sdk,
                    reference_interpreter=interpreter,
                    binaryen=binaryen,
                    wasmtime=wasmtime1,
                )
                command2 = b.prepare(
                    suite,
                    benchmark_output_dir_rev2,
                    rev1_config,
                    mimalloc=mimalloc,
                    wasi_sdk=wasi_sdk,
                    reference_interpreter=interpreter,
                    binaryen=binaryen,
                    wasmtime=wasmtime2,
                )
                json_path = benchmark_output_dir / "results.json"

                benchmark_pairs.append((b, [command1, command2], json_path))

            if benchmark_pairs:
                suite_files[suite_path] = benchmark_pairs

        # Perform actual benchmarking in each suite:
        for benchmark_pairs in suite_files.values():
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


class SubcommandSetup:
    """Implements the 'setup' subcommand.

    Install dependencies if missing.
    """

    @staticmethod
    def addSubparser(subparsers):
        parser = subparsers.add_parser(
            "setup",
            help="""Sets up the repos for the dependencies used by the harness
            and downloads tools that we don't built from source.

            The command is idempotent; it does nothing for depdencies that are
            already present.
            """,
        )

        parser.add_argument(
            "--wasmtime-create-worktree-from-development-repo",
            help=f"""Instead of cloning wasmtime from github, create a new git
            worktree inside {REPOS_PATH} based off an existing wasmtime
            development repository at path WASMTIME_DEVEL_REPO_PATH""",
            metavar="WASMTIME_DEVEL_REPO_PATH",
        )

    def execute(self, cli_args: argparse.Namespace):
        def ensureWasiSdkPresent():
            if not WasiSdk.isVersionInstalled(
                config.WASI_SDK_VERSION, WASI_SDK_BASE_PATH
            ):
                WasiSdk.download(config.WASI_SDK_VERSION, WASI_SDK_BASE_PATH)

        def checkExistingRepo(repo: str, expected_root_commit) -> bool:
            path = REPOS_PATH / repo
            if path.exists():
                r = GitRepo(path)
                check(
                    r.hasRev(expected_root_commit),
                    f"Error while setting up {repo} repo at {path}: It exists, but does not contain commit {expected_root_commit}, which we expected to find there",
                )
                return True
            else:
                return False

        def init_repo(repo_name, remotes):
            path = REPOS_PATH / repo
            GitRepo.initWithRemotes(path, remotes)

        def makeNewWorkdir(
            repo_description: str,
            new_worktree_repo: str,
            source_devel_repo_path: Path,
            expected_commit: str,
        ):
            new_worktree_path = REPOS_PATH / new_worktree_repo

            check(
                source_devel_repo_path.exists(),
                f"Supposed to create a worktree for {repo_description} development repository at {source_devel_repo_path}, but that path does not exist",
            )
            check(
                not new_worktree_path.exists(),
                f"Supposed to create new git worktree at {new_worktree_path}, but that path already exists",
            )

            devel_repo = GitRepo(source_devel_repo_path)
            check(
                devel_repo.hasRev(expected_commit),
                f"Expected {repo_description} development repo at {source_devel_repo_path} to contain commit {expected_commit}, which it doesn't",
            )

            devel_repo.addWorktree(new_worktree_path)

        ensureWasiSdkPresent()
        repos = [SPEC_REPO, BINARYEN_REPO, MIMALLOC_REPO]
        runCheck(f"mkdir -p '{REPOS_PATH}'")

        for repo in repos:
            expected_root_commit, remotes = config.GITHUB_REPOS[repo]
            if not checkExistingRepo(repo, expected_root_commit):
                init_repo(repo, remotes)

        # We have multiple wasmtime repos
        wasmtime_repos = [WASMTIME_REPO1, WASMTIME_REPO2]
        wasmtime_root_commit, wasmtime_github_remotes = config.GITHUB_REPOS["wasmtime"]

        for repo in wasmtime_repos:
            if checkExistingRepo(repo, wasmtime_root_commit):
                continue
            if cli_args.wasmtime_create_worktree_from_development_repo:
                devel_repo_path = Path(
                    cli_args.wasmtime_create_worktree_from_development_repo
                )
                makeNewWorkdir("wasmtime", repo, devel_repo_path, wasmtime_root_commit)
            else:
                init_repo(repo, wasmtime_github_remotes)


def main():
    parser = argparse.ArgumentParser(prog="bench")

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Can be given twice to enable full debug logging",
    )

    subcommands = {
        "run": SubcommandRun,
        "compare-revs": SubcommandCompareRevs,
        "setup": SubcommandSetup,
    }

    subparsers = parser.add_subparsers(
        title="Available subcommands", dest="command", required=True
    )

    for name, class_ in subcommands.items():
        class_.addSubparser(subparsers)

    cli_args = parser.parse_args()

    global logLevel
    logLevel = cli_args.verbose

    logMsg(f"CLI args object: {cli_args}")

    script_path = Path(__file__)
    check(
        script_path.parent == Path.cwd(),
        "This script should be executed from the root of the benchfx directory",
    )

    Class_ = subcommands[cli_args.command]
    Class_().execute(cli_args)


if __name__ == "__main__":
    try:
        main()
    except HarnessError as e:
        print("Error: " + e.args[0])
        logProcessOutput(traceback.format_exc())
