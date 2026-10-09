;;; domagi --- DuckDB-powered pangenome Swiss Army knife
;;; Copyright © 2026 Arun Isaac <arunisaac@systemreboot.net>
;;;
;;; This file is part of domagi.
;;;
;;; domagi is free software: you can redistribute it and/or modify it under the
;;; terms of the GNU General Public License as published by the Free Software
;;; Foundation, either version 3 of the License, or (at your option) any later
;;; version.
;;;
;;; domagi is distributed in the hope that it will be useful, but WITHOUT ANY
;;; WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
;;; FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
;;; details.
;;;
;;; You should have received a copy of the GNU General Public License along with
;;; domagi. If not, see <https://www.gnu.org/licenses/>.

(define-module (domagi-package)
  #:use-module ((gnu packages check) #:select (python-pytest))
  #:use-module ((gnu packages cmake) #:select (cmake))
  #:use-module ((gnu packages datastructures) #:select (verstable))
  #:use-module ((gnu packages duckdb) #:select (duckdb python-duckdb))
  #:use-module ((gnu packages pkg-config) #:select (pkg-config))
  #:use-module ((gnu packages python-xyz) #:select (python-click python-meson))
  #:use-module (guix build-system pyproject)
  #:use-module (guix gexp)
  #:use-module (guix git-download)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (guix packages)
  #:use-module (guix utils))

(define-public domagi
  (package
    (name "domagi")
    (version "0.1.0")
    (source (local-file ".."
                        "domagi-checkout"
                        #:recursive? #t
                        #:select? (or (git-predicate (dirname (current-source-directory)))
                                      (const #t))))
    (build-system pyproject-build-system)
    (inputs
     (list duckdb
           python-click
           python-duckdb))
    (native-inputs
     (list cmake
           python-meson
           pkg-config
           python-pytest
           verstable))
    (home-page "https://github.com/arunisaac/domagi")
    (synopsis "DuckDB-powered pangenome Swiss Army knife")
    (description "domagi is a DuckDB-powered clone of odgi, the pangenome
manipulation tool.")
    (license license:gpl3+)))

domagi
