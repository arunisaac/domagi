To replicate the results in the paper, please follow the instructions below. Guix is required.

# Download data
Download https://s3-us-west-2.amazonaws.com/human-pangenomics/pangenomes/freeze/freeze1/pggb/chroms/chr8.hprc-v1.0-pggb.gfa.gz and gunzip it.
```
wget https://s3-us-west-2.amazonaws.com/human-pangenomics/pangenomes/freeze/freeze1/pggb/chroms/chr8.hprc-v1.0-pggb.gfa.gz
gunzip chr8.hprc-v1.0-pggb.gfa.gz
```

# Install software
Drop into an environment with all the software installed.
```
guix time-machine -C channels.scm -- shell -m manifest.scm
```

# Compile the ccwl workflow
Compile the ccwl workflow into CWL.
```
ccwl compile benchmark.scm -o benchmark.cwl
```

# Run it
Run the CWL workflow using ravanan. If you need to add additional arguments so it runs on your HPC cluster, please do so.
```
ravanan --guix-channels=channels.scm --store=store benchmark.cwl benchmark-inputs.yaml
```
