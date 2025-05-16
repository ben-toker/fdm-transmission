from sys import stderr
from scipy.fft import fft
from scipy.io import wavfile
import argparse
import numpy
from bisect import bisect_right
from tqdm import tqdm


def is_positive(a: str):
    try:
        i = float(a)
    except ValueError:
        raise TypeError("bad sampling frequency value")
    if i <= 0:
        raise TypeError("bad sampling frequency value")
    return i


parser = argparse.ArgumentParser(
    prog="Decoder", description="Decodes encoded audio into bytestreams"
)

parser.add_argument("infile")
parser.add_argument("-n", "--num_bitstreams", type=int, default=1)
parser.add_argument(
    "-f",
    "--sampling_frequency",
    type=is_positive,
    help="Determines how often audio is sampled, measured in Hz",
    default=10,
)
parser.add_argument("-w", "--fft_window_size", type=int, default=4096)
parser.add_argument(
    "-t",
    "--threshold",
    type=int,
    default=-5,
    help="Measured in dB wrt the max amplitude of the source audio",
)
parser.add_argument("-u", "--upper_freq_bound", type=float, default=16000)
parser.add_argument("-l", "--low_freq_bound", type=float, default=200)
parser.add_argument("-o", "--output_prefix", required=True)
parser.add_argument(
    "-b", "--bin_size", help="Read only every b bins", type=int, default=10
)

args = parser.parse_args()

assert args.upper_freq_bound > args.low_freq_bound

sample_rate, audio = wavfile.read(args.infile)
print(f"Sample rate: {sample_rate}")

assert sample_rate / args.sampling_frequency > args.fft_window_size

# Need to convert fft-size into sample rate units
samps_per_frame = int(sample_rate / args.sampling_frequency)
fft_bin_size = sample_rate / (2 * args.fft_window_size)
frequency_key = numpy.arange(0, sample_rate / 2, fft_bin_size * 2)

# Pad audio with zeros until multiple of num_samps
audio_len = len(audio)
left = samps_per_frame - (audio_len % samps_per_frame)
audio = numpy.pad(audio, (0, left))

# Fold the array into a 2D array, splitting every samps_per_frame
audio.shape = (-1, samps_per_frame)

# Cut up audio such that we get fft_window_size samples per
low_idx = int((samps_per_frame - args.fft_window_size) / 2)
high_idx = int((samps_per_frame + args.fft_window_size) / 2)
# Grab the first samples from the last row instead of sampling from the middle
audio = numpy.vstack((audio[:-1, low_idx:high_idx], audio[-1, : args.fft_window_size]))

assert audio.shape[1] == args.fft_window_size


freq_values = fft(audio, norm="forward", overwrite_x=True)
# freq_values = numpy.array([a[1 : int(len(a) / 2)] for a in freq_values])
freq_values = numpy.absolute(freq_values)

low_bin = bisect_right(frequency_key, args.low_freq_bound)
high_bin = bisect_right(frequency_key, args.upper_freq_bound)
freq_values_sampled = numpy.array(
    [a[low_bin - 1 : high_bin - args.bin_size : args.bin_size] for a in freq_values]
)

assert freq_values_sampled.shape[1] >= args.num_bitstreams
max_freq = numpy.max(freq_values)
freq_values_db = 20 * numpy.log10(freq_values_sampled / max_freq)
stderr.write("[INFO] Finished FFT processing")

# Plotting for debug
# fig, ax = matplotlib.pyplot.subplots()
# ax.plot(numpy.arange(fvslen), freq_values_sampled[0])
# ax.grid()
# matplotlib.pyplot.show()
# breakpoint()


# Get frequencies for the start of each bin
bitstream_key = []
for i in range(args.num_bitstreams):
    num_bins = freq_values_sampled.shape[1]
    bitstream_key.append(int(i * num_bins / args.num_bitstreams))

# Initialize bit buffers
bit_buffers = [0 for _ in range(args.num_bitstreams)]
bit_buffer_counts = [0 for _ in range(args.num_bitstreams)]
out_fds = []

stderr.write("[INFO] Creating or truncating output files")
for i in range(args.num_bitstreams):
    name = args.output_prefix + str(i)
    out_fds.append(open(name, "wb"))
# Now we go through each frame
# TODO: multiprocessing
stderr.write("[INFO] Decoding and writing to files")
for frame in tqdm(freq_values_db):
    for bin_idx, bin_intensity in enumerate(frame):
        # Check upper and lower bounds
        # Else we have a bin with data in it
        # Figure out what bytestream it goes in
        band = bisect_right(list(bitstream_key), bin_idx) - 1
        # False = 1 = frequency present
        # True = 0 = frequency not present
        bit_buffers[band] <<= 1
        if bin_intensity > args.threshold:
            bit_buffers[band] |= 1
        bit_buffer_counts[band] += 1

        if bit_buffer_counts[band] >= 8:
            # Need to reverse every byte
            out_fds[band].write(bit_buffers[band].to_bytes())
            bit_buffers[band] = 0
            bit_buffer_counts[band] = 0

# Now that all of the bitstreams are complete, pad to nearest byte with zeros,
# push to bytestring, and write to file
for idx, count in enumerate(bit_buffer_counts):
    if count != 0:
        remainder = 8 - count
        bit_buffers[idx] <<= remainder
    out_fds[idx].write(bit_buffers[idx].to_bytes())

stderr.write("[INFO] Closing Files")
# Close all open files
for val in out_fds:
    val.close()
