import sys
import concurrent.futures
from scipy.io import wavfile
import numpy as np
import math
import argparse
from tqdm import tqdm


parser = argparse.ArgumentParser(
    prog="Encoder", description="Encodes binary into audio"
)

parser.add_argument(
    "-i",
    "--inputfiles",
    type=argparse.FileType("r"),
    nargs="+",
    help="Paths to one or more input files",
    required=True,
)
parser.add_argument(
    "-o",
    "--output",
    type=str,
    help="Path at which output WAV will be stored",
    required=True,
)
parser.add_argument(
    "-fm",
    "--freqmin",
    type=int,
    default=200,
    help="The minimum frequency which the decoder's microphone will be able to accurately pick up",
)
parser.add_argument(
    "-fM",
    "--freqmax",
    type=int,
    default=16000,
    help="The maximum frequency which the decoder's microphone will be able to accurately pick up",
)
parser.add_argument(
    "-fs",
    "--samplerate",
    type=int,
    default=44100,
    help="The desired sampling rate of the encoded audio in hz",
)
parser.add_argument(
    "-s",
    "--fftsize",
    type=int,
    default=4096,
    help="The window size of the discrete fourier transform that would be run on the decoder side",
)

args = parser.parse_args()

files = args.inputfiles
output = args.output


freq_min = args.freqmin
freq_max = args.freqmax
fs = args.samplerate
FFT_SIZE = args.fftsize


def read_file(file_name):
    with open(file_name, "rb") as file:
        return file.read()


# Dictionary to hold phase state for each frequency
phase_dict = {}


def generate_note(freq, time):
    # Number of samples in this block
    N = int(fs * time)

    # Compute time axis for this block
    t = np.arange(N) / fs

    # Retrieve previous phase (or initialize to 0)
    phase = phase_dict.get(freq, 0.0)

    # Generate waveform with starting phase
    wave = np.sin(2 * np.pi * freq * t + phase)

    # Compute how much phase we advanced in this block
    delta_phase = 2 * np.pi * freq * (N / fs)

    # Store updated phase, wrapped into [0, 2π)
    phase_dict[freq] = (phase + delta_phase) % (2 * np.pi)

    return wave


def encode(byte_streams):
    """
    Encode a list of byte streams into an audio waveform by mapping bits to spectral bins.
    - byte_streams: list of bytes-like objects
    """
    # Precompute parameters
    time = 0.1  # in seconds
    longest_len = max(len(s) for s in byte_streams)
    spectrum_size = freq_max - freq_min
    band_size = math.ceil(spectrum_size / len(byte_streams))
    hz_per_bin = (fs / FFT_SIZE) * 10  # bin size
    bins_per_band = int(band_size / hz_per_bin)
    num_windows = math.ceil((longest_len * 8) / bins_per_band)

    samples = None
    for p in tqdm(range(num_windows)):
        # Initialize one window's worth of samples (silence)
        window_samples = np.zeros(int(fs * time), dtype=float)

        # For each stream, map its bits into its frequency band
        for i, stream in enumerate(byte_streams):
            band_start = freq_min + i * (bins_per_band * hz_per_bin)
            for j in range(bins_per_band):
                bit_index = p * bins_per_band + j
                if bit_index < len(stream) * 8:
                    byte_idx = bit_index // 8
                    bit_pos = bit_index % 8
                    if (stream[byte_idx] >> (7 - bit_pos)) & 1:
                        freq = (
                            band_start + j * hz_per_bin
                        )  # (hz_per_bin * bins_per_band * i)
                        window_samples += generate_note(freq, time)

        # print("samples", samples)
        # Append or initialize the full signal
        if samples is None:
            samples = window_samples
        else:
            samples = np.concatenate((samples, window_samples))

    samples /= np.max(np.abs(samples))
    return samples


print("Reading files.")
with concurrent.futures.ThreadPoolExecutor() as executor:
    future_to_file = {executor.submit(read_file, file.name): file for file in files}

byte_streams = [future.result() for future in future_to_file]
signal = encode(byte_streams)
signal = np.int16(signal * 32767)


wavfile.write(output, fs, signal)
print(f"File has been written at {output}")
