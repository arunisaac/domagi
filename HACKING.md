# Drop into a development environment

The easiest way to get all the dependencies and development tools is to use `guix shell`.
```
guix shell -L .guix -m manifest.scm
```

# Build the C source code

Initialize the meson build directory.
```
meson setup builddir
```
Compile the C source code. Repeat this command everytime you modify the C code.
```
meson compile -C builddir
```

# Run domagi

Run domagi like so:
```
./pre-inst-env python3 -m domagi.domagi <subcommand> ...
```

# Run tests

Run tests.
```
./pre-inst-env python3 -m pytest
```
