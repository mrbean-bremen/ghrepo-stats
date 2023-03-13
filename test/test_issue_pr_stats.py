import json
from datetime import datetime
from pathlib import Path

import pytest

from ghrepo_stats.show_gh_stats import GitHubStats
from test.utils import PaginatedList


class Issue:
    def __init__(self, number, created_at, closed_at, is_pr, state):
        self.number = number
        self.created_at = created_at
        self.closed_at = closed_at
        self.pull_request = 1 if is_pr else None
        self.state = state


@pytest.fixture
def issues(github):
    yield github.return_value.get_repo.return_value.get_issues


@pytest.fixture
def issue_list():
    yield PaginatedList([
        Issue(1, datetime(2000, 1, 1), None, False, "open"),
        Issue(2, datetime(2000, 1, 2), datetime(2000, 1, 4), True, "closed"),
        Issue(3, datetime(2000, 1, 3), None, True, "open"),
        Issue(4, datetime(2000, 1, 4), None, False, "open"),
        Issue(5, datetime(2000, 1, 5), datetime(2000, 1, 7), False, "closed"),
        Issue(6, datetime(2000, 1, 6), None, True, "open"),
    ])


def test_no_issues_or_prs(ini_file, issues, capsys):
    issues.return_value = PaginatedList()
    GitHubStats("owner/repo", False, "test.csv").issue_pr_stats(show_issues=True)
    assert not Path("test.csv").exists()
    assert "No data points available" in capsys.readouterr().out

    GitHubStats("owner/repo", False, "test.csv").issue_pr_stats(show_issues=False)
    assert not Path("test.csv").exists()
    assert "No data points available" in capsys.readouterr().out


def test_one_open_issue(ini_file, issues):
    issues.return_value = PaginatedList([
        Issue(1, datetime(2000, 1, 1), None, False, "open")
    ])
    GitHubStats("owner/repo", False, "test.csv").issue_pr_stats(show_issues=True)
    csv = Path("test.csv")
    assert csv.exists()
    assert csv.read_text() == "2000-01-01 00:00:00,1\n"
    cache_path = Path.home() / ".ghrepo-stats" / "owner" / "repo" / "Issues.json"
    assert cache_path.exists()
    cached = json.loads(cache_path.read_text())
    assert len(cached["data"]) == 1
    assert cached["data"][0]["created_at"]["iso"] == "2000-01-01T00:00:00"
    assert cached["data"][0]["closed_at"] is None
    assert cached["data"][0]["number"] == 1
    assert cached["data"][0]["state"] == "open"
    assert not cached["data"][0]["is_pr"]


def test_one_closed_issue(ini_file, issues):
    issues.return_value = PaginatedList([
        Issue(1, datetime(2000, 1, 1, 1, 1, 0),
              datetime(2000, 1, 1, 1, 2, 0), False, "closed")
    ])
    GitHubStats("owner/repo", False, "test.csv").issue_pr_stats(show_issues=True)
    csv = Path("test.csv")
    assert csv.exists()
    contents = csv.read_text().strip().split("\n")
    assert len(contents) == 2
    assert contents[0] == "2000-01-01 01:01:00,1"
    assert contents[1] == "2000-01-01 01:02:00,0"

    cache_path = Path.home() / ".ghrepo-stats" / "owner" / "repo" / "Issues.json"
    assert cache_path.exists()
    cached = json.loads(cache_path.read_text())
    assert len(cached["data"]) == 1


def test_immediately_closed_issue_is_ignored(ini_file, issues):
    issues.return_value = PaginatedList([
        Issue(1, datetime(2000, 1, 1, 1, 1, 0),
              datetime(2000, 1, 1, 1, 1, 59), False, "closed")
    ])
    GitHubStats("owner/repo", False, "test.csv").issue_pr_stats(show_issues=True)
    csv = Path("test.csv")
    assert not csv.exists()


def test_query_pr_with_one_issue(ini_file, issues):
    issues.return_value = PaginatedList([
        Issue(1, datetime(2000, 1, 1), None, False, "open")
    ])
    GitHubStats("owner/repo", False, "test.csv").issue_pr_stats(show_issues=False)
    csv = Path("test.csv")
    assert not csv.exists()

    cache_path = Path.home() / ".ghrepo-stats" / "owner" / "repo" / "Issues.json"
    assert cache_path.exists()
    cached = json.loads(cache_path.read_text())
    assert len(cached["data"]) == 1
    assert cached["data"][0]["created_at"]["iso"] == "2000-01-01T00:00:00"
    assert cached["data"][0]["closed_at"] is None
    assert cached["data"][0]["number"] == 1
    assert cached["data"][0]["state"] == "open"
    assert not cached["data"][0]["is_pr"]


def test_one_pr_with_issue_present(ini_file, issues):
    issues.return_value = PaginatedList([
        Issue(1, datetime(2000, 1, 1), None, False, "open"),
        Issue(2, datetime(2000, 1, 2), None, True, "open")
    ])
    GitHubStats("owner/repo", False, "test.csv").issue_pr_stats(show_issues=False)
    csv = Path("test.csv")
    assert csv.exists()
    assert csv.read_text() == "2000-01-02 00:00:00,1\n"

    cache_path = Path.home() / ".ghrepo-stats" / "owner" / "repo" / "Issues.json"
    assert cache_path.exists()
    cached = json.loads(cache_path.read_text())
    assert len(cached["data"]) == 2


def test_several_issues(ini_file, issues, issue_list):
    issues.return_value = issue_list
    GitHubStats("owner/repo", False, "test.csv").issue_pr_stats(show_issues=True)
    csv = Path("test.csv")
    assert csv.exists()
    contents = csv.read_text().strip().split("\n")
    assert len(contents) == 4
    assert contents[0] == "2000-01-01 00:00:00,1"
    assert contents[1] == "2000-01-04 00:00:00,2"
    assert contents[2] == "2000-01-05 00:00:00,3"
    assert contents[3] == "2000-01-07 00:00:00,2"


def test_several_prs(ini_file, issues, issue_list):
    issues.return_value = issue_list
    GitHubStats("owner/repo", False, "test.csv").issue_pr_stats(show_issues=False)
    csv = Path("test.csv")
    assert csv.exists()
    contents = csv.read_text().strip().split("\n")
    assert len(contents) == 4
    assert contents[0] == "2000-01-02 00:00:00,1"
    assert contents[1] == "2000-01-03 00:00:00,2"
    assert contents[2] == "2000-01-04 00:00:00,1"
    assert contents[3] == "2000-01-06 00:00:00,2"


def test_cache(ini_file, issues, issue_list):
    issues.return_value = issue_list
    GitHubStats("owner/repo", False, "test.csv").issue_pr_stats(show_issues=True)

    issue_list.extend([
        Issue(7, datetime(2000, 1, 8), None, False, "open"),
        Issue(1, datetime(2000, 1, 1), datetime(2000, 1, 9), False, "closed"),
        Issue(9, datetime(2000, 1, 10), None, True, "open"),
        Issue(3, datetime(2000, 1, 3), datetime(2000, 1, 12), True, "closed"),
        Issue(10, datetime(2000, 1, 11), datetime(2000, 1, 12), False, "closed"),
        Issue(8, datetime(2000, 1, 9), datetime(2000, 1, 13), True, "closed"),
    ])
    del issue_list[2]
    del issue_list[0]

    GitHubStats("owner/repo", False, "test.csv").issue_pr_stats(show_issues=True)
    csv = Path("test.csv")
    assert csv.exists()
    contents = csv.read_text().strip().split("\n")
    assert len(contents) == 8
    assert contents[0] == "2000-01-01 00:00:00,1"
    assert contents[1] == "2000-01-04 00:00:00,2"
    assert contents[2] == "2000-01-05 00:00:00,3"
    assert contents[3] == "2000-01-07 00:00:00,2"
    assert contents[4] == "2000-01-08 00:00:00,3"
    assert contents[5] == "2000-01-09 00:00:00,2"
    assert contents[6] == "2000-01-11 00:00:00,3"
    assert contents[7] == "2000-01-12 00:00:00,2"

    GitHubStats("owner/repo", False, "test.csv").issue_pr_stats(show_issues=False)
    csv = Path("test.csv")
    assert csv.exists()
    contents = csv.read_text().strip().split("\n")
    assert len(contents) == 8
    assert contents[0] == "2000-01-02 00:00:00,1"
    assert contents[1] == "2000-01-03 00:00:00,2"
    assert contents[2] == "2000-01-04 00:00:00,1"
    assert contents[3] == "2000-01-06 00:00:00,2"
    assert contents[4] == "2000-01-09 00:00:00,3"
    assert contents[5] == "2000-01-10 00:00:00,4"
    assert contents[6] == "2000-01-12 00:00:00,3"
    assert contents[7] == "2000-01-13 00:00:00,2"
