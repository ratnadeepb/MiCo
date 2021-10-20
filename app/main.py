#!/usr/bin/env python3

"""
    Extract index from the request path which should be in the form `/svc/index`
    Given the index, extract the associated urls and cost from the `config.yaml`
    Wait for time = cost -> this is done by sleep for now
    Make parallel calls to all urls in the urls list
    @return if all calls are successful, return success
            if any underlying call fails a 404 is returned
            calling `/statistics` return CPU and memory usage in percent
"""

from flask import Flask, request
from flask.wrappers import Response
from joblib.parallel import delayed
import yaml
import sys
import time
import psutil
import requests
from requests.exceptions import ConnectionError
import joblib
import logging
import random

LOCAL_RESPONSE_TIME = 0
TOTAL_RESPONSE_TIME = 0
START_TIME = time.perf_counter()
FREQ = 0

app = Flask(__name__)


def isPrime(x) -> bool:
    k = 0
    for i in range(2, x // 2 + 1):
        if(x % i == 0):
            k = k + 1
    if k <= 0:
        return True
    else:
        return False


def largestPrime(x) -> int:
    prime = -1
    for num in range(x):
        if isPrime(num):
            prime = num
    return prime


def parse_config() -> list:
    """ Parse the config file """
    with open("config.yaml", 'r') as y:
        read_data = yaml.load(y, Loader=yaml.FullLoader)
    return read_data


def cpu_usage() -> float:
    """ Get CPU usage """
    return psutil.cpu_percent(interval=0.5)


def mem_usage():
    """ Get memory usage """
    return psutil.virtual_memory().percent


@app.route("/statistics", methods=['GET'])
def get_stats() -> dict:
    """ Get data about CPU and memory usage """
    return {'cpu': cpu_usage(),
            'mem': mem_usage(),
            'local_response_time':  LOCAL_RESPONSE_TIME,
            'total_response_time': TOTAL_RESPONSE_TIME,
            'perf_counter': FREQ
            }


def failure_response(url: str, status: int) -> Response:
    """ Send failure response """
    return Response('Error: failed to access {}\n'.format(url), status=status)


IS_BAD_SERVER = -1


def http_get(url: str) -> requests.models.Response:
    """ This is a helper function so we can instrument the calls """
    return requests.get(url)


def serve_fn(start, cost, urls, index, headers=None):
    global TOTAL_RESPONSE_TIME
    global LOCAL_RESPONSE_TIME
    p = 1_000
    for i in range(cost):
        largestPrime(p)
    LOCAL_RESPONSE_TIME = time.perf_counter() - start
    if urls is None:  # url list is empty => this is a leaf node
        TOTAL_RESPONSE_TIME = time.perf_counter() - start
        return {'urls': None, 'cost': cost}
    else:  # non-leaf node
        try:  # request might fail
            _ = joblib.Parallel(prefer="threads", n_jobs=len(urls))(
                (delayed(http_get)("http://{}".format(url), headers) for url in urls))
        except ConnectionError as e:  # send page not found if it does
            s = e.args[0].args[0].split()
            host = s[0].split('=')[1].split(',')[0]
            port = s[1].split('=')[1].split(')')[0]

            TOTAL_RESPONSE_TIME = time.perf_counter() - start

            return failure_response("{}:{}".format(host, port), 404)

        TOTAL_RESPONSE_TIME = time.perf_counter() - start

        # doesn't matter what is returned
        return {'urls': list(urls), 'cost': cost}


@app.route('/svc/<int:index>', methods=['GET'])
def serve(index) -> dict:
    """ Main workhorse function of the app """
    global START_TIME
    global FREQ

    # measure how many requests are we getting
    tmp = time.perf_counter()
    FREQ = tmp - START_TIME
    START_TIME = tmp

    start = time.perf_counter()

    # logger = logging.getLogger("mico_serve_logger")
    logging.basicConfig(filename="mico.log")

    index = list({index})[0]  # get the number from the param
    data = parse_config()  # get config data
    if len(data) < index + 1:  # number of elements in the config should equal to or more than the index
        sys.stderr.write("Error: Config file does not contain correct index")
        return failure_response("svc-{} doesn't exist".format(index), 500)

    d = data[index]  # get the config for the given index
    urls = d['svc']  # get all urls to be called
    cost = d['cost']  # cost of this call

    # the configuration server says if we want a bad component amongst
    bads = d['bads']
    if bads == 1:
        # the number of replicas will inform the chance of a replica failing
        replicas = d['replicas']
        prob = 1 / replicas
        # print("prob:", prob) # debug

        # based on how many replicas there are some servers are bad
        # but as of now, we only want leaf nodes to be potentially bad
        # we want to see if the problem potentially floats up
        global IS_BAD_SERVER
        if urls == None:  # if this is a leaf node
            # we want to change this value only once (as of now bad servers are bad from the start and don't flip over to the good side)
            if IS_BAD_SERVER == -1:
                if random.random() > prob:
                    IS_BAD_SERVER = 1
                else:
                    IS_BAD_SERVER = 0

        # print("bad server?", IS_BAD_SERVER) # DEBUG
        if IS_BAD_SERVER == 1:
            logging.debug("Bad Server")
            cost *= 5
            # cost *= replicas
        # print("cost:", cost) # DEBUG

    return serve_fn(start, cost, urls, index)


if __name__ == "__main__":
    app.run(host='0.0.0.0')
