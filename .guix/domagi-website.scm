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

(define-module (domagi-website)
  #:use-module ((gnu packages fonts) #:select (font-charter font-fira-code))
  #:use-module ((gnu packages haskell-xyz) #:select (pandoc))
  #:use-module (guix gexp)
  #:use-module (guix packages)
  #:use-module ((domagi-package) #:select (domagi)))

(define domagi-website-home-page-gexp
  (with-imported-modules '((guix build utils))
    #~(begin
        (use-modules (guix build utils))

        (copy-file #$(file-append (package-source domagi)
                                  "/README.md")
                   "README.md")
        (invoke #$(file-append pandoc "/bin/pandoc")
                "--standalone"
                "--metadata" "title=domagi"
                "--metadata" "document-css=false"
                "--css=style.css"
                "--from=gfm"
                (string-append "--output=" #$output)
                "README.md"))))

(define-public domagi-website
  (file-union "domagi-website"
              `(("index.html"
                 ,(computed-file "domagi-website-home-page.html"
                                 domagi-website-home-page-gexp))
                ("style.css" ,(local-file "../website/style.css"))
                ("fonts/charter_regular.woff2"
                 ,(file-append font-charter
                               "/share/fonts/web/charter_regular.woff2"))
                ("fonts/FiraCode-Regular.woff2"
                 ,(file-append font-fira-code
                               "/share/fonts/web/FiraCode-Regular.woff2"))
                ("fonts/FiraCode-SemiBold.woff2"
                 ,(file-append font-fira-code
                               "/share/fonts/web/FiraCode-SemiBold.woff2")))))

;; A quick wrapper to emulate how guix-forge serves the domagi website under a
;; /domagi prefix
(file-union "domagi-website"
            `(("domagi" ,domagi-website)))
