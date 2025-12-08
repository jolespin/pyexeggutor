#!/usr/bin/env python
import sys
import os
import time
import gzip
import bz2
import subprocess
import pickle
import json
import logging
import functools
import hashlib
import shutil
import tarfile
from datetime import datetime
from typing import Union, Set, TextIO
import pathlib
from tqdm import tqdm, tqdm_notebook, tqdm_gui
from memory_profiler import memory_usage

__version__ = "2025.12.5"


# Read/Write
# ==========
# Get file object
def open_file_reader(filepath: str, compression="auto", binary=False):
    """
    Opens a file for reading with optional compression.

    Args:
        filepath (str): Path to the file.
        compression (str, optional): Type of compression {None, 'gzip', 'bz2'}. Defaults to "auto".
        binary (bool, optional): Whether to open the file in binary mode. Defaults to False.

    Returns:
        file object: A file-like object.
    """
    # Determine compression type based on the file extension if 'auto' is specified
    if compression == "auto":
        ext = filepath.split(".")[-1].lower()
        if ext == "gz":
            compression = "gzip"
        elif ext == "bz2":
            compression = "bz2"
        else:
            compression = None

    # Determine the mode based on the 'binary' flag
    mode = "rb" if binary else "rt"

    # Open the file with or without compression
    if not compression:
        return open(filepath, mode)
    elif compression == "gzip":
        return gzip.open(filepath, mode)
    elif compression == "bz2":
        return bz2.open(filepath, mode)
    else:
        raise ValueError(f"Unsupported compression type: {compression}")
            
# Get file object
def open_file_writer(filepath: str, compression="auto", binary=False):
    """
    Args:
        filepath (str): path/to/file
        compression (str, optional): {None, gzip, bz2}. Defaults to "auto".
        binary (bool, optional): Whether to open the file in binary mode. Defaults to False.
    
    Returns:
        file object
    """
    if compression == "auto":
        ext = filepath.split(".")[-1].lower()
        if ext == "gz":
            compression = "gzip"
        elif ext == "bz2":
            compression = "bz2"
        else:
            compression = None

    if binary:
        mode = "wb"
    else:
        mode = "wt"

    if not compression:
        return open(filepath, mode)
    elif compression == "gzip":
        return gzip.open(filepath, mode)
    elif compression == "bz2":
        return bz2.open(filepath, mode)
    else:
        raise ValueError(f"Unsupported compression type: {compression}")
    

def read_list(filepath:str, into=list, compression:str="auto", comment:str="#"):
    """
    Reads a file line-by-line into a list of strings.

    Parameters:
        filepath (str): path/to/file
        into (callable): callable to convert the list of strings into a different data structure. Defaults to list.
        compression (str, optional): {None, gzip, bz2}. Defaults to "auto".
        comment (str, optional): the comment character to ignore. Defaults to "#".

    Returns:
        into: the converted list of strings
    """
    contents = list()
    with open_file_reader(filepath, compression=compression) as f:
        if comment:
            for line in f:
                line = line.strip()
                if line:
                    if not line.startswith(comment):
                        contents.append(line)
        else:
            for line in f:
                line = line.strip()
                if line:
                    contents.append(line)
    return into(contents)

def gzip_file(source_filepath: str, destination_filepath: str, logger=None):
    """
    Compress a source file using gzip and write it to a destination file.

    Args:
        source_filepath (str): Path to the source file to be gzipped.
        destination_filepath (str): Path to the destination file to write the gzipped output.  
	If directory, then uses basename from source_filepath and adds .gz extension

    Returns:
        None

    Raises:
        FileNotFoundError: If the source file does not exist.
        IOError: If there are issues with reading or writing files.
    """
    try:
        if os.path.isdir(destination_filepath):
            destination_filepath = os.path.join(destination_filepath, os.path.basename(source_filepath) + ".gz")
        if logger:
            logger.info(f" - Gzipping {source_filepath} --> {destination_filepath}")
        with open(source_filepath, "rb") as src:
            with gzip.open(destination_filepath, "wb") as dest:
                shutil.copyfileobj(src, dest)

    except FileNotFoundError as e:
        msg = f"Source file '{source_filepath}' not found: {e}"
        if logger:
            logger.critical(msg)
        raise Exception(msg)
    except IOError as e:
        msg = f"An I/O error occurred while processing the files: {e}"
        if logger:
            logger.critical(msg)
        raise Exception(msg)
    

def copy_file(source_filepath, destination_filepath, gzip=False, logger=None):
    """
    Copies a file or directory to a specified destination path. Supports both directory and specific file paths.
    Optionally compresses files with gzip.

    Parameters:
        source_filepath (str): Path to the source file or directory to be copied.
        destination_filepath (str): Path to the destination directory or file.
        gzip (bool, optional): If True, compress the file using gzip before copying. Defaults to False.
        logger (logging.Logger, optional): Logger for messages. Defaults to None.

    Raises:
        FileNotFoundError: If the source file or directory does not exist.
        ValueError: If gzip is True and destination_filepath is not a directory.
        IOError: If there are issues with reading or writing the file or directory.
    """
    # Normalize
    source_filepath = os.path.normpath(source_filepath)
    destination_filepath = os.path.normpath(destination_filepath)
    
    # Check if the source exists
    if not os.path.exists(source_filepath):
        raise FileNotFoundError(f"Source path not found: {source_filepath}")

    # Resolve symlink if the source is a symlink
    if os.path.islink(source_filepath):
        source_filepath = os.path.realpath(source_filepath)

    try:
        if gzip:
            if os.path.isdir(source_filepath):
                msg = f"Gzip compression is not supported for directories: {source_filepath}"
                if logger:
                    logger.critical(msg)
                raise ValueError(msg)

            # Ensure destination_filepath is a directory
            if not os.path.isdir(destination_filepath):
                os.makedirs(destination_filepath, exist_ok=True)

            # Gzip compression (assumes a gzip_file function exists)
            gzip_file(source_filepath, destination_filepath, logger=logger)
        else:
            # Ensure parent directory
            parent_directory = os.path.dirname(destination_filepath)
            if parent_directory:
                os.makedirs(parent_directory, exist_ok=True)
            # Source[File] --> Destination[File]
            if all([
                not os.path.isdir(source_filepath),
                not os.path.isdir(destination_filepath),
                ]):
                if logger:
                    logger.info(f" - Copying file {source_filepath} --> {destination_filepath}")
                shutil.copy(source_filepath, destination_filepath)
                
            # Source[File] --> Destination[Directory]
            elif all([
                not os.path.isdir(source_filepath),
                os.path.isdir(destination_filepath),
                ]):
                destination_filepath = os.path.join(destination_filepath, os.path.basename(source_filepath))
                if logger:
                    logger.info(f" - Copying file {source_filepath} --> {destination_filepath}")
                shutil.copy(source_filepath, destination_filepath)
            # Source[Directory] --> Destination[Directory]
            elif os.path.isdir(source_filepath):
                if os.path.exists(destination_filepath):
                    if not os.path.isdir(destination_filepath):
                        msg = f"If source is a directory, destination must be a directory: {source_filepath} -!-> {destination_filepath}"
                        if logger:
                            logger.critical(msg)
                        raise ValueError(msg)
                    subdirectory = source_filepath.split("/")[-1]
                    destination_filepath = os.path.join(destination_filepath, subdirectory)
                # Handle directories
                if logger:
                    logger.info(f" - Copying directory {source_filepath} --> {destination_filepath}")
                shutil.copytree(source_filepath, destination_filepath, dirs_exist_ok=True)


    except IOError as e:
        msg = f"Failed to copy {source_filepath} to {destination_filepath}: {e}"
        if logger:
            logger.critical(msg)
        raise IOError(msg)

# Pickle I/O
def read_pickle(filepath, compression="auto"):
    with open_file_reader(filepath, compression=compression, binary=True) as f:
        return pickle.load(f)
    
def write_pickle(obj, filepath, compression="auto"):
    with open_file_writer(filepath, compression=compression, binary=True) as f:
        pickle.dump(obj, f)
        
# Json I/O
def read_json(filepath):
    with open_file_reader(filepath, compression=None, binary=False) as f:
        return json.load(f)
    
def write_json(obj, filepath, indent=4):
    with open_file_writer(filepath, compression=None, binary=False) as f:
        return json.dump(obj, f, indent=indent)
    
# Archive
# =======
def archive_subdirectories(parent_directory:str, output_directory:str):
    """
    Creates .tar.gz archives for each subdirectory in the given parent directory.

    Parameters:
        parent_directory (str): Path to the directory containing subdirectories to archive.
        output_directory (str): Path to the directory where archives will be saved.
    """
    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)

    # Iterate through each subdirectory
    for subdir in tqdm(os.listdir(parent_directory), "Creating archives", unit=" directories"):
        subdir_path = os.path.join(parent_directory, subdir)

        # Skip files; only process directories
        if not os.path.isdir(subdir_path):
            continue

        # Define the archive name
        archive_name = os.path.join(output_directory, f"{subdir}.tar.gz")

        # Create the tar.gz archive
        with tarfile.open(archive_name, "w:gz") as archive:
            archive.add(subdir_path, arcname=subdir)
            print(f"Archived: {subdir_path} -> {archive_name}", file=sys.stderr)
    
# Formatting
# ==========
# Get duration
def format_duration(duration):
    """
    Format the elapsed time since `t0` in hours, minutes, and seconds.
    
    Adapted from @john-fouhy:
    https://stackoverflow.com/questions/538666/python-format-timedelta-to-string
    """
    hours, remainder = divmod(int(duration), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

# Format header for printing
def format_header(text, line_character="=", n=None):
    if n is None:
        n = len(text)
    line = n*line_character
    return "{}\n{}\n{}".format(line, text, line)

# Format memory
def format_bytes(B, unit="auto", return_units=True):
    """
    Return the given bytes as a human-readable string in KB, MB, GB, or TB.
    1 KB = 1024 Bytes

    Adapted from the following source (@whereisalext):
    https://stackoverflow.com/questions/12523586/python-format-size-application-converting-b-to-kb-mb-gb-tb/52379087
    """
    KB = 1024
    MB = KB ** 2  # 1,048,576
    GB = KB ** 3  # 1,073,741,824
    TB = KB ** 4  # 1,099,511,627,776

    def format_with_unit(size, unit_name):
        return f"{size:.2f} {unit_name}" if return_units else size

    unit = unit.lower()
    if unit != "auto":
        unit = unit.lower()
        if unit == "b":
            return format_with_unit(B, "B")
        elif unit == "kb":
            return format_with_unit(B / KB, "KB")
        elif unit == "mb":
            return format_with_unit(B / MB, "MB")
        elif unit == "gb":
            return format_with_unit(B / GB, "GB")
        elif unit == "tb":
            return format_with_unit(B / TB, "TB")
        else:
            raise ValueError(f"Unknown unit: {unit}")
    else:
        if B < KB:
            return format_with_unit(B, "B")
        elif KB <= B < MB:
            return format_with_unit(B / KB, "KB")
        elif MB <= B < GB:
            return format_with_unit(B / MB, "MB")
        elif GB <= B < TB:
            return format_with_unit(B / GB, "GB")
        else:
            return format_with_unit(B / TB, "TB")
        
# Logging
# =======
def build_logger(logger_name=__name__, stream=sys.stdout, level=logging.INFO):
    """
    Build a logger object that outputs to a given stream.
    If a logger with the same name already exists, it is overwritten.

    Args:
        logger_name (str, optional): Name of the logger. Defaults to __name__.
        stream (TextIO, optional): Where to output the logs. Defaults to sys.stdout.

    Returns:
        logging.Logger: The logger object.
    """
    # Check if the logger already exists and remove its handlers
    if logger_name in logging.root.manager.loggerDict:
        existing_logger = logging.getLogger(logger_name)
        for handler in existing_logger.handlers[:]:
            existing_logger.removeHandler(handler)
    
    # Create or overwrite the logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)  # Set the logging level

    # Create a stream handler to output logs to stdout
    stream_handler = logging.StreamHandler(stream)
    stream_handler.setLevel(level)  # Set the level for the handler

    # Create a formatter and set it to the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(stream_handler)

    return logger
    
def reset_logger(logger):
    """
    Reset the logger to remove all existing handlers and set a new handler to output to stdout.

    Args:
        logger (logging.Logger): The logger object to reset.

    Returns:
        None
    """
    # Remove all existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    
    # Set a new handler (for example, to output to stdout)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    # Optionally set a new level
    logger.setLevel(logging.DEBUG)
    
# Timestamp
def get_timestamp(format_string:str="%Y-%m-%d %H:%M:%S"):
    """
    Return a string representing the current date and time.

    Args:
        format_string (str): The format string to use when generating the timestamp string.
            Defaults to "%Y-%m-%d %H:%M:%S".

    Returns:
        str: The timestamp string.
    """
    # Get the current date and time
    now =  datetime.now()
    # Create a timestamp string
    return now.strftime(format_string)

# Check argument choices
def check_argument_choice(query, choices:set):

    """
    Check that a given argument choice is in a set of allowed choices.

    Raises
    ------
    ValueError
        If the given argument choice is not in the set of allowed choices.

    Parameters
    ----------
    query : str
        The argument choice to check
    choices : set
        The set of allowed choices
    """
    choices = set(choices)
    if query not in choices:
        raise ValueError(f"Invalid option '{query}'. Allowed choices are: {choices}")

# Profiling
# =========
def profile_peak_memory(func):
    """
    Decorator to measure and log the peak memory usage of a function.

    Parameters
    ----------
    func : callable
        The function to measure and log the peak memory usage of.

    Returns
    -------
    callable
        The decorated function.

    Notes
    -----
    This decorator uses the `memory_usage` function from the `memory_profiler`
    library to measure the memory usage of the decorated function. The peak
    memory usage is then logged to the console.

    Example
    -------
    >>> @profile_peak_memory
    ... def my_function():
    ...     # Do something that uses a lot of memory
    ...     return
    >>> my_function()
    Peak memory usage for my_function: 123.45 MB
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Measure memory usage
        mem_usage = memory_usage((func, args, kwargs), max_usage=True, retval=True, max_iterations=1)
        peak_memory, result = mem_usage[0], mem_usage[1]
        print(f"Peak memory usage for {func.__name__}: {format_bytes(peak_memory)}")
        return result
    return wrapper

def pv(iterable, description=None, version=None, total=None, unit='it'):
    """
    Display a progress bar for an iterable using `tqdm`.

    Parameters
    ----------
    iterable : iterable
        The iterable to attach the progress bar to.
    description : str, optional
        A string describing the progress bar, displayed before it. Defaults to None.
    version : str, optional
        The version of `tqdm` to use. Can be "gui", "notebook", or None for the standard version. Defaults to None.
    total : int, optional
        The total number of iterations. If not provided, it will be determined automatically. Defaults to None.
    unit : str, optional
        The unit of measurement for each iteration. Defaults to 'it'.

    Returns
    -------
    tqdm.std.tqdm or tqdm.notebook.tqdm or tqdm.gui.tqdm
        An instance of the `tqdm` progress bar initialized with the specified parameters.

    Raises
    ------
    ValueError
        If `version` is not one of the allowed choices: None, "gui", or "notebook".

    Notes
    -----
    This function is a wrapper for the `tqdm` library to create and display progress bars.
    """

    check_argument_choice(version, {None, "gui",  "notebook"})
    func = tqdm
    if version == "notebook":
        func = tqdm_notebook
    if version == "gui":
        func = tqdm_gui

    return tqdm(
        iterable,
        desc=description,
        total=total,
        unit=unit,
   )
    
    
# Directory
# =========
def get_filepath_basename(filepath: str, compression: str = "auto"):
    """
    Return the base name of a file path without the file extension.

    Parameters
    ----------
    filepath : str
        The file path to extract the base name from
    compression : str
        The compression type of the file. Options are "auto", "gzip", "bz2", or None.

    Returns
    -------
    str
        The base name of the file
    """
    if "/" in filepath:
        _, fn = os.path.split(filepath)
    else:
        fn = filepath

    if compression == "auto":
        if fn.endswith(".gz"):
            compression = "gzip"
        elif fn.endswith(".bz2"):
            compression = "bz2"
        else:
            compression = None

    if compression:
        if compression == "gzip":
            fn = fn[:-3]
        elif compression == "bz2":
            fn = fn[:-4]
    if "." in fn:
        return ".".join(fn.split(".")[:-1])
    else:
        return fn

def get_file_size(filepath:str, format=False):
    """
    Get the size of a file.

    Parameters
    ----------
    filepath : str
        The file path of the file to get the size of.
    format : bool
        Whether to format the size in bytes to a human-readable format.

    Returns
    -------
    int or str
        The size of the file in bytes, or the size formatted as a string.
    """
    size_in_bytes = os.stat(filepath).st_size
    if format:
        return format_bytes(size_in_bytes)
    else:
        return size_in_bytes
    
def check_file(filepath:str, empty_ok=False, minimum_filesize=1): # Doesn't handle empty gzipped files
    """
    Check if a file exists and is not empty.

    Parameters
    ----------
    filepath : str
        The path to the file to check.
    empty_ok : bool
        Whether an empty file is allowed. Defaults to False.
    minimum_filesize : int
        The minimum size of the file in bytes. Defaults to 1.

    Raises
    ------
    FileNotFoundError
        If the file does not exist or is empty and `empty_ok` is False.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(filepath)
    if not empty_ok:
        if get_file_size(filepath) < minimum_filesize:
            raise FileNotFoundError(filepath)

def get_executable_in_path(executable_name:str):
    """
    Check if an executable is in the PATH.

    Parameters
    ----------
    executable_name : str
        The name of the executable to check.

    Returns
    -------
    str or None
        The path to the executable, or None if it is not in the PATH.
    """
    return shutil.which(executable_name)

def add_executables_to_environment(executable_names:list, environment:dict=os.environ, logger=None):
    """
    Add an executables to the environment.

    Parameters
    ----------
    executable_names : list
        A list of executable names to add to the environment.
    environment : dict
        The environment dictionary to add the executables to. [Default: `os.environ`]
    logger : logging.Logger
        Optional logger to output messages to.

    Raises
    ------
    FileNotFoundError
        If any of the executables are not found in the PATH.
    """
    for name in executable_names:
        path = get_executable_in_path(name)
        if path:
            environment[name] = path
            msg = f"Added {path} to environment"
            if logger:
                logger.info(msg)
            else:
                print(msg)

        else:
            msg = f"Could not find {name} executable in PATH"
            if logger:
                logger.error(f"Could not find {name} in PATH")
            raise FileNotFoundError(msg)
            

# md5 hash from file
def get_md5hash_from_file(filepath:str, block_size=65536):
    """
    Calculate the MD5 hash of a file.

    Parameters:
    - file_path: The path to the file.
    - block_size: The size of each block read from the file (default is 64KB).

    Returns:
    - A string containing the MD5 hash.
    """
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            md5.update(block)
    return md5.hexdigest()

# md5 hash from directory
def get_md5hash_from_directory(directory:str):
    """
    Calculate the MD5 hash of all files in a directory.

    Parameters:
    - directory_path: The path to the directory.

    Returns:
    - A dictionary where the keys are file paths and the values are their MD5 hashes.
    """
    md5_hashes = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.isfile(file_path):
                file_md5 = get_md5hash_from_file(file_path)
                md5_hashes[file_path] = file_md5
    return md5_hashes

# Get directory tree structure
def get_directory_tree(root, ascii=False):
    """
    Get the directory tree structure as a string.

    Parameters:
    - root: The path to the root of the directory tree.
    - ascii: Whether to return the directory tree as an ASCII string (default is False).
    """
    if not ascii:
        return DisplayablePath.view(root)
    else:
        return DisplayablePath.get_ascii(root)

# Directory size
def get_directory_size(directory:str='.'):
    """
    Adapted from @Chris:
    https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
    """

    total_size = 0
    seen = {}
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                stat = os.stat(fp)
            except OSError:
                continue

            try:
                seen[stat.st_ino]
            except KeyError:
                seen[stat.st_ino] = True
            else:
                continue

            total_size += stat.st_size

    return total_size


# Classes
# =======
class RunShellCommand(object):
    """
    Args: 
        command:str command to be executed
        name:str name associated with command [Default: None]
        shell_executable:str path to executable [Default: /bin/bash]
        
    Usage: 
        cmd = RunShellCommand("time (sleep 5 & echo 'Hello World')", name="Demo")
        cmd.run()
        cmd
        # ================================================
        # RunShellCommand(name:Demo)
        # ================================================
        # (/bin/bash)$ time (sleep 5 & echo 'Hello World')
        # ________________________________________________
        # Properties:
        #     - stdout: 61.00 B
        #     - stderr: 91.00 B
        #     - returncode: 0
        #     - peak memory: 37.22 B
        #     - duration: 00:00:05

    """

    def __init__(
        self, 
        command:str, 
        name:str=None, 
        shell_executable:str="/bin/bash",
        validate_input_filepaths:list=None,
        validate_output_filepaths:list=None,
        ):

        if isinstance(command, str):
            command = [command]
        command = " ".join(list(filter(bool, map(str, command))))
        self.command = command
        self.name = name
        self.shell_executable = shell_executable
        self.validate_input_filepaths = validate_input_filepaths if validate_input_filepaths else list()
        self.validate_output_filepaths = validate_input_filepaths if validate_input_filepaths else list()
        self.executed = False
        
    def run(self, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **popen_kws):
        def execute_command(stdout, stderr):
            # Execute the process
            self.process_ = subprocess.Popen(
                self.command,
                shell=True,
                stdout=stdout,
                stderr=stderr,
                executable=self.shell_executable,
                universal_newlines=True,  # or text=True
                bufsize=1,  # Line-buffered mode
                **popen_kws,
            )
            # Wait until process is complete and return stdout/stderr
            self.stdout_, self.stderr_ = self.process_.communicate()

            # Flush the buffers
            if stdout is not None and hasattr(stdout, "flush"):
                stdout.flush()
            if stderr is not None and hasattr(stderr, "flush"):
                stderr.flush()

            # Capture return code
            self.returncode_ = self.process_.returncode

            # # Encode
            # if encoding:
            #     if self.stdout_:
            #         self.stdout_ = self.stdout_.decode(encoding)
            #     if self.stderr_:
            #         self.stderr_ = self.stderr_.decode(encoding)

        # I/O
        self.redirect_stdout = None
        if isinstance(stdout, str):
            self.redirect_stdout = stdout
            stdout = open(stdout, "w")

        self.redirect_stderr = None
        if isinstance(stderr, str):
            self.redirect_stderr = stderr
            stderr = open(stderr, "w")

        # Measure memory usage
        t0 = time.time()
        if self.validate_input_filepaths:
            for filepath in self.validate_input_filepaths:
                check_file(filepath, empty_ok=False)
        self.memory_usage_ = memory_usage((execute_command, (stdout, stderr,)), max_iterations=1)
        self.duration_ = time.time() - t0

        # Flush
        if hasattr(stdout, "flush"):
            stdout.flush()
        if hasattr(stderr, "flush"):
            stderr.flush()

        # Close
        if hasattr(stdout, "close"):
            stdout.close()
        if hasattr(stderr, "close"):
            stderr.close()

        self.peak_memory_ = max(self.memory_usage_)
        self.executed = True

        return self


    def __repr__(self):
        name_text = "{}(name:{})".format(self.__class__.__name__, self.name)
        command_text = "({})$ {}".format(self.shell_executable, self.command)
        n = max(len(name_text), len(command_text))
        pad = 4
        fields = [
            format_header(name_text,line_character="=", n=n),
            *format_header(command_text, line_character="_", n=n).split("\n")[1:],
            ]
        if self.executed:
            fields += [
            "Properties:",
            ]
            # stdout
            if self.redirect_stdout:
                fields += [
                pad*" " + "- stdout({}): {}".format(
                    self.redirect_stdout,
                    get_file_size(self.redirect_stdout, format=True),
                )
                ]
            else:
                fields += [
                pad*" " + "- stdout: {}".format(format_bytes(sys.getsizeof(self.stdout_))),
                ]
            # stderr
            if self.redirect_stderr:
                fields += [
                pad*" " + "- stderr({}): {}".format(
                    self.redirect_stderr,
                    get_file_size(self.redirect_stderr, format=True),
                )
                ]
            else:
                fields += [
                pad*" " + "- stderr: {}".format(format_bytes(sys.getsizeof(self.stderr_))),
                ]

            fields += [
            pad*" " + "- returncode: {}".format(self.returncode_),
            pad*" " + "- peak memory: {}".format(format_bytes(self.peak_memory_)),
            pad*" " + "- duration: {}".format(format_duration(self.duration_)),
            ]
        return "\n".join(fields)
    
    # Dump stdout, stderr, and returncode
    def dump(self, output_directory:str):    
        # stdout
        with open_file_writer(os.path.join(output_directory, f"{self.name}.o")) as f:
            print(self.stdout_, file=f)
        # stderr
        with open_file_writer(os.path.join(output_directory, f"{self.name}.e")) as f:
            print(self.stderr_, file=f)
        # returncode
        with open_file_writer(os.path.join(output_directory, f"{self.name}.returncode")) as f:
            print(self.returncode_, file=f)
            
    # Check status
    def check_status(self):
        if self.returncode_ != 0:
            raise subprocess.CalledProcessError(
                returncode=self.returncode_,
                cmd="\n".join([
                f"Command Failed: {self.command}",
                f"return code: {self.returncode_}",
                f"stderr:\n{self.stderr_}",
                ]),
            )
        else:
            if self.validate_output_filepaths:
                for filepath in self.validate_output_filepaths:
                    check_file(filepath, empty_ok=False)
            print(f"Command Successful: {self.command}", file=sys.stderr)

# # View directory structures
class DisplayablePath(object):
    """
    Source: https://github.com/jolespin/genopype
    
    Display the tree structure of a directory.

    Implementation adapted from the following sources:
        * Credits to @abstrus
        https://stackoverflow.com/questions/9727673/list-directory-tree-structure-in-python
    """
    display_filename_prefix_middle = '|__'
    display_filename_prefix_last = '|__'
    display_parent_prefix_middle = '    '
    display_parent_prefix_last = '|   '

    def __init__(self, path, parent_path, is_last):
        self.path = pathlib.Path(str(path))
        self.parent = parent_path
        self.is_last = is_last
        if self.parent:
            self.depth = self.parent.depth + 1
        else:
            self.depth = 0

    @property
    def displayname(self):
        if self.path.is_dir():
            return self.path.name + '/'
        return self.path.name

    @classmethod
    def make_tree(cls, root, parent=None, is_last=False, criteria=None):
        root = pathlib.Path(str(root))
        criteria = criteria or cls._default_criteria

        displayable_root = cls(root, parent, is_last)
        yield displayable_root

        children = sorted(list(path
                               for path in root.iterdir()
                               if criteria(path)),
                          key=lambda s: str(s).lower())
        count = 1
        for path in children:
            is_last = count == len(children)
            if path.is_dir():
                for item in cls.make_tree(path, parent=displayable_root, is_last=is_last, criteria=criteria):
                    yield item
            else:
                yield cls(path, displayable_root, is_last)
            count += 1

    @classmethod
    def _default_criteria(cls, path):
        return True

    @property
    def displayname(self):
        if self.path.is_dir():
            return self.path.name + '/'
        return self.path.name

    def displayable(self):
        if self.parent is None:
            return self.displayname

        _filename_prefix = (self.display_filename_prefix_last
                            if self.is_last
                            else self.display_filename_prefix_middle)

        parts = ['{!s} {!s}'.format(_filename_prefix,
                                    self.displayname)]

        parent = self.parent
        while parent and parent.parent is not None:
            parts.append(self.display_parent_prefix_middle
                         if parent.is_last
                         else self.display_parent_prefix_last)
            parent = parent.parent

        return ''.join(reversed(parts))

    # Additions by Josh L. Espinoza for Soothsayer
    @classmethod
    def get_ascii(cls, root):
        ascii_output = list()
        paths = cls.make_tree(root)
        for path in paths:
            ascii_output.append(path.displayable())
        return "\n".join(ascii_output)
    @classmethod
    def view(cls, root, file=sys.stdout):
        print(cls.get_ascii(root), file=file)
        
# Genomics
def fasta_writer(header:str, seq:str, file:TextIO, wrap:int=1000):
    """
    Write a FASTA record to a file

    Parameters
    ----------
    header : str
        FASTA header
    seq : str
        FASTA sequence
    file : TextIO
        File to write the FASTA record to
    wrap : int, optional
        Wrap the sequence at this many characters, by default 1000
    """
    # Write the FASTA header
    print(f">{header}", file=file)
    
    if wrap:
        # Write the sequence with lines of length 'wrap'
        for i in range(0, len(seq), wrap):
            # Get a chunk of the sequence with a max length of 'wrap'
            line = seq[i:i+wrap]
            print(line, file=file)
    else:
        print(seq, file=file)
        
def fastq_writer(header: str, seq: str, quality: str, file: TextIO):
    """
    Write a FASTQ record to a file
    
    Parameters
    ----------
    header : str
        FASTQ header (without @ prefix)
    seq : str
        FASTQ sequence
    quality : str
        FASTQ quality scores (must be same length as seq)
    file : TextIO
        File to write the FASTQ record to
    """
    # Single write operation is much faster than 4 separate prints
    file.write(f"@{header}\n{seq}\n+\n{quality}\n")

from typing import Union, Set, Optional, TextIO

def parse_attribute_from_gff(
    file: Union[str, TextIO], 
    attribute_key: str, 
    feature_type: Optional[Union[str, Set[str]]] = "CDS"
):
    """
    Parse GFF file and yield (contig_id, attribute_value) for specified feature types.
    
    Parameters
    ----------
    file : str or file-like object
        Path to GFF file (can be gzipped) or file handle (e.g., sys.stdin)
    attribute_key : str
        Attribute key to extract (e.g., 'locus_tag', 'gene_id')
    feature_type : str, set of str, or None, default "CDS"
        Feature type(s) to filter for (e.g., 'CDS', {'CDS', 'mRNA'}).
        If None, all feature types are included.
    
    Yields
    ------
    tuple of (str, str)
        (contig_id, attribute_value)
    """
    # Normalize feature_type to set for consistent handling
    if feature_type is None:
        feature_types = None  # Check all feature types
    elif isinstance(feature_type, str):
        feature_types = {feature_type}
    else:
        feature_types = set(feature_type)
    
    # Determine if we need to open/close the file
    if isinstance(file, str):
        f = open_file_reader(file)
        should_close = True
    else:
        f = file
        should_close = False
    
    try:
        for line in tqdm(f, desc=f"Parsing GFF: {file}"):
            # Skip comment/header lines
            if line.startswith('#'):
                continue
            
            fields = line.strip().split('\t')
            
            # GFF has 9 columns
            if len(fields) < 9:
                continue
            
            id_contig = fields[0]
            feature = fields[2]
            attributes = fields[8]
            
            # Check if this feature type matches (skip check if feature_types is None)
            if feature_types is not None and feature not in feature_types:
                continue
            
            # Parse attributes (format: key1=value1;key2=value2;...)
            for attr in attributes.split(';'):
                if '=' in attr:
                    key, value = attr.split('=', 1)  # Split only on first '='
                    if key == attribute_key:
                        yield id_contig, value
                        break  # Found the attribute, move to next line
    finally:
        if should_close:
            f.close()