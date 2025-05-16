"""
First Frame

Takes a YUV420 video, resolution as input and outputs the first frame,
Y channel only
"""

import argparse
import re


def is_valid_resolution(a: str):
    res_re = r"(\d+)x(\d+)"
    match = re.fullmatch(res_re, a)
    if not match:
        raise argparse.ArgumentTypeError(f"{a} is not a valid resolution")
    return match.group(1), match.group(2)


parser = argparse.ArgumentParser(
    prog="FirstFrame",
    description="Takes a YUV420 video, resolution as input and outputs the first frame, Y channel only",
)

parser.add_argument("file", type=argparse.FileType("rb"))
parser.add_argument("-r", "--resolution", type=is_valid_resolution)

args = parser.parse_args()

width, height = map(int, args.resolution)

num_bytes = width * height

img_buffer = args.file.read(num_bytes)
for byte in img_buffer:
    print(f"{byte:02x}")
