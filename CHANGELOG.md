#### Change Log:
* [2025.12.5] - Added `parse_attribute_from_gff`
* [2025.12.1] - Added `fastq_writer`
* [2025.11.7] - Added `indent=4` to `write_json`
* [2025.9.29] - Added `ftp-downloader.py`
* [2025.2.19] - Added `pv` wrapper for `tqdm`
* [2025.2.6] - Added `read_list` function
* [2025.2.6] - Added automatic overwrite for logs with same name via `logger` and set default level to `logging.INFO`
* [2025.1.23] - Added `bin/archive-subdirectories.py` and scripts section in `setup.py`
* [2025.1.23] - Added `gzip_file` and `archive_subdirectories` functions
* [2024.11.19] - Added `get_executable_in_path` and `add_executables_to_environment` functions

#### Pending:
* `memory_profiler` does not work for `subprocess` shell commands.  Port to `psutils` instead.
* Add support for [Jug](https://jug.readthedocs.io/en/latest/tutorial.html#example) for parallel tasks on different processors or wrapper around `concurrent`
* Replace `build_logger` with `loguru`
