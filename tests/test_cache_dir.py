"""Tests for the ``cache_dir`` configuration of the fork."""

from __future__ import annotations

import textwrap

import pytest

from _pytask.config_utils import normalize_cache_dir
from pytask import DataCatalog
from pytask import ExitCode
from pytask import build
from pytask import cli

_TASK_MODULE = """
def task_example():
    return None
"""

_CACHE_FILES = ("file_hashes.json", "pytask.sqlite3", "runtimes.json")


@pytest.mark.parametrize(
    ("cache_dir", "expected"),
    # An empty value falls back to the default of the command-line option.
    [(None, ".pytask"), ("", ".pytask"), ("cache", "cache")],
)
def test_normalize_cache_dir_resolves_relative_paths(tmp_path, cache_dir, expected):
    assert normalize_cache_dir(cache_dir, tmp_path) == tmp_path.joinpath(expected)


def test_normalize_cache_dir_keeps_absolute_paths(tmp_path):
    cache_dir = tmp_path.joinpath("elsewhere")

    assert normalize_cache_dir(cache_dir, tmp_path.joinpath("project")) == cache_dir
    assert normalize_cache_dir(cache_dir.as_posix(), tmp_path) == cache_dir


def test_cache_dir_option_moves_the_cache(tmp_path, runner):
    tmp_path.joinpath("task_example.py").write_text(textwrap.dedent(_TASK_MODULE))

    result = runner.invoke(cli, ["build", tmp_path.as_posix(), "--cache-dir", "cache"])

    assert result.exit_code == ExitCode.OK
    cache = tmp_path.joinpath("cache")
    for name in _CACHE_FILES:
        assert cache.joinpath(name).exists()
    assert not tmp_path.joinpath(".pytask").exists()
    # The lockfile is state, not cache, and always stays in the project root.
    assert tmp_path.joinpath("pytask.lock").exists()


def test_cache_dir_option_accepts_an_absolute_path(tmp_path):
    project = tmp_path.joinpath("project")
    project.mkdir()
    project.joinpath("task_example.py").write_text(textwrap.dedent(_TASK_MODULE))
    cache = tmp_path.joinpath("elsewhere")

    session = build(paths=project, cache_dir=cache)

    assert session.exit_code == ExitCode.OK
    assert session.config["cache_dir"] == cache
    assert cache.joinpath("pytask.sqlite3").exists()
    assert not project.joinpath(".pytask").exists()


def test_cache_dir_from_config_file(tmp_path):
    tmp_path.joinpath("task_example.py").write_text(textwrap.dedent(_TASK_MODULE))
    tmp_path.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            """
            [tool.pytask.ini_options]
            cache_dir = "cache"
            """
        )
    )

    session = build(paths=tmp_path)

    assert session.exit_code == ExitCode.OK
    assert session.config["cache_dir"] == tmp_path.joinpath("cache")
    for name in _CACHE_FILES:
        assert tmp_path.joinpath("cache", name).exists()


def test_data_catalog_uses_the_configured_cache_dir(tmp_path):
    """A data catalog created outside a session must not ignore ``cache_dir``."""
    tmp_path.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            """
            [tool.pytask.ini_options]
            cache_dir = "cache"
            """
        )
    )

    data_catalog = DataCatalog(name="cat", _instance_path=tmp_path)

    assert data_catalog.path == tmp_path.joinpath("cache", "data_catalogs", "cat")


def test_clean_keeps_the_cache_dir(tmp_path, runner):
    tmp_path.joinpath("task_example.py").write_text(textwrap.dedent(_TASK_MODULE))
    build(paths=tmp_path, cache_dir=tmp_path.joinpath("cache"))

    result = runner.invoke(
        cli,
        ["clean", tmp_path.as_posix(), "--cache-dir", "cache", "--mode", "force"],
    )

    assert result.exit_code == ExitCode.OK
    assert tmp_path.joinpath("cache", "pytask.sqlite3").exists()
