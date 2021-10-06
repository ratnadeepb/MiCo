#!/usr/bin/env python3

import os

DEP_DIR = "k8s_deployment/"

def get_num_svcs(threshold):
    for name in os.listdir(DEP_DIR):
        cmd = f"kubectl autoscale deployment {name.split('.')[0]} --min=1 --max=5 --cpu-percent={threshold}"
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
    get_num_svcs(THRESHOLD)