import time
import socket

from config_file import configs

def pre_run_checklist(scommand):
    """
    Pre-run checklist defined by intan tutorial.
    It is used to check if the controller is running and the sample rate is correct.

    Parameters
    ----------
    scommand: socket.socket
        The socket object for sending commands to the controller.
    """
    # If controller is running, stop it.
    scommand.sendall(b'get runmode')
    commandReturn = str(scommand.recv(configs.command_buffer_size), "utf-8")
    if commandReturn != "Return: RunMode Stop":
        scommand.sendall(b'set runmode stop')
        time.sleep(configs.command_time)

    # Query sample rate from RHX software.
    scommand.sendall(b'get sampleratehertz')
    commandReturn = str(scommand.recv(configs.command_buffer_size), "utf-8")
    expectedReturnString = "Return: SampleRateHertz "
    # Look for "Return: SampleRateHertz N" where N is the sample rate.
    if commandReturn.find(expectedReturnString) == -1:
        raise AssertionError(
            'Unable to get sample rate from server.'
        )

def set_up_stimulation(scommand, patterns, mea_data):
    """
    Set up stimulation for the experiment.
    Define the hotkey to trigger stimulation, stimulation channel and stimulation parameters.

    Parameters
    ----------
    scommand: socket.socket
        The socket object for sending commands to the controller.
    patterns: list
        The list of patterns to be used in the experiment.
    mea_data: dict
        The dictionary of MEA data.

    Return:
    -------
    pattern_key_pair: dict
        The dictionary of pattern key pair.
    """
    # Initialize the pattern key pair.
    pattern_key_pair = {tuple(pattern): None for pattern in patterns}
    pattern_index = 1

    for pattern in patterns:
        for channel in pattern:
            chip_title = mea_data[channel]['chip_title']
            index_on_chip = mea_data[channel]['chip_index']

            # Enable relative channels and hotkeys for stimulation.
            cmd_str = f"set {chip_title}-{index_on_chip}.stimenabled true"
            scommand.sendall(cmd_str.encode('utf-8'))
            time.sleep(configs.command_time)
            cmd_str = f"set {chip_title}-{index_on_chip}.source keypressf{pattern_index}"
            scommand.sendall(cmd_str.encode('utf-8'))
            time.sleep(configs.command_time)

            # Set stimulation parameters.
            cmd_str = f"set {chip_title}-{index_on_chip}.firstphaseamplitudemicroamps {configs.stimulation_amp}"
            scommand.sendall(cmd_str.encode('utf-8'))
            time.sleep(configs.command_time)
            cmd_str = f"set {chip_title}-{index_on_chip}.firstphasedurationmicroseconds {configs.stimulation_time}"
            scommand.sendall(cmd_str.encode('utf-8'))
            time.sleep(configs.command_time)
            cmd_str = f"set {chip_title}-{index_on_chip}.secondphaseamplitudemicroamps {configs.stimulation_amp}"
            scommand.sendall(cmd_str.encode('utf-8'))
            time.sleep(configs.command_time)
            cmd_str = f"set {chip_title}-{index_on_chip}.secondphasedurationmicroseconds {configs.stimulation_time}"
            scommand.sendall(cmd_str.encode('utf-8'))
            time.sleep(configs.command_time)

        pattern_key_pair[tuple(pattern)] = pattern_index
        pattern_index += 1

    scommand.sendall(b"execute UploadStimParameters")  
    time.sleep(30)
    
    return pattern_key_pair


def run_training_pipline(patterns, pipline, mea_data):
    """
    Run the training pipline.
    Parameters
    ----------
    patterns: list
        The list of patterns to be used in the experiment.
    pipline: list
        The list of phases to be used in the experiment.
    mea_data: dict
        The dictionary of MEA data.
    """
    initial_time = time.time()
    # Start TCP server, only send command
    print('Connecting to TCP command server...')
    scommand = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    scommand.connect(('128.174.126.145', 5000))

    # Set recording file name and path
    scommand.sendall(b'set Filename.BaseFilename qixian')
    time.sleep(configs.command_time)
    scommand.sendall(b'set Filename.Path E:/Qixian_intan_temp')
    time.sleep(configs.command_time)
    scommand.sendall(b'set CreateNewDirectory true')
    time.sleep(configs.command_time)

    # Run pre-run checklist defined by intan tutorial
    pre_run_checklist(scommand)

    # set save parameters
    scommand.sendall(b"set FileFormat Traditional")
    time.sleep(configs.command_time)
    scommand.sendall(b"set SaveWidebandAmplifierWaveforms false")
    time.sleep(configs.command_time)
    scommand.sendall(b"set SaveSpikeData true")
    time.sleep(configs.command_time)

    # set up stimulation
    pattern_key_pair = set_up_stimulation(scommand, patterns, mea_data)

    # Start recording
    scommand.sendall(b'set runmode record')
    time.sleep(configs.command_time)

    pretrain_interval = configs.stimulation_interval_per_pattern / configs.stimulation_number

    for phase, duration in pipline:

        with open(configs.log_file_name, "a") as file:
            file.write(f"step {phase} started, current time is: {time.time() - initial_time}\n")
    
        if phase == "pretrain":
            count = 0
            session_start_time = time.time()
            for _ in range(duration):
                for pattern in patterns:
                    for _ in range(configs.stimulation_number):
                        next_time = session_start_time + (count+1) * pretrain_interval
                        key = pattern_key_pair[tuple(pattern)]
                        scommand.sendall(f'execute manualstimtriggerpulse f{key}'.encode('utf-8'))

                        sleep_time = next_time - time.time()
                        if sleep_time < 0:
                            print("high latency: find sleep_time < 0")
                            time.sleep(pretrain_interval)
                        else:
                            time.sleep(sleep_time)

                        count += 1
                    
            print(f"pretrain done, time taken: {time.time() - session_start_time}")
    
        if phase == "train":
            count = 0
            session_start_time = time.time()
            for _ in range(duration):
                for pattern in patterns:
                    next_time = session_start_time + (count+1) * configs.train_phase_interval
                    key = pattern_key_pair[tuple(pattern)]
                    scommand.sendall(f'execute manualstimtriggerpulse f{key}'.encode('utf-8'))

                    sleep_time = next_time - time.time()
                    if sleep_time < 0:
                        print("high latency: find sleep_time < 0")
                        time.sleep(configs.train_phase_interval)
                    else:
                        time.sleep(sleep_time)
                        
                    count += 1
                    
            print(f"train done, time taken: {time.time() - session_start_time}")

        
        if phase == "rest":
            time.sleep(duration)

        with open(configs.log_file_name, "a") as file:
            file.write(f"step {phase} finished, current time is: {time.time() - initial_time}\n")

    scommand.sendall(b'set runmode stop')
    