project('domagi', 'c')

cc = meson.get_compiler('c')

duckdb = dependency('DuckDB', required: false)
# If pkg-config and cmake dependency discovery failed, fall back to
# looking for the library manually.
if not duckdb.found()
  duckdb = cc.find_library('duckdb')
endif

omp = dependency('openmp')
if cc.has_header('verstable.h')
  verstable = declare_dependency()
else
  verstable = dependency('verstable')
endif

py = import('python').find_installation()
py.install_sources('domagi/domagi.py',
                   subdir: 'domagi')

install_data('domagi/matrix.sql',
             'domagi/schema.sql',
             'domagi/chop-1.sql',
             'domagi/chop-2.sql',
             'domagi/extract-node-traversal.sql',
             'domagi/extract-path-range.sql',
             'domagi/bed-depth.sql',
             'domagi/overlap.sql',
             'domagi/path-depth.sql',
             'domagi/pre-import.sql',
	     'domagi/post-import.sql',
             install_dir: py.get_install_dir() / 'domagi')

executable('domagi_importgfa',
           'c/importgfa.c',
           dependencies: [duckdb, omp, verstable],
           install: true)
