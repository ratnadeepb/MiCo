#!/usr/bin/env python3
import  yaml

DEP_DIR = "k8s_deployment/{}"

def parse_config() -> list:
    """
        Get number of layers and replicas in each layer
        @return: tuple - (index, replicas)
    """
    global INDICES
    with open("app/config.yaml", 'r') as y:
        read_data = yaml.load(y, Loader=yaml.FullLoader)
    indices = []
    for i in range(len(read_data)):
        indices.append([read_data[i]['index'], read_data[i]['replicas']])
    return indices

def writeConfig(image):
    """
        Create the K8s deployment/service file for each layer
    """
    indices = parse_config()
    for elem in indices:
        index = elem[0]
        replicas = elem[1]
        name = "testapp-svc-{}".format(index)

        fname = DEP_DIR.format("testapp-svc-{}.yaml".format(index))

        # the service part
        svc = {'apiVersion': 'v1',
                        'kind': 'Service', 
                        'metadata': {'name': name},
                        'spec': {'selector': {'app': name},
                                'ports': [{'protocol': 'TCP',
                                            'port': 5000,
                                            'targetPort': 5000 }],
                        'type': 'LoadBalancer' }
                        }

        # the deployment part
        deployment = {'apiVersion': 'apps/v1',
                        'kind': 'Deployment',
                        'metadata': {'name': name,
                                        'labels': { 'app': name
                                        }
                        },
                        'spec': { 'replicas': replicas,
                                    'selector': {'matchLabels': {'app': name}},
                                    'template': {'metadata': {'labels': {'app': name}},
                                                    'spec': {'containers': 
                                                                [{'name': name,
                                                                    'image': image,
                                                                    'ports': [
                                                                        {'containerPort': 5000}
                                                                    ],
                                                                    'resources': {'limits': {'memory': '100Mi', 'cpu': '1500m'},
                                                                                'requests': {'memory': '50Mi', 'cpu': '1000m'}
                                                                    }
                                                    }]}
                                    },
                        }
        }

        # write both parts to the same yaml
        with open(fname, 'w') as file:
            yaml.dump(svc, file)
            file.write("\n---\n\n")
            yaml.dump(deployment, file)

def usage():
    print("{} <image_name>".format(__file__))

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        usage()
    else:
        image = sys.argv[1]
        writeConfig(image)