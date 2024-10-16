# PyExeggutor
`pyexeggutor` is a simple wrapper for the subprocess module to run shell commands in Python.

![](images/exeggutor.png)

## Installation:
```
pip install pyexeggutor
```
## Usage:

### Hello World
```python
import pyexeggutor as exe

cmd = exe.RunShellCommand(["time echo 'Hello World'"], name="hello_world")
cmd.run()
# ====================================
# RunShellCommand(name:hello_world)
# ====================================
# (/bin/bash)$ time echo 'Hello World'
# ____________________________________
# Properties:
#     - stdout: 53.00 B
#     - stderr: 83.00 B
#     - returncode: 0
#     - peak memory: 33.59 B
#     - duration: 00:00:00

print(cmd.stdout_)
# Hello World

print(cmd.stderr_)
# real	0m0.000s
# user	0m0.000s
# sys	0m0.000s

print(cmd.returncode_)
# 0
```

### Hello Salmon
```python
# Set up command
from pyexeggutor import (
    RunShellCommand,
    build_logger,
    format_bytes,
)

# Set up logger (optional)
pipeline_name = "Hello Salmon"

logger = build_logger(pipeline_name)

cmd = RunShellCommand(
    command=[
        salmon_executable,
        "index",
        "--keepDuplicates",
        "--threads",
        n_jobs,
        "--transcripts",
        fasta,
        "--index",
        os.path.join(index_directory, "salmon_index"),
        index_options,   
        ], 
    name="salmon_indexer",
)

# Run
logger.info(f"[{cmd.name}] running command: {cmd.command}")
cmd.run()
logger.info(f"[{cmd.name}] duration: {cmd.duration_}")
logger.info(f"[{cmd.name}] peak memory: {format_bytes(cmd.peak_memory_)}")

# Dump
logger.info(f"[{cmd.name}] dumping stdout, stderr, and return code: {log_directory}")
cmd.dump(log_directory)

# Validate
logger.info(f"[{cmd.name}] checking return code status: {cmd.returncode_}")
cmd.check_status()
```
### Miscellaenous
#### Genomics

```python
import pyfastx # Not a dependency
from pyexeggutor import (
    open_file_writer,
    fasta_writer, 
)

wrap = 1000 # Max 1000 characters per line, use 0 for no wrap
with open_file_writer("output.fasta.gz") as f:
    for id, seq in pyfastx.Fasta("path/to/input.fasta.gz", build_index=False):
        fasta_writer(header=id, seq=seq, file=f, wrap=wrap)
```
## Development Stage:
* `beta`
