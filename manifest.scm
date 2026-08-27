(use-modules ((gnu packages docbook) #:select (docbook-xml docbook-xsltng))
             ((gnu packages task-management) #:select (git-bug))
             ((gnu packages xml) #:select (python-lxml))
             ((domagi-package) #:select (domagi))
             ((odgi-package) #:select (odgi))
             (srfi srfi-1))

(define (manifest-cons* . args)
  "ARGS is of the form (PACKAGES ... ONTO-MANIFEST). Return a manifest
with PACKAGES and all packages in ONTO-MANIFEST."
  (let ((packages (drop-right args 1))
        (onto-manifest (last args)))
    (manifest (append (map package->manifest-entry packages)
                      (manifest-entries onto-manifest)))))

(manifest-cons* docbook-xml
                docbook-xsltng
                git-bug
                odgi
                python-lxml
                (package->development-manifest domagi))
