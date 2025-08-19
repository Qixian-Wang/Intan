import os
from pydantic import BaseModel, ConfigDict
import numpy as np
from datetime import datetime

class Configs(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    command_time: float = 0.2
    command_buffer_size: int = 1024

    num_channels: int = 32
    channel_head: str = "a"

    # Stimulation parameters
    stimulation_amp: float | int = 0.1 # miu_A
    stimulation_time: int = 200 # miu_S

    # Pipline parameters
    stimulation_interval_per_pattern: int = 2
    train_phase_interval_per_pattern: int = 4
    stimulation_number: int = 4


    max_impedance: float = 3.5e6
    min_impedance: float = 1e5

    log_file_name: str = f"experiment_log_{datetime.now().date()}.txt"

    
configs = Configs()