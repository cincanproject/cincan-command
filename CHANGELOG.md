# Change log

## [0.2.6]

- Bugfix: Piping input for tools should be working now.
- Feature: Added support for interactive tools. Docker run switches `--interactive` (or `-i`)and `--tty` (or `-t`) must be explicitly defined for this to work. This feature also changed the arguments of `--in` and `--out`: shortened `-i` and `-o` removed.

## [0.2.5]

Changed
- Bugfix: Give uploaded input files world-writeable permissions (777).
  Otherwise containers with non-root users work only when host uid and container uid match.

## [0.2.4]

Changed
- Bugfix: Do not load **all** versions of an image, use the 'default' tag if none given

## [0.2.3]

Changed
- Bugfix: Colons ':' in output files made output download to fail

## [0.2.2]

Added:
- Say something about supported platforms

Changed
- Bugfix: Sometimes '/' in command line was stripped away
- Bugfix: Output files prefixes to other output files not downloaded from container

## [0.2.1] 

Changed
- Bugfix: Tool output mixed stdout and stderr together
- Bugfix: Documentation flaws

## [0.2.0]

Added
- Initial beta version
