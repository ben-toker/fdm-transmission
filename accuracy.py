import argparse
from subprocess import run
from os.path import getsize
from sys import stderr


def int_8(a):
    return int(a, base=8)


parser = argparse.ArgumentParser(
    prog="Bitwise Diff",
    description="""Performs a bitwise diff on two input files and gives byte
    and bit accuracy""",
)

parser.add_argument("infile1")
parser.add_argument("infile2")

args = parser.parse_args()

try:
    # Get filesizes from both, use smaller filesize as correct
    size = min(getsize(args.infile1), getsize(args.infile2))
except FileNotFoundError:
    stderr.write("Make sure paths are correctly input")
    exit(1)

size_bits = size * 8
in_command = ["cmp", "-l", args.infile1, args.infile2]

cmp_out = run(in_command, capture_output=True).stdout.split(b"\n")
if cmp_out[-1] == b"":
    del cmp_out[-1]
bad_bytes = len(cmp_out)
byte_accuracy = (1 - (bad_bytes / size)) * 100

for e in cmp_out:
    print(e)
print(f"Byte accuracy: {byte_accuracy:.3f}%")

total_bad_bits = 0
# Calculate bit accuracy
for diff in cmp_out:
    split = diff.split()
    split = split[1:3]
    split = list(map(int_8, split))
    for i in range(8):
        bits = [(a & (2**i)) >> i for a in split]
        if bits[0] != bits[1]:
            total_bad_bits += 1

bit_accuracy = (1 - (total_bad_bits / size_bits)) * 100
print(f"Bit accuracy: {bit_accuracy:.3f}%")
