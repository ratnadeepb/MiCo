#!/usr/bin/env python3

import os
import yaml

DEP_DIR = "k8s_deployment/"

def parse_config() -> dict:
    """
        Get number of layers and replicas in each layer
        @return: tuple - (index, replicas)
    """
    data = {}
    with open("app/config.yaml", 'r') as y:
        read_data = yaml.load(y, Loader=yaml.FullLoader)

    for i in range(len(read_data)):
        data[read_data[i]['index']] = [read_data[i]['cost'], read_data[i]['replicas']]
    return data

def scale_deps(threshold):
    data = parse_config()
    for name in os.listdir(DEP_DIR):
        [cost, reps] = data[int(name.split('.')[0].split('-')[-1])]
        max_pods = cost * reps
        cmd = f"kubectl autoscale deployment {name.split('.')[0]} --min=1 --max={max_pods} --cpu-percent={threshold}"
        os.system(cmd)

def usage():
    print(f"{__file__} <cpu_threshold>")
    print(f"Using default CPU threshold of {THRESHOLD}")

if __name__ == "__main__":
    THRESHOLD = 50
    import sys
    if len(sys.argv) < 2:
        usage()
    else:
        THRESHOLD = int(sys.argv[1])
    scale_deps(THRESHOLD)
