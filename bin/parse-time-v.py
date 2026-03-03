#!/usr/bin/env python
import sys
import argparse
import pandas as pd
from pyexeggutor import (
    open_file_reader,
    parse_time_v,
)

def main():
    parser = argparse.ArgumentParser(description="Parse /usr/bin/time -v output files")
    parser.add_argument("filepaths", nargs="+", metavar="filepath")
    parser.add_argument("-o", "--output", default="-", help="Output filepath [default: stdout]")
    opts = parser.parse_args()

    records = []
    for fp in opts.filepaths:
        with open_file_reader(fp) as f:
            metrics = parse_time_v(f.read())
        metrics["filepath"] = fp
        records.append(metrics)

    df = pd.DataFrame(records).set_index("filepath")

    output = sys.stdout if opts.output == "-" else opts.output
    df.to_csv(output, sep="\t")

if __name__ == "__main__":
    main()