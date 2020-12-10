# ghrepo-stats

Have you ever wondered how the number of stargazers or the number of open
issues has changed over time for your (or any) GitHub repository? I did, so I 
wrote this small command line tool to do this (and to play around with the
GitHub API).

*ghrepo-stats* uses [pygithub](https://github.com/PyGithub/PyGithub) to 
collect some statistics from a specific repository using a command line tool
and show it using [matplotlib](https://github.com/matplotlib/matplotlib). 
This is mostly a playground to try out the GitHub API.

Features
--------
Currently, the following sub-commands are supported:
- stars: shows the number of stargazers over time (caveat: stargazers that
  have removed their star are not shown, as the info is not available)
- issues: shows the number of open issues over time
- prs: shows the number of open pull requests over time

_Caution:_
Don't try this with repositories with many (open or close) issues - this will
take a lot of time and load on the GitHub API. 

Installation
------------
If you want to try it, you can install it from GitHub:
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
usage: show-ghstats [-h] [--verbose] sub_command repo_name

Shows GitHub repo statistics

positional arguments:
  sub_command    The kind of statistics to show. Possible values: 'issues',
                 'prs', 'stars', 'commits'.
  repo_name      Full repository name in the form <repo_owner>/<repo_name>.

optional arguments:
  -h, --help     show this help message and exit
  --verbose, -v  Outputs diagnostic information
```

So, for example, to get a star plot of a specific repository, you can write:
```
$ show-ghstats stars "my-github-username/my-repo"
```

Example
-------
Show the number of stargazers over time:
```
$ show-ghstats stars "jmcgeheeiv/pyfakefs"
```
![stars](https://github.com/mrbean-bremen/ghrepo-stats/blob/master/doc/images/stars.jpg)

Check how many issues have been open over time:
```
$ show-ghstats issues "vvvv/svg"
```
![issues](https://github.com/mrbean-bremen/ghrepo-stats/blob/master/doc/images/issues.jpg)

See how the code size changed over time measured in additions/deletions:
```
$ show-ghstats codesize "pytest-dev/pytest"
```
![issues](https://github.com/mrbean-bremen/ghrepo-stats/blob/master/doc/images/codesize.jpg)

To do
-----
A list of things I may add at some time:
- add tests
- output results to csv
- add from/to dates
- add more statistics
- cache/reuse read statistics
