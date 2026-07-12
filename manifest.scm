(use-modules ((gnu packages task-management) #:select (git-bug))
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

(manifest-cons* git-bug
                odgi
                (package->development-manifest domagi))
