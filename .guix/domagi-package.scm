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
  #:use-module ((gnu packages duckdb) #:select (duckdb python-duckdb))
  #:use-module ((gnu packages pkg-config) #:select (pkg-config))
  #:use-module ((gnu packages python-xyz) #:select (python-click python-meson))
  #:use-module (guix build-system copy)
  #:use-module (guix build-system pyproject)
  #:use-module (guix gexp)
  #:use-module (guix git-download)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (guix packages)
  #:use-module (guix utils))

(define-public verstable
  (package
    (name "verstable")
    (version "2.2.1")
    (source (origin
              (method git-fetch)
              (uri (git-reference
                     (url "https://github.com/JacksonAllan/Verstable")
                     (commit (string-append "v" version))))
              (file-name (git-file-name name version))
              (sha256
               (base32
                "0lwh9kh0jl2vxcijd8606h5xvsjxxa051qaqlx82cl36nh0hkkxp"))))
    (build-system copy-build-system)
    (arguments
     (list #:install-plan
           #~'(("verstable.h" "include/verstable.h"))))
    (home-page "https://github.com/JacksonAllan/Verstable")
    (synopsis "Generic C hash table library")
    (description "Verstable is a versatile generic hash table intended
to bring the speed and memory efficiency of state-of-the-art C++ hash
tables such as Abseil/Swiss, Boost, and Bytell to C.

Its features include:
@begin itemize
@item Type safety
@item Customizable hash, comparison, and destructor functions
@item Single header
@item C99 compatibility
@item Generic API in C11 and later
@item High speed mostly impervious to load factor
@item Only two bytes of overhead per bucket
@item Tombstone-free deletion
@end itemize")
    (license license:expat)))

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
