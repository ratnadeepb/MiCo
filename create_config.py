#!/usr/bin/env python3
import networkx as nx
import yaml

# values to be collected from users
node_count = 3
edge_count = 2
replicas = [2, 4, 2]
costs = [2, 2, 4]
bads = [0, 0, 1]
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
    # too expensive?
    for edge in H.edges:
        # print(edge[0][-1])
        if edge[0] == 'testapp-svc-%s' % idx:
            svc.append('testapp-svc-%s:5000/svc/%s' %
                       (edge[1][-1], edge[1][-1]))
        elif edge[1] == 'testapp-svc-%s' % idx:
            svc.append('testapp-svc-%s:5000/svc/%s' %
                       (edge[0][-1], edge[0][-1]))
    config_tmpl['svc'] = svc
    configs.append(config_tmpl)

# print(configs)

with open(fname, 'w') as file:
    yaml.dump(configs, file)
