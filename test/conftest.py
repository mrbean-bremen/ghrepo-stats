from pathlib import Path
from unittest import mock

import pytest


@pytest.fixture
def ini_content():
    yield """
[auth]
username = ghrepo-user
token = ghp_qwertyuiop12asdfghjkl34zxcvbnm
"""


@pytest.fixture
def ini_file(fs, ini_content):
    fs.create_file(Path.home() / "ghrepo-stats.ini", contents=ini_content)


@pytest.fixture
def github():
    with mock.patch("ghrepo_stats.show_gh_stats.Github") as patched:
        yield patched
