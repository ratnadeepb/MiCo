#!/usr/bin/env python3
import networkx as nx
import yaml
import sys
from numpy.random import randint

if len(sys.argv) < 3:
    sys.stderr.write("not enough arguments\n")
    sys.stderr.write(
        f"Usage: {__file__} <node_count|int> <edge_count|int> <max_cost|int>\n")
    sys.exit(1)

_node_count = int(sys.argv[1])
_edge_count = int(sys.argv[2])
max_cost = int(sys.argv[3])
# values to be collected from users
node_count = 3
edge_count = 2
# ultimately, we would want every service to start a single pod
_replicas = [1] * _node_count
print(_replicas)  # debug

replicas = [2, 4, 2]

costs = [2, 2, 4]
# create a list of random costs
_costs = randint(max_cost + 1, size=_node_count)
print(_costs)  # debug

bads = [0, 0, 1]
# randomly allow some services to have bad pods
_bads = randint(2, size=_node_count)
print(_bads)  # debug

fname = "test-config.yaml"
# =================================

map = {}
for i in range(node_count):
    map[i] = 'testapp-svc-%s' % i

G = nx.binomial_graph(node_count, edge_count)

H = nx.relabel_nodes(G, map)

configs = []

for item in map.items():
    config_tmpl = {}
    idx = item[0]
    config_tmpl['index'] = idx
    config_tmpl['replicas'] = replicas[idx]
    config_tmpl['cost'] = costs[idx]
    config_tmpl['bads'] = bads[idx]
    svc = []
    # too expensive???
    for edge in H.edges:
        if edge[0] == 'testapp-svc-%s' % idx:
            svc.append('testapp-svc-%s:5000/svc/%s' %
                       (edge[1][-1], edge[1][-1]))
        elif edge[1] == 'testapp-svc-%s' % idx:
            svc.append('testapp-svc-%s:5000/svc/%s' %
                       (edge[0][-1], edge[0][-1]))
    config_tmpl['svc'] = svc
    configs.append(config_tmpl)

with open(fname, 'w') as file:
    yaml.dump(configs, file)
