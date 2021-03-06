# ghrepo-stats [![PyPI version](https://badge.fury.io/py/ghrepo-stats.svg)](https://badge.fury.io/py/ghrepo-stats)

Have you ever wondered how the number of stargazers or the number of open
issues has changed over time for your (or any) GitHub repository? I did, so I 
wrote this small command line tool to do this.

*ghrepo-stats* uses [pygithub](https://github.com/PyGithub/PyGithub) to 
collect some statistics from a specific repository using a command line tool
and show it using [matplotlib](https://github.com/matplotlib/matplotlib) or
write it to a csv file. 

Features
--------
The following sub-commands are supported:
- stars: shows the number of stargazers over time (caveat: stargazers that
  have removed their star are not shown, as the info is not available)
- issues: shows the number of currently open issues over time
- prs: shows the number of currently open pull requests over time
- commits: shows the number of commits over the last year
- codesize: shows the change of the code size over time measured by the 
  number of added and deleted lines
- issue-life: shows the average life time in days of issues over time
  (sampled once a week) 
- pr-life: shows the average life time in days of issues over time 
  (sampled once a week) 

_Caution:_
Using sub-commands related to issues and PRs on repositories with many
(open or close) issues  will take a lot of time due to API access
limitations.  

Installation
------------
If you want to try it, you can install it from PyPi:
```
pip install ghrepo-stats
```
Or you can install the current master from GitHub:
```
pip install git+https://github.com/mrbean-bremen/ghrepo-stats
```

Usage
-----
To use this, you need a 
[personal access token](https://docs.github.com/en/free-pro-team@latest/github/authenticating-to-github/creating-a-personal-access-token)
able to read public repositories for your GitHub account. The user name and
token is expected to be found in the file `ghrepo-stats.ini`, either in the
repository root, or in your home path.

The contents should be in the form:
```
[auth]
username = my-github-username
token = 123456789abcdef0123456789abcdef012345678
```

To get usage information you can now type:
```
$ show-ghstats -h
usage: show-ghstats [-h] [--verbose] [--csv CSV] sub_command repo_name

Shows GitHub repo statistics

positional arguments:
  sub_command    The kind of statistics to show. Possible values: 'issues',
                 'prs', 'stars', 'commits', 'codesize', 'issue-life', 'pr-
                 life'.
  repo_name      Full repository name in the form <repo_owner>/<repo_name>.

optional arguments:
  -h, --help     show this help message and exit
  --verbose, -v  Outputs diagnostic information
  --csv CSV      Write the output into a csv file with the given file path
```

So, for example, to get a star plot of a specific repository, you can write:
```
$ show-ghstats stars "my-github-username/my-repo"
```
If you want to have the numbers saved in a csv file instead to play around with
the numbers you can write: 
```
$ show-ghstats stars "my-github-username/my-repo" --csv=my_repo-issues
```
This will write a file `my_repo-issues.csv` with the numbers (date+time /
number of issues) in the current path.

Examples
--------
Get some measure of popularity change by showing the number of stargazers over
time (note: stars that have been retracted are not counted):
```
$ show-ghstats stars "jmcgeheeiv/pyfakefs"
```
![stars](https://github.com/mrbean-bremen/ghrepo-stats/raw/master/doc/images/stars.jpg)

Check how fast issues are handled over time. An increasing curve means ever 
more unresolved issues (also depends on the policies of the specific
project - some projects leave issues open indefinitely, while others close 
outdated issues):
```
$ show-ghstats issue-life "jmcgeheeiv/pyfakefs"
```
![issue-lifetime](https://github.com/mrbean-bremen/ghrepo-stats/raw/master/doc/images/issuelife.jpg)

Check how fast issues are handled by showing how many issues have been open
over time:
```
$ show-ghstats issues "vvvv/svg"
```
![issues](https://github.com/mrbean-bremen/ghrepo-stats/raw/master/doc/images/issues.jpg)

See how the code size changed over time measured in code additions/deletions:
```
$ show-ghstats codesize "pytest-dev/pytest"
```
![codesize](https://github.com/mrbean-bremen/ghrepo-stats/raw/master/doc/images/codesize.jpg)

