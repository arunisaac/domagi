(list (channel
        (name 'domagi)
        (url "https://git.systemreboot.net/domagi/")
        (branch "main")
        (commit "fd1982b4883e08710de42a972827bab48116b7f9")
        (introduction
         (make-channel-introduction
          "b35f8cf1054912282dfea938c35e1c5949d2cba6"
          (openpgp-fingerprint
           "7F73 0343 F2F0 9F3C 77BF  79D3 2E25 EE8B 6180 2BB3"))))
      (channel
        (inherit %default-guix-channel)
        (commit "eec85c7f76b4b85da9fe9e7d1778d063620d4801")))
