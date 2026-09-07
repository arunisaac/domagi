[![domagi CI badge](https://ci.systemreboot.net/badge/domagi.svg)](https://ci.systemreboot.net/jobs/domagi) [![domagi website CI badge](https://ci.systemreboot.net/badge/domagi-website.svg)](https://ci.systemreboot.net/jobs/domagi-website)

domagi is a DuckDB-powered clone of [odgi](https://odgi.readthedocs.io), the pangenome manipulation tool.

# Installation
## Using Guix
You can download the latest development version of domagi using Guix. Put the following into a file `channels.scm`.
```scheme
(cons (channel
       (name 'domagi)
       (url "https://git.systemreboot.net/domagi/")
       (branch "main")
       (introduction
        (make-channel-introduction
         "b35f8cf1054912282dfea938c35e1c5949d2cba6"
         (openpgp-fingerprint
          "7F73 0343 F2F0 9F3C 77BF  79D3 2E25 EE8B 6180 2BB3"))))
      %default-channels)
```
Then run
```
guix time-machine -C channels.scm -- shell domagi
```
You will be dropped into a shell with domagi on your `PATH`. From there, you can run any domagi command.

Using this installation method, no persistent installation is left on your machine.

## Using pip
In a new directory, create a python virtual environment and activate it.
```
mkdir domagi
cd domagi
python3 -m venv .venv
source .venv/bin/activate
```
Ensure that your system has [cmake](https://cmake.org/), [DuckDB](https://duckdb.org/) and the [verstable.h](https://github.com/JacksonAllan/Verstable/) header-only library installed. Then, install the development version of domagi using pip.
```
pip install git+https://git.systemreboot.net/domagi/
```
You can now run any domagi command in this virtual environment.

# Documentation

See the [manual of the development version](https://forge.systemreboot.net/domagi/manual/dev/en/).
