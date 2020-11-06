# Changelog

Changelog - based on [keepachangelog](https://keepachangelog.com) - format.


## [0.2.11]

2020-11-06

### Added

 - CI tests Python versions 3.6, 3.7, 3.8 and 3.9 separately
 - New run option `--batch` to remove functionality meant for tty devices.

### Changed

 - Less information printed about version checks
 - Uses quay.io as default registry e.g. cincan/ilspy converted to quay.io/cincan/ilspy namespace. Remove old cache from path ~/.cincan/ !

### Fixed

 - Avoid excessive memory use with large input files
 - Speedier download with argument `--mkdir` and with containers with non-root working directory
 - Version tests to be compatible with supported Python versions

## [0.2.10]

2020-08-21

### Added

 - Integration tests for basic functionality
 - CI can make new release automatically based on tag commit

### Removed

 - Experiemental commands 'fanin' and 'fanout'
 - Code for fixing bug in Docker Python library - this was fixed in the upstream. Docker library >= 4.3.0  recommended to use.

## [0.2.9]

2020-07-11

### Added

  - Visual progress bar when downloading image from Docker registry
  - With change of registry module, list subcommand has many new features, such as listing image sizes, versions and more
  - With change of registry module, feature for tool version check on runtime enabled

### Changed

  - Default runtime tag is now 'latest', secondary tag 'dev' for cincan tools, error check improved with image usage
  - registry reworked - lives in separate module cincan-registry

### Deprecated

  - Default tag 'latest-stable' on listing will be changed to 'latest'

## [0.2.8] 

2020-03-20

### Added

  - Feature for filtering downloadable files from container, based on '.cincanignore' file which is stored inside container.
  - Ability to filter `cincan list` by Docker image tag names
  - Version number information from CLI

### Changed

  - Sub command 'list' now fetches data in parallel for speed

### Fixed

  - Files are now downloaded properly in MacOS
  - Slow download speed of 'get_archive' method fixed locally. Bug in upstream.

## [0.2.7] 

2020-02-13

### Added

 - Experimental logging now documented to an extend

### Fixed

  - Accept filenames with whitespace(s) as arguments

## [0.2.6] 

2020-01-24

### Added
  - Support for interactive tools, enabled with  `--interactive` (or `-i`)
  - Point out if cannot use docker

### Changed

  - Must explicitly enable container TTY with `--tty` (or `-t`)
  - For docker compatibility dropped the shorthand versions of `--in` and `--out` (`-i` and `-o`).

### Fixed

- Bugfix: Piping input for tools should be working now

## [0.2.5] 

2019-12-20

### Fixed
  - Give uploaded input files world-writeable permissions (777). Otherwise containers with non-root users work only when host uid and container uid match.

## [0.2.4] 

2019-12-16

### Fixed
  - Do not load **all** versions of an image, use the 'default' tag if none given

## [0.2.3] 

2019-12-11

### Fixed
 - Colons ':' in output files made output download to fail

## [0.2.2] 

2019-12-5

### Added:
  - Say something about supported platforms

### Fixed
  -  Sometimes '/' in command line was stripped away
  - Output files prefixes to other output files not downloaded from container

## [0.2.1] 

2019-11-30

### Fixed

  - Tool output mixed stdout and stderr together
  - Documentation flaws

## [0.2.0] 

2019-11-27

### Added
  - Initial beta version
