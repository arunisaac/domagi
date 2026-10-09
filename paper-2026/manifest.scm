(use-modules ((gnu packages bioinformatics) #:select (ccwl))
             ((gnu packages bioinformatics) #:select (ravanan) #:prefix guix:)
	     ((gnu packages guile-xyz) #:select (guile-filesystem))
             (guix git-download)
             (guix packages))

(define ravanan
  (let ((commit "1f5000ad6ff98278bf638ff0176ddfd5bf8933cf"))
    (package
      (inherit guix:ravanan)
      (name "ravanan")
      (version "0.2.0")
      (source (origin
                (method git-fetch)
                (uri (git-reference
                       (url "https://git.systemreboot.net/ravanan")
                       (commit commit)))
                (file-name (git-file-name name version))
                (sha256
                 (base32
                  "1dq3jn8z78x287krfvi6hbj066pmz8mk2qamjfsind0bxxjk3qzd")))))))

(packages->manifest
 (list ccwl ravanan))
