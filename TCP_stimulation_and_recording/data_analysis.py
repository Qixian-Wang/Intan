import scipy.signal as sig
import numpy as np
import matplotlib.pyplot as plt

COMMAND_BUFFER_SIZE = 1024
NUM_CHANNELS = 32
CHANNEL_HEAD = "b"
WAVEFORM_BUFFER_SIZE = 20000000
FRAMES_PER_BLOCK = 128
FREQUENCY = 30000
TIMESTEP = 1 / FREQUENCY

def readUint32(array, arrayIndex):
    """Reads 4 bytes from array as unsigned 32-bit integer.
    """
    variableBytes = array[arrayIndex: arrayIndex + 4]
    variable = int.from_bytes(variableBytes, byteorder='little', signed=False)
    arrayIndex = arrayIndex + 4
    return variable, arrayIndex


def readInt32(array, arrayIndex):
    """Reads 4 bytes from array as signed 32-bit integer.
    """
    variableBytes = array[arrayIndex: arrayIndex + 4]
    variable = int.from_bytes(variableBytes, byteorder='little', signed=True)
    arrayIndex = arrayIndex + 4
    return variable, arrayIndex


def readUint16(array, arrayIndex):
    """Reads 2 bytes from array as unsigned 16-bit integer.
    """
    variableBytes = array[arrayIndex: arrayIndex + 2]
    variable = int.from_bytes(variableBytes, byteorder='little', signed=False)
    arrayIndex = arrayIndex + 2
    return variable, arrayIndex


def bandpass_filter(data, lowcut=300, highcut=3000, order=3):
    nyq = 0.5 * FREQUENCY
    b, a = sig.butter(order, [lowcut/nyq, highcut/nyq], btype='band')
    return sig.filtfilt(b, a, data)


def detect_spikes(filtered, thresh_std=5, dead_time_ms=1.0, window_ms=1.0):
    spike_times = [[] for _ in range(NUM_CHANNELS)]
    for ch in range(NUM_CHANNELS):
        thresh = 10 #-thresh_std * np.std(filtered[ch])
        crossings = np.where((filtered[ch][:-1] > thresh) & (filtered[ch][1:] <= thresh))[0] + 1
        dead_samples = int(dead_time_ms * 1e-3 * FREQUENCY)
        half_win = int(window_ms * 1e-3 * FREQUENCY / 2)

        spikes_idx = []
        last_idx = -np.inf
        for idx in crossings:
            if idx - last_idx < dead_samples:
                continue
            if idx - half_win < 0 or idx + half_win >= len(filtered[ch]):
                continue
            spikes_idx.append(idx)
            last_idx = idx

        spike_times[ch] = np.array(spikes_idx) / FREQUENCY
    return spike_times


def decode_data(rawData, numBlocks):
    rawIndex = 0
    timestamps = []
    data = [[] for _ in range(NUM_CHANNELS)]
    for block in range(numBlocks):
        # Expect 4 bytes to be TCP Magic Number as uint32.
        magicNumber, rawIndex = readUint32(rawData, rawIndex)
        if magicNumber != 0x2ef07a08:
            print(f"Bad magic number at block {block}, position {rawIndex-4}: 0x{magicNumber:08x}")
            raise AssertionError('Error... magic number incorrect')

        # Each block should contain 128 frames of data - process each of these one-by-one
        for _ in range(FRAMES_PER_BLOCK):
            # Expect 4 bytes to be timestamp as int32.
            rawTimestamp, rawIndex = readInt32(rawData, rawIndex)
            timestamps.append(rawTimestamp * TIMESTEP)

            # Expect 2 bytes of wideband data for each channel.
            for ch in range(NUM_CHANNELS):
                rawSample, rawIndex = readUint16(rawData, rawIndex)
                data[ch].append(0.195 * (rawSample - 32768))
            
    return timestamps, data

def data_analysis(rawData, numBlocks):
    # Decode timestamp and data
    timestamps, data = decode_data(rawData, numBlocks)

    # Bandpass filter
    filtered = bandpass_filter(data, lowcut=300, highcut=3000, order=3)

    # Detect spikes
    spike_times = detect_spikes(filtered, thresh_std=5, dead_time_ms=1.0, window_ms=1.0)
    
    # Raster plot
    plt.figure(figsize=(10, 6))
    for ch in range(NUM_CHANNELS):
        plt.plot(spike_times[ch], np.ones(len(spike_times[ch])) * ch, '|', color='red', markersize=6)
    plt.xlabel('Time (s)')
    plt.ylabel('Channel')
    plt.title('Raster Plot')
    plt.show()