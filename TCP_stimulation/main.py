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

IP_ADDRESS = '127.0.0.1'
COMMAND_TIME = 0.2


def recv_all_available(sock, buffer_size=WAVEFORM_BUFFER_SIZE, timeout=0.1):
    """
    Read all available data from socket buffer exhaustively.
    
    Args:
        sock: Socket object
        buffer_size: Size of chunks to read at a time
        timeout: Timeout in seconds to wait for more data
    
    Returns:
        bytearray: All available data from the socket
    """
    sock.settimeout(timeout)
    data = bytearray()
    
    try:
        while True:
            chunk = sock.recv(buffer_size)
            if not chunk:
                break
            data.extend(chunk)
            # If we got less than requested, there might be no more data
            if len(chunk) < buffer_size:
                # Try one more time with a very short timeout
                sock.settimeout(0.01)
                try:
                    extra_chunk = sock.recv(buffer_size)
                    if extra_chunk:
                        data.extend(extra_chunk)
                    else:
                        break
                except socket.timeout:
                    break
    except socket.timeout:
        pass  # Expected when no more data is available
    
    # Reset socket to blocking mode
    sock.settimeout(None)
    return data

def clear_socket_buffer(sock, timeout=0.1):
    """
    Clear any remaining data in the socket buffer.
    
    Args:
        sock: Socket object
        timeout: Timeout for reading chunks
    """
    sock.settimeout(timeout)
    try:
        while True:
            data = sock.recv(WAVEFORM_BUFFER_SIZE)
            if not data:
                break
    except socket.timeout:
        pass
    sock.settimeout(None)


def ReadWaveformDataDemo():
    # Connect to TCP command server - default home IP address at port 5000.
    print('Connecting to TCP command server...')
    scommand = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    scommand.connect((IP_ADDRESS, 5000))

    # Connect to TCP waveform server - default home IP address at port 5001.
    print('Connecting to TCP waveform server...')
    swaveform = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    swaveform.connect((IP_ADDRESS, 5001))

    # Query runmode from RHX software.
    scommand.sendall(b'get runmode')
    commandReturn = str(scommand.recv(COMMAND_BUFFER_SIZE), "utf-8")

    # If controller is running, stop it.
    if commandReturn != "Return: RunMode Stop":
        scommand.sendall(b'set runmode stop')
        time.sleep(COMMAND_TIME)

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
    time.sleep(COMMAND_TIME)

    waveformBytesPerFrame = 4 + NUM_CHANNELS * 2
    waveformBytesPerBlock = FRAMES_PER_BLOCK * waveformBytesPerFrame + 4

    for ch in range(NUM_CHANNELS):
        cmd = f"set {CHANNEL_HEAD}-{ch:03d}.tcpdataoutputenabled true"
        scommand.sendall(cmd.encode('utf-8'))
        time.sleep(COMMAND_TIME)
    
    # Clear any initial data in the TCP buffer
    clear_socket_buffer(swaveform)
    print("TCP data output enabled for all channels and buffer cleared.")
    
    for channel in range(NUM_CHANNELS):
        # configure stim parameters
        cmd_str = f"set {CHANNEL_HEAD}-{channel:03d}.stimenabled true"
        scommand.sendall(cmd_str.encode('utf-8'))
        time.sleep(COMMAND_TIME)
        cmd_str = f"set {CHANNEL_HEAD}-{channel:03d}.source keypressf1"
        scommand.sendall(cmd_str.encode('utf-8'))
        time.sleep(COMMAND_TIME)
        cmd_str = f"set {CHANNEL_HEAD}-{channel:03d}.firstphaseamplitudemicroamps 10"
        scommand.sendall(cmd_str.encode('utf-8'))
        time.sleep(COMMAND_TIME)
        cmd_str = f"set {CHANNEL_HEAD}-{channel:03d}.firstphasedurationmicroseconds 500"
        scommand.sendall(cmd_str.encode('utf-8'))
        time.sleep(COMMAND_TIME)
        cmd_str = f"execute uploadstimparameters {CHANNEL_HEAD}-{channel:03d}"
        scommand.sendall(cmd_str.encode('utf-8'))
        time.sleep(1)
        
        # Original approach with warmup phase
        rawData = bytearray()
        
        # Clear any existing data in the waveform buffer before starting
        clear_socket_buffer(swaveform)
        
        scommand.sendall(b'set runmode run')
        time.sleep(COMMAND_TIME)

        print(f"Starting data acquisition for channel {channel}")
        print("Phase 1: System stabilization (3 warmup cycles)...")
        
        # Phase 1: Warmup phase - let the system stabilize but don't save data
        warmup_cycles = 10
        for warmup in range(warmup_cycles):
            print(f"Warmup cycle {warmup + 1}/{warmup_cycles}")
            
            # Trigger stimulation
            #scommand.sendall(b'execute manualstimtriggerpulse f1')
            
            # Wait longer for data to accumulate during warmup
            time.sleep(0.5)
            
            # Read and discard warmup data (just to clear buffers)
            warmup_data = recv_all_available(swaveform, timeout=0.8)
            print(f"  Warmup data size: {len(warmup_data)} bytes")
            
            # Wait for the rest of the second
            time.sleep(0.5)
        
        print("Phase 2: Actual data collection (5 seconds)...")
        
        # Phase 2: Actual data collection
        start_time = time.time()
        stim_count = 0
        
        try:
            while time.time() - start_time < 5:
                stim_count += 1
                print(f"Stimulation {stim_count}")
                
                # Trigger stimulation
                scommand.sendall(b'execute manualstimtriggerpulse f1')
                
                # Wait longer for data to accumulate (based on your observation)
                time.sleep(0.3)
                
                # Read all available data exhaustively with longer timeout
                data_chunk = recv_all_available(swaveform, timeout=0.8)
                
                if data_chunk:
                    rawData.extend(data_chunk)
                    print(f"  Data chunk length: {len(data_chunk)}")
                    print(f"  Total length: {len(rawData)}")
                else:
                    print("  No data received in this iteration")
                
                # Wait for the rest of the second
                time.sleep(0.7)
                
                elapsed_time = time.time() - start_time
                print(f"  Elapsed time: {elapsed_time:.2f}s")
                
        except KeyboardInterrupt:
            print("Acquisition interrupted by user")
        except Exception as e:
            print(f"Error during data acquisition: {e}")
        finally:
            # Always stop the run mode
            scommand.sendall(b'set runmode stop')
            time.sleep(COMMAND_TIME)
        
        # Read any final data that might still be coming
        print("Reading final data...")
        final_data = recv_all_available(swaveform, timeout=1.0)
        if final_data:
            rawData.extend(final_data)
            print(f"Final data chunk: {len(final_data)} bytes")
        
        # Clear remaining buffer
        clear_socket_buffer(swaveform)

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
