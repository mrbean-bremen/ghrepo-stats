import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from ghrepo_stats.show_gh_stats import GitHubStats
from test.utils import User, PaginatedList


@pytest.fixture
def stargazers(github):
    yield github.return_value.get_repo.return_value.get_stargazers_with_dates


@pytest.fixture
def stargazer_list():
    yield PaginatedList([
        Stargazer(datetime(2000, 1, 1, tzinfo=tzinfo()),
                  User("user1", 24)),
        Stargazer(datetime(2000, 1, 2, tzinfo=tzinfo()),
                  User("user2", 12)),
        Stargazer(datetime(2000, 1, 3, tzinfo=tzinfo()),
                  User("user3", 42))
    ])


def tzinfo():
    return timezone(timedelta(0))


class Stargazer:
    """Mimics github.Stargazer."""
    def __init__(self, starred_at, user):
        self.starred_at = starred_at
        self.user = user


def test_no_stars(ini_file, stargazers, capsys):
    stargazers.return_value = PaginatedList()
    GitHubStats("owner/repo", False, "test.csv").star_stats()
    assert not Path("test.csv").exists()
    assert "No data points available" in capsys.readouterr().out


def test_one_star(ini_file, stargazers):
    stargazers.return_value = PaginatedList([
        Stargazer(datetime(2000, 1, 1, tzinfo=tzinfo()), User("user", 24))
    ])
    GitHubStats("owner/repo", False, "test.csv").star_stats()
    csv = Path("test.csv")
    assert csv.exists()
    assert csv.read_text() == "2000-01-01 00:00:00+00:00,1\n"
    cache_path = Path.home() / ".ghrepo-stats" / "owner" / "repo" / "Stars.json"
    assert cache_path.exists()
    cached = json.loads(cache_path.read_text())
    assert len(cached["data"]) == 1
    assert cached["data"][0]["starred_at"]["iso"] == "2000-01-01T00:00:00+00:00"
    assert cached["data"][0]["id"] == 24


def test_several_stars(ini_file, stargazers, stargazer_list):
    stargazers.return_value = stargazer_list
    GitHubStats("owner/repo", False, "test.csv").star_stats()
    csv = Path("test.csv")
    assert csv.exists()
    contents = csv.read_text().strip().split("\n")
    assert len(contents) == 3
    assert contents[0] == "2000-01-01 00:00:00+00:00,1"
    assert contents[2] == "2000-01-03 00:00:00+00:00,3"
    cache_path = Path.home() / ".ghrepo-stats" / "owner" / "repo" / "Stars.json"
    assert cache_path.exists()
    cached = json.loads(cache_path.read_text())
    assert len(cached["data"]) == 3
    assert cached["data"][0]["starred_at"]["iso"] == "2000-01-01T00:00:00+00:00"
    assert cached["data"][0]["id"] == 24
    assert cached["data"][2]["starred_at"]["iso"] == "2000-01-03T00:00:00+00:00"
    assert cached["data"][2]["id"] == 42


def test_caching(ini_file, stargazers, stargazer_list, capsys):
    stargazers.return_value = stargazer_list
    GitHubStats("owner/repo", True, "test.csv").star_stats()
    out = capsys.readouterr()
    assert "user1" in out.out
    assert "user2" in out.out
    assert "user3" in out.out

    stargazers.return_value.append(Stargazer(
        datetime(2000, 1, 4, tzinfo=tzinfo()), User("user4", 21)))
    GitHubStats("owner/repo", True, "test.csv").star_stats()
    out = capsys.readouterr()
    # make sure the cached values (except the last one) have not been accessed again
    assert "user1" not in out.out
    assert "user2" not in out.out
    assert "user4" in out.out

    csv = Path("test.csv")
    contents = csv.read_text().strip().split("\n")
    assert len(contents) == 4
    assert contents[2] == "2000-01-03 00:00:00+00:00,3"
    assert contents[3] == "2000-01-04 00:00:00+00:00,4"


def test_caching_after_removed_last(ini_file, stargazers, stargazer_list, capsys):
    stargazers.return_value = stargazer_list
    GitHubStats("owner/repo", False, "test.csv").star_stats()

    del stargazer_list[2]

    GitHubStats("owner/repo", True, "test.csv").star_stats()
    out = capsys.readouterr()
    assert "user1" not in out.out

    csv = Path("test.csv")
    contents = csv.read_text().strip().split("\n")
    assert len(contents) == 2
    assert contents[0] == "2000-01-01 00:00:00+00:00,1"
    assert contents[1] == "2000-01-02 00:00:00+00:00,2"


def test_after_removing_all(ini_file, stargazers, stargazer_list, capsys):
    stargazers.return_value = stargazer_list
    GitHubStats("owner/repo", False, "test.csv").star_stats()
    stargazers.return_value = PaginatedList()

    GitHubStats("owner/repo", True, "test1.csv").star_stats()
    assert not Path("test1.csv").exists()
    assert "No data points available" in capsys.readouterr().out


def test_caching_after_removed_first(ini_file, stargazers, stargazer_list):
    stargazers.return_value = stargazer_list
    GitHubStats("owner/repo", False, "test.csv").star_stats()

    del stargazer_list[0]
    GitHubStats("owner/repo", False, "test.csv").star_stats()

    csv = Path("test.csv")
    contents = csv.read_text().strip().split("\n")
    assert len(contents) == 2
    assert contents[0] == "2000-01-02 00:00:00+00:00,1"
    assert contents[1] == "2000-01-03 00:00:00+00:00,2"


def test_caching_after_removing_first_and_adding(ini_file, stargazers, stargazer_list):
    stargazers.return_value = stargazer_list
    GitHubStats("owner/repo", True, "test.csv").star_stats()

    del stargazer_list[0]
    stargazers.return_value.append(Stargazer(
        datetime(2000, 1, 4, tzinfo=timezone(timedelta(0))), User("user4", 21)))
    GitHubStats("owner/repo", False, "test.csv").star_stats()

    csv = Path("test.csv")
    contents = csv.read_text().strip().split("\n")
    assert len(contents) == 3
    assert contents[0] == "2000-01-02 00:00:00+00:00,1"
    assert contents[1] == "2000-01-03 00:00:00+00:00,2"
    assert contents[2] == "2000-01-04 00:00:00+00:00,3"


def test_caching_after_removing_and_adding_one(ini_file, stargazers, stargazer_list):
    stargazers.return_value = stargazer_list
    GitHubStats("owner/repo", True, "test.csv").star_stats()

    del stargazer_list[1]
    stargazers.return_value.append(
        Stargazer(datetime(2000, 1, 4, tzinfo=tzinfo()), User("user4", 21)))
    GitHubStats("owner/repo", False, "test.csv").star_stats()

    csv = Path("test.csv")
    contents = csv.read_text().strip().split("\n")
    assert len(contents) == 3
    assert contents[0] == "2000-01-01 00:00:00+00:00,1"
    assert contents[1] == "2000-01-03 00:00:00+00:00,2"
    assert contents[2] == "2000-01-04 00:00:00+00:00,3"


def test_caching_after_removing_last_and_adding(ini_file, stargazers, stargazer_list):
    stargazers.return_value = stargazer_list
    GitHubStats("owner/repo", True, "test.csv").star_stats()

    del stargazer_list[2]
    stargazers.return_value.append(Stargazer(
        datetime(2000, 1, 4, tzinfo=tzinfo()), User("user4", 21)))
    GitHubStats("owner/repo", False, "test.csv").star_stats()

    csv = Path("test.csv")
    contents = csv.read_text().strip().split("\n")
    assert len(contents) == 3
    assert contents[0] == "2000-01-01 00:00:00+00:00,1"
    assert contents[1] == "2000-01-02 00:00:00+00:00,2"
    assert contents[2] == "2000-01-04 00:00:00+00:00,3"


def test_caching_after_removing_all_and_adding(ini_file, stargazers, stargazer_list):
    stargazers.return_value = stargazer_list
    GitHubStats("owner/repo", True, "test.csv").star_stats()

    stargazers.return_value = PaginatedList([
        Stargazer(datetime(2000, 1, 4, tzinfo=tzinfo()), User("user4", 21))
    ])
    GitHubStats("owner/repo", True, "test.csv").star_stats()

    csv = Path("test.csv")
    contents = csv.read_text().strip().split("\n")
    assert len(contents) == 1
    assert contents[0] == "2000-01-04 00:00:00+00:00,1"
