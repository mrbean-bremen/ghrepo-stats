# Release Notes

## Unreleased

### Infrastructure
* remove tests for older Python versions, add Python 3.12 and 3.13 to CI
* add dependabot config for action updates

## [Version 0.5.4](https://pypi.org/project/ghrepo-stats/0.5.4/) (2023-03-13)

### Fixes
* fixed a few edge cases in stargazer caching
* fixed a problem in issue/pr stat that could skip some entries 

### Infrastructure
* added tests for `ConfigReader`, `star_stats` and `issue_pr_stats`
* added GitHub action workflows for tests and release

## [Version 0.5.3](https://pypi.org/project/ghrepo-stats/0.5.3/) (2023-03-11)

### Fixes
* fixed handling of removed stargazers that have been cached 

## [Version 0.5.2](https://pypi.org/project/ghrepo-stats/0.5.2/) (2023-02-02)

### Fixes
* fixed `--csv` option: it only worked for a file name without a directory 

## [Version 0.5.1](https://pypi.org/project/ghrepo-stats/0.5.1/) (2023-01-30)

### Fixes
* added missing default value for `min-stars` option for dependents (caused crash if 
  not set)

## [Version 0.5.0](https://pypi.org/project/ghrepo-stats/0.5.0/) (2022-12-28)

### New features
* added output of dependent repositories and packages

### Fixes
* fixed a regression for showing issue life-times - the feature had been broken 
  with the recent changes

## [Version 0.4.0](https://pypi.org/project/ghrepo-stats/0.4.0/) (2022-12-26)

### Changes
* statistics for issues, PRs and stars are now cached in the filesystem and will be 
  used on subsequent calls

## [Version 0.3.1](https://pypi.org/project/ghrepo-stats/0.3.1/) (2021-12-17)

### Fixes
* reading ini file from home directory did not work

## [Version 0.3.0](https://pypi.org/project/ghrepo-stats/0.3.0/) (2021-01-13)

### New features
* added statistics for issue and PR life time change

### Fixes
* correctly handle case with no data points

## [Version 0.2.1](https://pypi.org/project/ghrepo-stats/0.2.1/) (2020-12-29)

### Fixes
* fixed regression that caused the default version not to work

## [Version 0.2.0](https://pypi.org/project/ghrepo-stats/0.2.0/) (2020-12-18)

### New Features
* added CSV output option

## [Version 0.1.0](https://pypi.org/project/ghrepo-stats/0.1.0/) (2020-12-12)
Initial release.