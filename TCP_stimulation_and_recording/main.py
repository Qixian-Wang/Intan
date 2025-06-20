import os
import time
import socket
import numpy as np
import matplotlib.pyplot as plt

from data_analysis import data_analysis
from data_analysis import (
    COMMAND_BUFFER_SIZE,
    NUM_CHANNELS,
    CHANNEL_HEAD,
    WAVEFORM_BUFFER_SIZE,
    FRAMES_PER_BLOCK,
)


def ReadWaveformDataDemo():
    # Connect to TCP command server - default home IP address at port 5000.
    print('Connecting to TCP command server...')
    scommand = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    scommand.connect(('128.174.126.145', 5000))

    # Connect to TCP waveform server - default home IP address at port 5001.
    print('Connecting to TCP waveform server...')
    swaveform = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    swaveform.connect(('128.174.126.145', 5001))

    # Query runmode from RHX software.
    scommand.sendall(b'get runmode')
    commandReturn = str(scommand.recv(COMMAND_BUFFER_SIZE), "utf-8")

    # If controller is running, stop it.
    if commandReturn != "Return: RunMode Stop":
        scommand.sendall(b'set runmode stop')
        time.sleep(0.1)

    # Query sample rate from RHX software.
    scommand.sendall(b'get sampleratehertz')
    commandReturn = str(scommand.recv(COMMAND_BUFFER_SIZE), "utf-8")
    expectedReturnString = "Return: SampleRateHertz "
    # Look for "Return: SampleRateHertz N" where N is the sample rate.
    if commandReturn.find(expectedReturnString) == -1:
        raise AssertionError(
            'Unable to get sample rate from server.'
        )

    # Clear TCP data output to ensure no TCP channels are enabled.
    scommand.sendall(b'execute clearalldataoutputs')
    time.sleep(0.1)

    waveformBytesPerFrame = 4 + NUM_CHANNELS * 2
    waveformBytesPerBlock = FRAMES_PER_BLOCK * waveformBytesPerFrame + 4

    for ch in range(NUM_CHANNELS):
        cmd = f"set {CHANNEL_HEAD}-{ch:03d}.tcpdataoutputenabled true"
        scommand.sendall(cmd.encode('utf-8'))
        time.sleep(0.1)

    for channel in range(NUM_CHANNELS):
        # configure stim parameters
        cmd_str = f"set {CHANNEL_HEAD}-{channel:03d}.stimenabled true"
        scommand.sendall(cmd_str.encode('utf-8'))
        time.sleep(0.1)
        cmd_str = f"set {CHANNEL_HEAD}-{channel:03d}.source keypressf1"
        scommand.sendall(cmd_str.encode('utf-8'))
        time.sleep(0.1)
        cmd_str = f"set {CHANNEL_HEAD}-{channel:03d}.firstphaseamplitudemicroamps 10"
        scommand.sendall(cmd_str.encode('utf-8'))
        time.sleep(0.1)
        cmd_str = f"set {CHANNEL_HEAD}-{channel:03d}.firstphasedurationmicroseconds 500"
        scommand.sendall(cmd_str.encode('utf-8'))
        time.sleep(0.1)
        cmd_str = f"execute uploadstimparameters {CHANNEL_HEAD}-{channel:03d}"
        scommand.sendall(cmd_str.encode('utf-8'))
        time.sleep(1)

        # Every second for 5 seconds, execute a ManualStimTriggerPulse command
        rawData = bytearray()
        scommand.sendall(b'set runmode run')
        time.sleep(0.1)

        print("Acquiring data, and stimulating every second")
        start_time = time.time()
        while time.time() - start_time < 5:
            swaveform.recv(WAVEFORM_BUFFER_SIZE)
            scommand.sendall(b'execute manualstimtriggerpulse f1')
            time.sleep(1)
            data_chunk = swaveform.recv(WAVEFORM_BUFFER_SIZE)
            rawData.extend(data_chunk)
            print(f"data_chunk length: {len(data_chunk)}")
            print(f"total length: {len(rawData)}")

        scommand.sendall(b'set runmode stop')
        time.sleep(0.1)
        swaveform.recv(WAVEFORM_BUFFER_SIZE)
        swaveform.close()

        # Find magic number and make sure data starts with it
        magic_positions = []
        for i in range(len(rawData) - 3):
            value = int.from_bytes(rawData[i:i+4], byteorder='little', signed=False)
            if value == 0x2ef07a08:
                magic_positions.append(i)
    
        if magic_positions[0] != 0:
            print(f"Data doesn't start with magic number. Trimming first {magic_positions[0]} bytes.")
            rawData = rawData[magic_positions[0]:]
        
        numBlocks = int(len(rawData) / waveformBytesPerBlock)
        print(f"Calculated number of blocks: {numBlocks}")

        # Save data to file
        save_path = "data"
        os.makedirs(save_path, exist_ok=True)
        with open(f"{save_path}/data_stimulation_channel_{channel}.bin", "wb") as f:
            f.write(rawData)

        data_analysis(rawData, numBlocks)

if __name__ == '__main__':
    ReadWaveformDataDemo()
