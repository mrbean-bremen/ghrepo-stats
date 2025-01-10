# Copyright 2020 mrbean-bremen. See LICENSE file for details.
import argparse
import configparser
import csv
import enum
import json
import math
import os
import sys
from collections import namedtuple
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import matplotlib.pyplot as pyplot
import requests
from bs4 import BeautifulSoup
from github import Github, UnknownObjectException


class UnknownRepository(Exception):
    pass


class StatKind(enum.Enum):
    Issues = 0,
    Stars = 1


def utcnow() -> datetime:
    if sys.version_info < (3, 11):
        return datetime.utcnow()
    else:
        from datetime import UTC
        return datetime.now(UTC)


def write_datetime(obj):
    if isinstance(obj, datetime):
        return {"iso": obj.isoformat()}


def read_datetime(obj):
    iso_format = obj.get('iso')
    if iso_format is not None:
        return datetime.fromisoformat(iso_format)
    return obj


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
        if path.exists():
            return path
        # fall back to home directory
        path = Path.home() / self.ini_file
        if path.exists():
            return path
        raise FileNotFoundError(
            f"Missing initialization file {self.ini_file}, "
            f"cannot authorize to GitHub")

    def parse(self):
        config = configparser.ConfigParser()
        config.read(self.ini_path())
        self._username = config.get("auth", "username")
        self._token = config.get("auth", "token")


class GitHubStats:
    cache_dir = ".ghrepo-stats"

    def __init__(self, repo_name: str, verbose: bool, csv_file: str = "",
                 show_packages: bool = False, min_stars: int = 0):
        self.repo_name: str = repo_name
        self.verbose = verbose
        self.show_packages = show_packages
        self.min_stars = min_stars
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
        start = utcnow()
        stargazers = self.repository().get_stargazers_with_dates().reversed
        cached, since = self.cached_result(StatKind.Stars)
        existing_ids = [e["id"] for e in cached]
        results = []
        cache_is_valid = False
        for stargazer in stargazers:
            if self.verbose:
                print(stargazer.starred_at, stargazer.user.login)
            user_id = stargazer.user.id
            if user_id in existing_ids:
                # we found at least one id that is in the cache
                cache_is_valid = True
                found_all = False
                if len(cached) > stargazers.totalCount - len(results):
                    # at least one star has been removed - we remove the cache
                    # entries backwards until we find the first removed star
                    while cached and len(cached) > stargazers.totalCount - len(results):
                        last_id = existing_ids.pop()
                        cached.pop()
                        if last_id == user_id:
                            break
                        if (len(cached) == stargazers.totalCount - len(results) and
                                existing_ids[-1] == user_id):
                            found_all = True
                            break
                    if found_all:
                        break
                else:
                    break
            results.append({
                "starred_at": stargazer.starred_at,
                "id": stargazer.user.id
            })
        if not cache_is_valid or len(cached) > stargazers.totalCount - len(results):
            cached.clear()
        if results:
            results.sort(key=lambda s: s["starred_at"])
            cached.extend(results)
            self.write_cache(cached, start, StatKind.Stars)

        times = []
        for stargazer in cached:
            times.append(stargazer["starred_at"])
        if self.verbose:
            print(f"Getting stars took {utcnow() - start}")
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
        # count the lifetime weekly
        issues = self.collect_issues_or_prs(show_issues)

        if not issues:
            return self.handle_output([], [], "")

        slots: List[dict] = []
        start_time = issues[0].opened
        now = utcnow()
        slot_time = start_time
        while slot_time < now:
            slots.append({"time": slot_time, "nr": 0, "days": 0})
            slot_time = slot_time + timedelta(days=7)

        slot_len = len(slots)
        for issue in issues:
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
        cached, since = self.cached_result(StatKind.Issues)
        last_number = 0
        kwargs = {"state": "all"}
        if cached:
            kwargs["since"] = since + timedelta(seconds=1)
            last_number = cached[-1]["number"]
        start = utcnow()
        results = self.repository().get_issues(**kwargs)
        new_results = []
        for result in results:
            new_results.append({
                "is_pr": result.pull_request is not None,
                "created_at": result.created_at,
                "closed_at": result.closed_at,
                "number": result.number,
                "state": result.state
            })
            if result.number <= last_number:
                # an existing issues has been closed or reopened -
                # remove it from cache
                for c in cached:
                    if c["number"] == result.number:
                        cached.remove(c)
                        break
        if self.verbose:
            print(f"Getting issues/prs took {utcnow() - start}")
        if new_results:
            cached.extend(new_results)
            cached.sort(key=lambda v: v["number"])
            self.write_cache(cached, start, StatKind.Issues)

        Issue = namedtuple("Issue", ["opened", "closed"])
        issues: List[Issue] = []
        for issue in cached:
            if collect_issues == issue["is_pr"]:
                # ignore PRs or issues
                continue
            if issue["closed_at"] is not None:
                open_time = issue["closed_at"] - issue["created_at"]
                if open_time.days == 0 and open_time.seconds < 60:
                    # ignore immediately closed issues
                    # happens for imported closed issues
                    continue
            if self.verbose:
                print(issue["number"], issue["created_at"], issue["closed_at"])
            issues.append(Issue(opened=issue["created_at"],
                                closed=issue["closed_at"]))
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
        pyplot.style.use("seaborn-v0_8")
        pyplot.plot(issue_times, issue_nrs)
        max_y = max(issue_nrs) + 1
        step = max(1, max_y // 6)
        order = int(math.log10(step))
        tens = 10 ** order
        base = step // tens
        base = 10 * base if base > 7 else 5 if base > 3 else 2 if base > 2 else base
        step = base * tens
        pyplot.yticks(range(0, max_y, step))
        pyplot.title(f"{self.repo_name}: {title}")
        pyplot.show()

    def write_csv(self, numbers, times):
        directory = os.path.dirname(self.csv_file)
        if directory:
            try:
                os.makedirs(directory, exist_ok=True)
            except OSError:
                print(f"Failed to create path {directory} - exiting")
                return False
        try:
            with open(self.csv_file, "w") as csv_file:
                writer = csv.writer(csv_file, lineterminator="\n")
                for t, nr in zip(times, numbers):
                    writer.writerow([t, nr])
        except OSError as ex:
            print(f"Failed to write csv file {self.csv_file}: {ex}")
            return False
        return True

    def cache_path(self, stat_kind):
        org, name = self.repo_name.split("/")
        return (Path.home() / self.cache_dir / org / name /
                (stat_kind.name + ".json"))

    def cached_result(self, stat_kind):
        cache_path = self.cache_path(stat_kind)
        if cache_path.exists():
            with open(cache_path) as f:
                cached = json.load(f, object_hook=read_datetime)
                if cached["data"]:
                    # check if the cache has timezone info, which has been added at some time
                    # in the API result, and ignore the cache if not so it will be recreated
                    first_item = cached["data"][0]
                    created = "created_at" if stat_kind == StatKind.Issues else "starred_at"
                    first_date = first_item[created]
                    if first_date.tzinfo is None:
                        return [], None
                return cached["data"], cached["since"]
        return [], None

    def write_cache(self, result, date, stat_kind):
        cache_path = self.cache_path(stat_kind)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cached = {
            "since": date,
            "data": result
        }
        with open(cache_path, "w") as f:
            json.dump(cached, f, default=write_datetime)

    def dependents(self):
        # partly taken from https://stackoverflow.com/a/58772379/12480730
        subquery = "?dependent_type=PACKAGE" if self.show_packages else ""
        url = f"https://github.com/{self.repo_name}/network/dependents{subquery}"
        repos = []
        while True:
            r = requests.get(url)
            soup = BeautifulSoup(r.content, "html.parser")
            data = [
                ("{}/{}".format(
                    t.find('a',
                           {"data-repository-hovercards-enabled": ""}).text,
                    t.find('a', {"data-hovercard-type": "repository"}).text
                ), int(t.div.span.text.strip().replace(",", "")))
                for t in
                soup.findAll("div", {"data-test-id": "dg-repo-pkg-dependent"})
            ]
            if not data:
                break
            repos.extend([r for r in data if r[1] >= self.min_stars])

            button_anchors = soup.find(
                "div", {"class": "paginate-container"}
            ).find_all("a")
            for anchor in button_anchors:
                if anchor.text == "Next":
                    url = anchor["href"]
                    break
            else:
                break
        # sort descending by number of stargazers
        repos.sort(key=lambda d: d[1], reverse=True)
        if self.csv_file:
            names = [r[0] for r in repos]
            stars = [r[1] for r in repos]
            self.write_csv(stars, names)
        else:
            # if no file was given, just write to stdout
            for name, star in repos:
                print(f"{name}\t{star}")


def main():
    commands = {
        "issues": GitHubStats.issue_stats,
        "prs": GitHubStats.pr_stats,
        "stars": GitHubStats.star_stats,
        "commits": GitHubStats.commit_stats,
        "codesize": GitHubStats.code_size_change,
        "issue-life": GitHubStats.issue_lifetime,
        "pr-life": GitHubStats.pr_lifetime,
        "dependents": GitHubStats.dependents
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
    parser.add_argument("--packages", action="store_true",
                        help="Only for dependents: get dependent packages "
                             "instead of repositories")
    parser.add_argument("--min-stars", type=int, default=0,
                        help="Only for dependents: limits the output to "
                             "dependents with at least the given number of "
                             "stargazers.")
    args = parser.parse_args()
    repo_name = args.repo_name
    sub_command = args.sub_command.lower()

    if sub_command not in commands:
        print(f"Invalid command {sub_command}."
              f"Supported commands: {command_string}")
        return 1
    try:
        stats = GitHubStats(repo_name, args.verbose, args.csv,
                            args.packages, args.min_stars)
        commands[sub_command](stats)
    except Exception as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
