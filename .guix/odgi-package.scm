;; This odgi package definition is from https://git.genenetwork.org/guix-bioinformatics/tree/gn/packages/pangenome.scm?id=e586976ac493d2f7480784f098d58c9fed065b02#n524

(define-module (odgi-package)
  #:use-module ((gnu packages datastructures)
                #:select (libdivsufsort sdsl-lite))
  #:use-module ((gnu packages jemalloc) #:select (jemalloc))
  #:use-module ((gnu packages mpi) #:select (openmpi))
  #:use-module ((gnu packages pkg-config) #:select (pkg-config))
  #:use-module ((gnu packages python) #:select (python))
  #:use-module ((gnu packages python-xyz) #:select (pybind11))
  #:use-module (guix build-system cmake)
  #:use-module (guix download)
  #:use-module (guix gexp)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (guix packages))

(define-public odgi
  (package
    (name "odgi")
    (version "0.9.4")
    (source (origin
              (method url-fetch)
              (uri (string-append "https://github.com/pangenome/odgi/releases"
                                  "/download/v" version
                                  "/odgi-v" version ".tar.gz"))
              (sha256
               (base32
                "10f25fqm1snxr0lw659scns5r4a52lg8131rg50jkwikv1nxw3g5"))
              (snippet
               #~(begin
                   (use-modules (guix build utils))
                   (substitute* "CMakeLists.txt"
                     (("-march=native") "")
                     (("-msse4\\.2") ""))))))
    (build-system cmake-build-system)
    (arguments
     (list
      #:tests? #f
      #:parallel-build? #f  ; parallel build uses too much memory
      #:phases
      #~(modify-phases %standard-phases
          (add-after 'unpack 'use-gnuinstalldirs-macros
            (lambda _
              (substitute* "CMakeLists.txt"
                (("project\\(odgi\\)" all)
                 (string-append all "\ninclude(GNUInstallDirs)"))
                (("LIBRARY DESTINATION lib")
                 "LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}")
                (("ARCHIVE DESTINATION lib")
                 "ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}"))))
          (add-after 'unpack 'link-to-libodgi
            (lambda _
              (substitute* "CMakeLists.txt"
                (("^  \\$<TARGET_OBJECTS:odgi_objs>.*") "")
                (("target_link_libraries\\(odgi " all)
                 (string-append all "libodgi_shared "))))))))
    (native-inputs (list pkg-config))
    (inputs
     (list jemalloc
           libdivsufsort
           openmpi
           pybind11
           python
           sdsl-lite))
    (properties '((tunable? . #t)))
    (home-page "https://github.com/vgteam/odgi")
    (synopsis "Optimized Dynamic Genome/Graph Implementation")
    (description "odgi provides an efficient and succinct dynamic DNA
sequence graph model, as well as algorithms for pangenome analysis.")
    (license license:expat)))

odgi
