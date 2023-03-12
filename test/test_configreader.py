import configparser
from pathlib import Path

import pytest

import ghrepo_stats
from ghrepo_stats.show_gh_stats import ConfigReader


@pytest.fixture
def config_reader():
    yield ConfigReader()


def test_missing_configfile(fs, config_reader):
    with pytest.raises(FileNotFoundError, match="Missing initialization file*"):
        config_reader.parse()


def test_missing_section(fs, config_reader):
    fs.create_file(Path.home() / "ghrepo-stats.ini", contents="")
    with pytest.raises(configparser.NoSectionError, match="No section: 'auth'"):
        config_reader.parse()


def test_missing_username(fs, config_reader):
    fs.create_file(Path.home() / "ghrepo-stats.ini", contents="[auth]")
    with pytest.raises(configparser.NoOptionError, match="No option 'username'*"):
        config_reader.parse()


def test_missing_token(fs, config_reader):
    fs.create_file(Path.home() / "ghrepo-stats.ini",
                   contents="[auth]\nusername=user_name")
    with pytest.raises(configparser.NoOptionError, match="No option 'token'*"):
        config_reader.parse()


def test_valid_inifile_in_home(fs, config_reader, ini_content):
    fs.create_file(Path.home() / "ghrepo-stats.ini", contents=ini_content)
    config_reader.parse()
    assert config_reader.username == "ghrepo-user"
    assert config_reader.token == "ghp_qwertyuiop12asdfghjkl34zxcvbnm"


def test_valid_inifile_in_repo(fs, config_reader, ini_content):
    fs.create_file(Path(ghrepo_stats.__file__).parent.parent /
                   "ghrepo-stats.ini", contents=ini_content)
    config_reader.parse()
    assert config_reader.username == "ghrepo-user"
    assert config_reader.token == "ghp_qwertyuiop12asdfghjkl34zxcvbnm"
