# Copyright 2020 mrbean-bremen. See LICENSE file for details.
import argparse
import configparser
from pathlib import Path

import matplotlib.pyplot as pyplot
from github import Github


class MissingConfig(Exception):
    pass


class ConfigReader:
    ini_file = "ghrepo-stats.ini"

    def __init__(self):
        self._username: str = ''
        self._token: str = ''

    @property
    def username(self) -> str:
        if not self._username:
            self.parse()
        return self._username

    @property
    def token(self) -> str:
        if not self._token:
            self.parse()
        return self._token

    def ini_path(self):
        # first check in the repository root path
        current_path = Path(__file__).parent.parent
        path = current_path / self.ini_file
        if path.exists:
            return path
        # fall back to home directory
        path = Path.home() / self.ini_file
        if path.exists:
            return path
        raise FileNotFoundError(
            f"Missing initialization file {self.ini_file}, "
            f"cannot authorize to GitHub")

    def parse(self):
        config = configparser.ConfigParser()
        config.read(self.ini_path())
        if not config.has_section("auth"):
            raise MissingConfig(f"Section 'auth' missing in {self.ini_file}, "
                                f"cannot authorize to GitHub")
        self._username = config.get("auth", "username")
        if not self._username:
            raise MissingConfig(f"Missing entry 'username'in {self.ini_file}, "
                                f"cannot authorize to GitHub")
        self._token = config.get("auth", "token")
        if not self._token:
            raise MissingConfig(f"Missing entry 'token'in {self.ini_file}, "
                                f"cannot authorize to GitHub")


class GitHubStats:
    def __init__(self, repo_name: str, verbose: bool):
        self.repo_name: str = repo_name
        self.verbose = verbose
        self.config = ConfigReader()
        self.github = Github(self.config.username, self.config.token)

    def issue_stats(self):
        return self.issue_pr_stats(show_issues=True)

    def pr_stats(self):
        return self.issue_pr_stats(show_issues=False)

    def issue_pr_stats(self, show_issues: bool):
        repo = self.github.get_repo(self.repo_name)
        issues = repo.get_issues(state="all")
        times = []
        for issue in issues:
            if show_issues != (issue.pull_request is None):
                # ignore PRs or issues
                continue
            if (issue.closed_at is not None and
                    (issue.closed_at - issue.created_at).seconds < 60):
                # ignore immediately closed issues
                # happens for imported closed issues
                continue
            if self.verbose:
                print(issue.number, issue.created_at, issue.closed_at)
            times.append((issue.created_at, 1))
            if issue.closed_at is not None:
                times.append((issue.closed_at, -1))

        times = sorted(times)
        issue_nrs = []
        issue_times = []
        nr = 0
        for t, diff in times:
            nr += diff
            issue_nrs.append(nr)
            issue_times.append(t)

        issue_type = "issues" if show_issues else "pull requests"
        title = f"Number of open {issue_type} over time"
        self.show_plot(issue_nrs, issue_times, title)

    def star_stats(self):
        repo = self.github.get_repo(self.repo_name)
        stargazers = repo.get_stargazers_with_dates()
        times = []
        for stargazer in stargazers:
            if self.verbose:
                print(stargazer.starred_at, stargazer.user.login)
            times.append(stargazer.starred_at)

        times = sorted(times)
        star_nrs = []
        star_times = []
        nr = 0
        for t in times:
            nr += 1
            star_nrs.append(nr)
            star_times.append(t)

        title = f"Number of stargazers over time"
        self.show_plot(star_nrs, star_times, title)

    def show_plot(self, issue_nrs, issue_times, title):
        pyplot.plot(issue_times, issue_nrs)
        max_y = max(issue_nrs) + 1
        step = max(1, max_y // 6)
        pyplot.yticks(range(0, max_y, step))
        pyplot.title(f'{self.repo_name}: {title}')
        pyplot.show()


def main():
    parser = argparse.ArgumentParser(
        description='Shows GitHub repo statistics')
    parser.add_argument('sub_command',
                        help='The kind of statistics to show. '
                             'Possible values: issues, prs, stars.')
    parser.add_argument('repo_name',
                        help='Full repository name in the form '
                             '<repo_owner>/<repo_name>.')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Outputs diagnostic information')
    args = parser.parse_args()
    repo_name = args.repo_name
    sub_command = args.sub_command.lower()

    commands = {
        "issues": GitHubStats.issue_stats,
        "prs": GitHubStats.pr_stats,
        "stars": GitHubStats.star_stats
    }
    if sub_command not in commands:
        print(f"Invalid command {sub_command}."
              f"Supported commands: 'stars', 'issues', 'prs'")
        return 1
    try:
        stats = GitHubStats(repo_name, args.verbose)
        commands[sub_command](stats)
    except Exception:
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
