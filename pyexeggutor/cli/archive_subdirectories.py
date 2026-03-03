#!/usr/bin/env python
import sys
import os
import argparse
from pyexeggutor import archive_subdirectories

def main():
    parser = argparse.ArgumentParser(description="Archive each subdirectory into a .tar.gz file.")
    parser.add_argument("-i", "--parent_directory", type=str, help="Path to the parent directory containing subdirectories.")
    parser.add_argument("-o", "--output_directory", type=str, help="Path to the output directory where archives will be saved.")
    args = parser.parse_args()

    archive_subdirectories(args.parent_directory, args.output_directory)

if __name__ == "__main__":
    main()