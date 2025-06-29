from __future__ import annotations

import pickle
import sys
import textwrap
from pathlib import Path

import pytest
from attrs import define

from _pytask.collect_command import _find_common_ancestor_of_all_nodes
from _pytask.collect_command import _print_collected_tasks
from pytask import ExitCode
from pytask import PathNode
from pytask import Task
from pytask import cli
from tests.conftest import enter_directory


def test_collect_task(runner, tmp_path):
    source = """
    from pathlib import Path

    def task_example(path=Path("in.txt"), produces=Path("out.txt")): ...
    """
    tmp_path.joinpath("task_module.py").write_text(textwrap.dedent(source))
    tmp_path.joinpath("in.txt").touch()

    result = runner.invoke(cli, ["collect", tmp_path.as_posix()])

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_module.py>" in captured
    assert "<Function" in captured
    assert "task_example>" in captured

    result = runner.invoke(cli, ["collect", tmp_path.as_posix(), "--nodes"])

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_module.py>" in captured
    assert "<Function" in captured
    assert "task_example>" in captured
    assert "<Dependency" in captured
    assert "in.txt>" in captured
    assert "<Product" in captured
    assert "out.txt>" in captured


def test_collect_task_new_interface(runner, tmp_path):
    source = """
    from pathlib import Path

    def task_example(depends_on=Path("in.txt"), arg=1, produces=Path("out.txt")): ...
    """
    tmp_path.joinpath("task_module.py").write_text(textwrap.dedent(source))
    tmp_path.joinpath("in.txt").touch()

    result = runner.invoke(cli, ["collect", tmp_path.as_posix()])

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_module.py>" in captured
    assert "<Function" in captured
    assert "task_example>" in captured

    result = runner.invoke(cli, ["collect", tmp_path.as_posix(), "--nodes"])

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_module.py>" in captured
    assert "<Function" in captured
    assert "task_example>" in captured
    assert "<Dependency" in captured
    assert "in.txt>" in captured
    assert "<Product" in captured
    assert "out.txt>" in captured
    assert "arg" in captured


def test_collect_task_in_root_dir(runner, tmp_path):
    source = """
    from pathlib import Path

    def task_example(path=Path("in.txt"), produces=Path("out.txt")): ...
    """
    tmp_path.joinpath("task_module.py").write_text(textwrap.dedent(source))
    tmp_path.joinpath("in.txt").touch()

    with enter_directory(tmp_path):
        result = runner.invoke(cli, ["collect"])

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_module.py>" in captured
    assert "<Function" in captured
    assert "task_example>" in captured


def test_collect_parametrized_tasks(runner, tmp_path):
    source = """
    from pytask import task
    from pathlib import Path

    for arg, produces in [(0, "out_0.txt"), (1, "out_1.txt")]:

        @task
        def task_example(depends_on=Path("in.txt"), arg=arg, produces=produces):
            pass
    """
    tmp_path.joinpath("task_module.py").write_text(textwrap.dedent(source))
    tmp_path.joinpath("in.txt").touch()

    result = runner.invoke(cli, ["collect", tmp_path.as_posix()])

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "").replace("\u2502", "")
    assert "<Module" in captured
    assert "task_module.py>" in captured
    assert "<Function" in captured
    assert "[depends_on0-0-out_0.txt]>" in captured
    assert "[depends_on1-1-out_1.txt]>" in captured


def test_collect_task_with_expressions(runner, tmp_path):
    source = """
    from pathlib import Path

    def task_example_1(path=Path("in_1.txt"), produces=Path("out_1.txt")): ...
    def task_example_2(path=Path("in_2.txt"), produces=Path("out_2.txt")): ...
    """
    tmp_path.joinpath("task_module.py").write_text(textwrap.dedent(source))
    tmp_path.joinpath("in_1.txt").touch()
    tmp_path.joinpath("in_2.txt").touch()

    result = runner.invoke(cli, ["collect", tmp_path.as_posix(), "-k", "_1"])

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_module.py>" in captured
    assert "<Function" in captured
    assert "task_example_1>" in captured
    assert "<Function" in captured
    assert "task_example_2>" not in captured

    result = runner.invoke(cli, ["collect", tmp_path.as_posix(), "-k", "_1", "--nodes"])

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_module.py>" in captured
    assert "<Function" in captured
    assert "task_example_1>" in captured
    assert "<Dependency" in captured
    assert "in_1.txt>" in captured
    assert "<Product" in captured
    assert "out_1.txt>" in captured


def test_collect_task_with_marker(runner, tmp_path):
    source = """
    import pytask
    from pathlib import Path

    @pytask.mark.wip
    def task_example_1(path=Path("in_1.txt"), produces=Path("out_1.txt")): ...

    def task_example_2(path=Path("in_2.txt"), produces=Path("out_2.txt")): ...
    """
    tmp_path.joinpath("task_module.py").write_text(textwrap.dedent(source))
    tmp_path.joinpath("in_1.txt").touch()

    config = """
    [tool.pytask.ini_options]
    markers = {'wip' = 'A work-in-progress marker.'}
    """
    tmp_path.joinpath("pyproject.toml").write_text(textwrap.dedent(config))

    result = runner.invoke(cli, ["collect", tmp_path.as_posix(), "-m", "wip"])

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_module.py>" in captured
    assert "<Function" in captured
    assert "task_example_1>" in captured
    assert "<Function" in captured
    assert "task_example_2>" not in captured

    result = runner.invoke(
        cli, ["collect", tmp_path.as_posix(), "-m", "wip", "--nodes"]
    )

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_module.py>" in captured
    assert "<Function" in captured
    assert "task_example_1>" in captured
    assert "<Dependency" in captured
    assert "in_1.txt>" in captured
    assert "<Product" in captured
    assert "out_1.txt>" in captured


def test_collect_task_with_ignore_from_config(runner, tmp_path):
    source = """
    from pathlib import Path

    def task_example_1(path=Path("in_1.txt"), produces=Path("out_1.txt")): ...
    """
    tmp_path.joinpath("task_example_1.py").write_text(textwrap.dedent(source))

    source = """
    def task_example_2(path=Path("in_2.txt"), produces=Path("out_2.txt")): ...
    """
    tmp_path.joinpath("task_example_2.py").write_text(textwrap.dedent(source))
    tmp_path.joinpath("in_1.txt").touch()

    config = """
    [tool.pytask.ini_options]
    ignore = ["task_example_2.py"]
    """
    tmp_path.joinpath("pyproject.toml").write_text(textwrap.dedent(config))

    result = runner.invoke(cli, ["collect", tmp_path.as_posix()])

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_example_1.py>" in captured
    assert "task_example_2.py>" not in captured
    assert "<Function" in captured
    assert "task_example_1>" in captured
    assert "<Function" in captured
    assert "task_example_2>" not in captured

    result = runner.invoke(cli, ["collect", tmp_path.as_posix(), "--nodes"])

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_example_1.py>" in captured
    assert "task_example_2.py>" not in captured
    assert "<Function" in captured
    assert "task_example_1>" in captured
    assert "<Dependency" in captured
    assert "in_1.txt>" in captured
    assert "<Product" in captured
    assert "out_1.txt>" in captured


def test_collect_task_with_ignore_from_cli(runner, tmp_path):
    source = """
    from pathlib import Path

    def task_example_1(path=Path("in_1.txt"), produces=Path("out_1.txt")): ...
    """
    tmp_path.joinpath("task_example_1.py").write_text(textwrap.dedent(source))
    tmp_path.joinpath("in_1.txt").touch()

    source = """
    from pathlib import Path

    def task_example_2(path=Path("in_2.txt"), produces=Path("out_2.txt")): ...
    """
    tmp_path.joinpath("task_example_2.py").write_text(textwrap.dedent(source))

    result = runner.invoke(
        cli, ["collect", tmp_path.as_posix(), "--ignore", "task_example_2.py"]
    )

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_example_1.py>" in captured
    assert "task_example_2.py>" not in captured
    assert "<Function" in captured
    assert "task_example_1>" in captured
    assert "<Function" in captured
    assert "task_example_2>" not in captured

    result = runner.invoke(
        cli,
        ["collect", tmp_path.as_posix(), "--ignore", "task_example_2.py", "--nodes"],
    )

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_example_1.py>" in captured
    assert "task_example_2.py>" not in captured
    assert "<Function" in captured
    assert "task_example_1>" in captured
    assert "<Dependency" in captured
    assert "in_1.txt>" in captured
    assert "<Product" in captured
    assert "out_1.txt>" in captured


@define
class Node:
    path: Path

    def state(self): ...


def function(depends_on, produces): ...


def test_print_collected_tasks_without_nodes(capsys):
    dictionary = {
        Path("task_path.py"): [
            Task(
                base_name="function",
                path=Path("task_path.py"),
                function=function,
                depends_on={0: Node("in.txt")},
                produces={0: Node("out.txt")},
            )
        ]
    }

    _print_collected_tasks(dictionary, False, "file", Path())

    captured = capsys.readouterr().out
    assert "<Module task_path.py>" in captured
    assert "<Function task_path.py::function>" in captured
    assert "<Dependency in.txt>" not in captured
    assert "<Product out.txt>" not in captured


def test_print_collected_tasks_with_nodes(capsys):
    dictionary = {
        Path("task_path.py"): [
            Task(
                base_name="function",
                path=Path("task_path.py"),
                function=function,
                depends_on={"depends_on": PathNode(name="in.txt", path=Path("in.txt"))},
                produces={0: PathNode(name="out.txt", path=Path("out.txt"))},
            )
        ]
    }

    _print_collected_tasks(dictionary, True, "file", Path())

    captured = capsys.readouterr().out

    assert "<Module task_path.py>" in captured
    assert "<Function task_path.py::function>" in captured
    assert "<Dependency in.txt>" in captured
    assert "<Product out.txt>" in captured


@pytest.mark.parametrize(("show_nodes", "expected_add"), [(False, "src"), (True, "..")])
def test_find_common_ancestor_of_all_nodes(show_nodes, expected_add):
    tasks = [
        Task(
            base_name="function",
            path=Path.cwd() / "src" / "task_path.py",
            function=function,
            depends_on={
                "depends_on": PathNode.from_path(Path.cwd() / "src" / "in.txt")
            },
            produces={
                0: PathNode.from_path(
                    Path.cwd().joinpath("..", "bld", "out.txt").resolve()
                )
            },
        )
    ]

    result = _find_common_ancestor_of_all_nodes(tasks, [Path.cwd() / "src"], show_nodes)
    assert result == Path.cwd().joinpath(expected_add).resolve()


def test_task_name_is_shortened(runner, tmp_path):
    tmp_path.joinpath("a", "b").mkdir(parents=True)
    tmp_path.joinpath("a", "b", "task_example.py").write_text("def task_example(): ...")

    result = runner.invoke(cli, ["collect", tmp_path.as_posix()])

    assert result.exit_code == ExitCode.OK
    assert "task_example.py::task_example" in result.output
    assert "a/b/task_example.py::task_example" not in result.output


def test_python_node_is_collected(runner, tmp_path):
    source = """
    from pytask import Product
    from typing import Annotated
    from pathlib import Path

    def task_example(
        dependency: int = 1, path: Annotated[Path, Product] = Path("out.txt")
    ):
        ...
    """
    tmp_path.joinpath("task_module.py").write_text(textwrap.dedent(source))
    result = runner.invoke(cli, ["collect", tmp_path.as_posix(), "--nodes"])

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_module.py>" in captured
    assert "<Function" in captured
    assert "task_example>" in captured
    assert "Dependency" in captured
    assert "Product" in captured


def test_none_is_a_python_node(runner, tmp_path):
    source = """
    from pytask import Product
    from typing import Annotated
    from pathlib import Path

    def task_example(
        dependency = None, path: Annotated[Path, Product] = Path("out.txt")
    ):
        ...
    """
    tmp_path.joinpath("task_module.py").write_text(textwrap.dedent(source))
    result = runner.invoke(cli, ["collect", tmp_path.as_posix(), "--nodes"])

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_module.py>" in captured
    assert "<Function" in captured
    assert "task_example>" in captured
    assert "Dependency" in result.output
    assert "Product" in captured


def test_python_nodes_are_aggregated_into_one(runner, tmp_path):
    source = """
    from pytask import Product
    from typing import Annotated
    from pathlib import Path

    def task_example(
        nested = {"a": (1, 2), 2: {"b": None}},
        path: Annotated[Path, Product] = Path("out.txt")
    ):
        ...
    """
    tmp_path.joinpath("task_module.py").write_text(textwrap.dedent(source))
    result = runner.invoke(cli, ["collect", tmp_path.as_posix(), "--nodes"])

    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_module.py>" in captured
    assert "<Function" in captured
    assert "task_example>" in captured
    assert "Dependency" in result.output
    assert "Product" in captured


def test_node_protocol_for_custom_nodes(runner, tmp_path):
    source = """
    from typing import Annotated
    from pytask import Product
    from attrs import define
    from pathlib import Path

    @define
    class CustomNode:
        name: str
        value: str
        signature: str = "id"

        def state(self):
            return self.value

        def load(self): ...
        def save(self, value): ...

    def task_example(
        data = CustomNode("custom", "text"),
        out: Annotated[Path, Product] = Path("out.txt"),
    ) -> None:
        out.write_text(data)
    """
    tmp_path.joinpath("task_module.py").write_text(textwrap.dedent(source))

    result = runner.invoke(cli, ["collect", "--nodes", tmp_path.as_posix()])
    assert result.exit_code == ExitCode.OK
    assert "<Dependency custom>" in result.output


def test_node_protocol_for_custom_nodes_with_paths(runner, tmp_path):
    source = """
    from typing import Annotated
    from typing import Any
    from pytask import Product
    from pathlib import Path
    from attrs import define
    import pickle

    @define
    class PickleFile:
        name: str
        path: Path
        signature: str = "id"
        attributes: dict[Any, Any] = {}

        def state(self):
            return str(self.path.stat().st_mtime)

        def load(self):
            with self.path.open("rb") as f:
                out = pickle.load(f)
            return out

        def save(self, value):
            with self.path.open("wb") as f:
                pickle.dump(value, f)

    _PATH = Path(__file__).parent.joinpath("in.pkl")

    def task_example(
        data = PickleFile(_PATH.as_posix(), _PATH),
        out: Annotated[Path, Product] = Path("out.txt"),
    ) -> None:
        out.write_text(data)
    """
    tmp_path.joinpath("task_module.py").write_text(textwrap.dedent(source))
    tmp_path.joinpath("in.pkl").write_bytes(pickle.dumps("text"))

    result = runner.invoke(cli, ["collect", "--nodes", tmp_path.as_posix()])
    assert result.exit_code == ExitCode.OK
    assert "in.pkl" in result.output


def test_setting_name_for_python_node_via_annotation(runner, tmp_path):
    source = """
    from pathlib import Path
    from typing import Annotated
    from pytask import Product, PythonNode
    from typing import Any

    def task_example(
        input: Annotated[str, PythonNode(name="node-name", value="text")],
        path: Annotated[Path, Product] = Path("out.txt"),
    ) -> None:
        path.write_text(input)
    """
    tmp_path.joinpath("task_module.py").write_text(textwrap.dedent(source))

    result = runner.invoke(cli, ["collect", "--nodes", tmp_path.as_posix()])
    assert result.exit_code == ExitCode.OK
    assert "Dependency" in result.output


def test_more_nested_pytree_and_python_node_as_return(runner, snapshot_cli, tmp_path):
    source = """
    from pathlib import Path
    from typing import Any
    from typing import Annotated
    from pytask import PythonNode
    from typing import Dict

    nodes = [
        PythonNode(),
        (PythonNode(), PythonNode()),
        PythonNode()
    ]

    def task_example() -> Annotated[Dict[str, str], nodes]:
        return [{"first": "a", "second": "b"}, (1, 2), 1]
    """
    tmp_path.joinpath("task_module.py").write_text(textwrap.dedent(source))
    result = runner.invoke(cli, ["collect", "--nodes", tmp_path.as_posix()])
    assert result.exit_code == ExitCode.OK
    if sys.platform != "win32":
        assert result.output == snapshot_cli()


def test_more_nested_pytree_and_python_node_as_return_with_names(
    runner, snapshot_cli, tmp_path
):
    source = """
    from pathlib import Path
    from typing import Any
    from typing import Annotated
    from pytask import PythonNode
    from typing import Dict

    nodes = [
        PythonNode(name="dict"),
        (PythonNode(name="tuple1"), PythonNode(name="tuple2")),
        PythonNode(name="int")
    ]

    def task_example() -> Annotated[Dict[str, str], nodes]:
        return [{"first": "a", "second": "b"}, (1, 2), 1]
    """
    tmp_path.joinpath("task_module.py").write_text(textwrap.dedent(source))
    result = runner.invoke(cli, ["collect", "--nodes", tmp_path.as_posix()])
    assert result.exit_code == ExitCode.OK
    if sys.platform != "win32":
        assert result.output == snapshot_cli()


@pytest.mark.parametrize(
    "node_def",
    [
        "paths: Annotated[List[Path], DirectoryNode(pattern='*.txt'), Product])",
        "produces=DirectoryNode(pattern='*.txt'))",
        ") -> Annotated[None, DirectoryNode(pattern='*.txt')]",
    ],
)
def test_collect_task_with_provisional_path_node_as_product(runner, tmp_path, node_def):
    source = f"""
    from pytask import DirectoryNode, Product
    from typing import Annotated, List
    from pathlib import Path

    def task_example({node_def}: ...
    """
    tmp_path.joinpath("task_module.py").write_text(textwrap.dedent(source))

    # Without nodes.
    result = runner.invoke(cli, ["collect", tmp_path.as_posix()])
    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_module.py>" in captured
    assert "<Function" in captured
    assert "task_example>" in captured

    # With nodes.
    result = runner.invoke(cli, ["collect", tmp_path.as_posix(), "--nodes"])
    assert result.exit_code == ExitCode.OK
    captured = result.output.replace("\n", "").replace(" ", "")
    assert "<Module" in captured
    assert "task_module.py>" in captured
    assert "<Function" in captured
    assert "task_example>" in captured
    assert "<Product" in captured
    assert "/*.txt>" in captured


def test_collect_task_with_provisional_dependencies(runner, tmp_path):
    source = """
    from typing import Annotated
    from pytask import DirectoryNode
    from pathlib import Path

    def task_example(
        paths = DirectoryNode(pattern="[ab].txt")
    ) -> Annotated[str, Path("merged.txt")]:
        path_dict = {path.stem: path for path in paths}
        return path_dict["a"].read_text() + path_dict["b"].read_text()
    """
    tmp_path.joinpath("task_example.py").write_text(textwrap.dedent(source))

    result = runner.invoke(cli, ["collect", "--nodes", tmp_path.as_posix()])
    assert result.exit_code == ExitCode.OK
    assert "[ab].txt" in result.output


def test_collect_custom_node_receives_default_name(runner, tmp_path):
    source = """
    from typing import Annotated

    class CustomNode:
        name: str = ""

        def state(self): return None
        def signature(self): return "signature"
        def load(self, is_product): ...
        def save(self, value): ...

    def task_example() -> Annotated[None, CustomNode()]: ...
    """
    tmp_path.joinpath("task_example.py").write_text(textwrap.dedent(source))
    result = runner.invoke(cli, ["collect", "--nodes", tmp_path.as_posix()])
    assert result.exit_code == ExitCode.OK
    output = result.output.replace(" ", "").replace("\n", "")
    assert "task_example::return" in output
