#### Change Log:
* [2025.1.23] - Added `bin/archive-subdirectories.py` and scripts section in `setup.py`
* [2025.1.23] - Added `gzip_file` and `archive_subdirectories` functions
* [2024.11.19] - Added `get_executable_in_path` and `add_executables_to_environment` functions

#### Pending:
* `memory_profiler` does not work for `subprocess` shell commands.  Port to `psutils` instead.
* Add support for [Jug](https://jug.readthedocs.io/en/latest/tutorial.html#example) for parallel tasks on different processors