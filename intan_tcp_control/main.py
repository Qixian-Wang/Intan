from config_file import configs

from stimulation import run_training_pipline
from mea_yaml.mea_layout import mea_channel_filter


with open(configs.log_file_name, "w") as file:
    file.write("Log created:\n")

impedance_path = "C:/Users/qixianw2/Desktop/intan_tcp/mea_yaml/impedance.csv"
mea_file_path = "C:/Users/qixianw2/Desktop/intan_tcp/mea_yaml/128_rhs.yaml"

patterns = ["block1", "block2", "block3", "block4"]
selected_channels, mea_data = mea_channel_filter(patterns, impedance_path, mea_file_path, plot_layout=True)

pipline = [("train", 20), ("rest", 100),
           ("pretrain", 200), ("rest", 600), ("train", 20), ("rest", 1800),
           ("pretrain", 200), ("rest", 600), ("train", 20), ("rest", 1800),
           ("pretrain", 200), ("rest", 600), ("train", 20), ("rest", 1800),
           ("pretrain", 200), ("rest", 600), ("train", 20)]

with open(configs.log_file_name, "a") as file:
    file.write("expected pipline:\n")
    file.write(f"{str(pipline)}\n")

run_training_pipline(selected_channels, pipline, mea_data)








