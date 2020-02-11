# Change log

## [0.2.7]

- Bugfix: Accept filenames with whitespace(s) as arguments

## [0.2.6]

- Bugfix: Piping input for tools should be working now
- Added: Support for interactive tools, enabled with  `--interactive` (or `-i`)
- Changed: Must explicitly enable container TTY with `--tty` (or `-t`)
- Changed: For docker compatibility dropped the shorthand versions of `--in` and `--out` (`-i` and `-o`).
- Added: Point out if cannot use docker

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
