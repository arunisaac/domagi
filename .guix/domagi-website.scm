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
  #:use-module ((gnu packages diagram) #:select (pikchr))
  #:use-module ((gnu packages docbook) #:select (docbook-xsltng))
  #:use-module ((gnu packages fonts) #:select (font-charter font-fira-code))
  #:use-module ((gnu packages haskell-xyz) #:select (pandoc))
  #:use-module ((gnu packages python) #:select (python))
  #:use-module ((gnu packages xml) #:select (python-lxml))
  #:use-module (guix gexp)
  #:use-module (guix packages)
  #:use-module (guix profiles)
  #:use-module (guix utils)
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

(define domagi-web-manual-en-gexp
  (with-imported-modules '((guix build utils))
    #~(begin
        (use-modules (guix build utils)
                     (ice-9 popen)
                     (srfi srfi-26)
                     (rnrs io ports))

        (define (call-with-input-pipe command proc)
          (let ((port #f))
            (dynamic-wind
              (lambda ()
                (set! port (apply open-pipe* OPEN_READ command)))
              (cut proc port)
              (lambda ()
                (unless (zero? (close-pipe port))
                  (error "Command invocation failed" command))))))

        (define (pikchr source svg)
          (mkdir-p (dirname svg))
          (call-with-output-file svg
            (cut display
                 (call-with-input-pipe (list #$(file-append pikchr "/bin/pikchr")
                                             "--svg-only"
                                             source)
                   get-string-all)
                 <>)))

        (setenv "HOME" "/tmp")
        (set-path-environment-variable
         "GUIX_PYTHONPATH"
         (list (string-append "lib/python"
                              #$(version-major+minor (package-version python))
                              "/site-packages"))
         (list #$(profile
                   (content (concatenate-manifests
                             (list (packages->manifest (list python-lxml))
                                   (package->development-manifest domagi)))))))
        (copy-recursively #$(file-append (package-source domagi)
                                         "/doc")
                          (string-append (getcwd) "/doc"))
        (invoke #$(file-append python "/bin/python3")
                (string-append #$(package-source domagi) "/extractdoc.py"))
        (chdir "doc")
        (pikchr "er.pic"
                (string-append #$output "/media/er.svg"))
        (pikchr "schema.pic"
                (string-append #$output "/media/schema.svg"))
        (invoke #$(file-append docbook-xsltng "/bin/docbook")
                (string-append "--resources:" #$output)
                "-xi:on"
                "resource-base-uri=/domagi/manual/"
                "mediaobject-output-base-uri=/domagi/manual/media/"
                "-s:domagi.dbk"
                (string-append "-o:" #$output "/dev/en/index.html")))))

(define-public domagi-website
  (file-union "domagi-website"
              `(("index.html"
                 ,(computed-file "domagi-website-home-page.html"
                                 domagi-website-home-page-gexp))
                ("style.css" ,(local-file "../website/style.css"))
                ("manual"
                 ,(computed-file "domagi-web-manual-en"
                                 domagi-web-manual-en-gexp))
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
