# Copyright 2020 mrbean-bremen. See LICENSE file for details.
import argparse
import configparser
import csv
import os
from collections import namedtuple
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

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
    def __init__(self, repo_name: str, verbose: bool, csv_file: str = ""):
        self.repo_name: str = repo_name
        self.verbose = verbose
        self.config = ConfigReader()
        self.github = Github(self.config.username, self.config.token)
        if csv_file:
            extension = os.path.splitext(csv_file)[1]
            if not extension:
                csv_file = csv_file + ".csv"
        self.csv_file = csv_file

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
        issues = self.collect_issues_or_prs(show_issues)
        times = []
        for issue in issues:
            times.append((issue.opened, 1))
            if issue.closed is not None:
                times.append((issue.closed, -1))

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
        return self.handle_output(issue_nrs, issue_times, title)

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
        return self.handle_output(star_nrs, star_times, title)

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
        return self.handle_output(commit_nrs, times, title)

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
        return self.handle_output(commit_size, times, title)

    def issue_pr_lifetime(self, show_issues: bool):
        # count the life time weekly
        issues = self.collect_issues_or_prs(show_issues)

        if not issues:
            return self.handle_output([], [], "")

        slots: List[dict] = []
        start_time = issues[-1].opened
        now = datetime.now()
        slot_time = start_time
        while slot_time < now:
            slots.append({"time": slot_time, "nr": 0, "days": 0})
            slot_time = slot_time + timedelta(days=7)

        slot_len = len(slots)
        for issue in reversed(issues):
            days_from_start = (issue.opened - start_time).days
            index = days_from_start // 7
            days = 7 - days_from_start % 7
            end_time = issue.closed or now
            # add increasing issue length at issue lifetime
            while index < slot_len and slots[index]["time"] < end_time:
                slots[index]["days"] += days
                slots[index]["nr"] += 1
                days += 7
                index += 1
            days = (end_time - issue.opened).days
            # add issue duration to slots after it is closed
            while index < slot_len:
                slots[index]["days"] += days
                slots[index]["nr"] += 1
                index += 1

        issue_nrs = []
        issue_times = []
        for slot in slots:
            issue_nrs.append(slot["days"] // slot["nr"])
            issue_times.append(slot["time"])

        issue_type = "issues" if show_issues else "pull requests"
        title = f"Lifetime of {issue_type} over time"
        return self.handle_output(issue_nrs, issue_times, title)

    def collect_issues_or_prs(self, collect_issues):
        results = self.repository().get_issues(state="all")
        Issue = namedtuple("Issue", ["opened", "closed"])
        issues: List[Issue] = []
        for issue in results:
            if collect_issues != (issue.pull_request is None):
                # ignore PRs or issues
                continue
            if (issue.closed_at is not None and
                    (issue.closed_at - issue.created_at).seconds < 60):
                # ignore immediately closed issues
                # happens for imported closed issues
                continue
            if self.verbose:
                print(issue.number, issue.created_at, issue.closed_at)
            issues.append(Issue(opened=issue.created_at,
                                closed=issue.closed_at))
        return issues

    def issue_lifetime(self):
        return self.issue_pr_lifetime(show_issues=True)

    def pr_lifetime(self):
        return self.issue_pr_lifetime(show_issues=False)

    def handle_output(self, numbers, times, title):
        if not numbers:
            print("No data points available - nothing to do.")
            return False
        if self.csv_file:
            return self.write_csv(numbers, times)
        self.show_plot(numbers, times, title)
        return True

    def show_plot(self, issue_nrs, issue_times, title):
        pyplot.plot(issue_times, issue_nrs)
        max_y = max(issue_nrs) + 1
        step = max(1, max_y // 6)
        pyplot.yticks(range(0, max_y, step))
        pyplot.title(f"{self.repo_name}: {title}")
        pyplot.show()

    def write_csv(self, numbers, times):
        directory = os.path.dirname(self.csv_file)
        if directory:
            try:
                os.makedirs(self.csv_file, exist_ok=True)
            except OSError:
                print(f"Failed to create path {directory} - exiting")
            return False
        try:
            with open(self.csv_file, "w") as csv_file:
                writer = csv.writer(csv_file, lineterminator="\n")
                for t, nr in zip(times, numbers):
                    writer.writerow([t, nr])
        except OSError:
            print(f"Failed to write csv file {self.csv_file} - exiting")
            return False
        return True


def main():
    commands = {
        "issues": GitHubStats.issue_stats,
        "prs": GitHubStats.pr_stats,
        "stars": GitHubStats.star_stats,
        "commits": GitHubStats.commit_stats,
        "codesize": GitHubStats.code_size_change,
        "issue-life": GitHubStats.issue_lifetime,
        "pr-life": GitHubStats.pr_lifetime
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
    parser.add_argument("--csv", help="Write the output into a csv file "
                                      "with the given file path")
    args = parser.parse_args()
    repo_name = args.repo_name
    sub_command = args.sub_command.lower()

    if sub_command not in commands:
        print(f"Invalid command {sub_command}."
              f"Supported commands: {command_string}")
        return 1
    try:
        stats = GitHubStats(repo_name, args.verbose, args.csv)
        commands[sub_command](stats)
    except Exception as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
