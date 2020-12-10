# Copyright 2020 mrbean-bremen. See LICENSE file for details.
import argparse
import configparser
from pathlib import Path

import matplotlib.pyplot as pyplot
from github import Github, UnknownObjectException


class MissingConfig(Exception):
    pass


class UnknownRepository(Exception):
    pass


class ConfigReader:
    ini_file = "ghrepo-stats.ini"

    def __init__(self):
        self._username: str = ""
        self._token: str = ""

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
            raise MissingConfig(f"Missing entry 'username' in"
                                f" {self.ini_file}, "
                                f"cannot authorize to GitHub")
        self._token = config.get("auth", "token")
        if not self._token:
            raise MissingConfig(f"Missing entry 'token' in {self.ini_file}, "
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

    def repository(self):
        try:
            return self.github.get_repo(self.repo_name)
        except UnknownObjectException:
            raise UnknownRepository(
                f"No repository found with name {self.repo_name}")

    def issue_pr_stats(self, show_issues: bool):
        issues = self.repository().get_issues(state="all")
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
        stargazers = self.repository().get_stargazers_with_dates()
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

    def commit_stats(self):
        commits = self.repository().get_stats_commit_activity()
        times = []
        commit_nrs = []
        for commit_stat in commits:
            if self.verbose:
                print(commit_stat.week, commit_stat.total)
            times.append(commit_stat.week)
            commit_nrs.append(commit_stat.total)

        title = f"Number of commit per week in last year"
        self.show_plot(commit_nrs, times, title)

    def code_size_change(self):
        freq_stats = self.repository().get_stats_code_frequency()
        times = []
        commit_size = []
        code_size = 0
        for freq in freq_stats:
            if self.verbose:
                print(freq.week, freq.additions, freq.deletions)
            times.append(freq.week)
            code_size += freq.additions - freq.deletions
            commit_size.append(code_size)

        title = f"Change of code size over time"
        self.show_plot(commit_size, times, title)

    def show_plot(self, issue_nrs, issue_times, title):
        pyplot.plot(issue_times, issue_nrs)
        max_y = max(issue_nrs) + 1
        step = max(1, max_y // 6)
        pyplot.yticks(range(0, max_y, step))
        pyplot.title(f"{self.repo_name}: {title}")
        pyplot.show()


def main():
    commands = {
        "issues": GitHubStats.issue_stats,
        "prs": GitHubStats.pr_stats,
        "stars": GitHubStats.star_stats,
        "commits": GitHubStats.commit_stats,
        "codesize": GitHubStats.code_size_change,
    }
    command_string = ", ".join([f"'{cmd}'" for cmd in commands])
    parser = argparse.ArgumentParser(
        description="Shows GitHub repo statistics")
    parser.add_argument("sub_command",
                        help="The kind of statistics to show. "
                             f"Possible values: {command_string}.")
    parser.add_argument("repo_name",
                        help="Full repository name in the form "
                             "<repo_owner>/<repo_name>.")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Outputs diagnostic information")
    args = parser.parse_args()
    repo_name = args.repo_name
    sub_command = args.sub_command.lower()

    if sub_command not in commands:
        print(f"Invalid command {sub_command}."
              f"Supported commands: {command_string}")
        return 1
    try:
        stats = GitHubStats(repo_name, args.verbose)
        commands[sub_command](stats)
    except Exception as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
