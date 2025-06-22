# Dial-up inspired signal transmission system

Oberlin College CSCI 342 Final Project
Ezra Crowe, Ethan Meltzer, Ben Toker

## Overview

This project is a multi-bitstream to audio codec that mimics behavior found in
analog transmission technologies like dialup.
The project mainly consists of two files, `encode.py` and `decode.py`.
`encode.py` accepts paths to multiple files and produces an audio file in `wav`
format. The decoder accepts a `wav` audio file as command line argument as well
as the number of bitstreams encoded in the input audio (`-n`) and the prefix
to name each output file (`-o`), which will have an index number appended to it.

## Running

If you have `uv` installed, the `pyproject.toml` specifies all dependencies and
versioning. Just substitute `uv run` in for `python` below.
Otherwise, make sure that `scipy` is available in your python environment, then
run

```
python encode.py -i INPUT_PATH1 [INPUT_PATH2 ...] -o "outputfile"
python decode.py INPUT_PATH -n NUM_OUTPUT_FILES -o OUTPUT_PREFIX
```

respectively for further information on arguments to supply.


## Testing

`accuracy.py` will compare two files using `cmp` and report all the bytes that
differ, as well as the percentage of bytes that match and the percentage of
bits that match in each file. If the files are different sizes, the shorter
file will be used to determine the number of total bytes/bits, and additional
data in the longer file is ignored. On a UNIX system with the `cmp` command
installed, run

```
python accuracy.py FILE1 FILE2
```
