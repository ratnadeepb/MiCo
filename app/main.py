#!/usr/bin/env python3

"""
    Extract index from the request path which should be in the form `/svc/index`
    Given the index, extract the associated urls and cost from the `config.yaml`
    Wait for time = cost -> this is done by sleep for now
    Make parallel calls to all urls in the urls list
    @return if all calls are successful, return success
            if any underlying call fails a 404 is returned
            calling `/statistics` return CPU and memory usage in percent along with function timings
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
from jaeger_logger_reporter import LoggerTraceConfig, LoggerTracerReporter
from opentracing.ext import tags
from opentracing.propagation import Format
from opentracing_instrumentation.request_context import get_current_span

LOCAL_RESPONSE_TIME = 0
TOTAL_RESPONSE_TIME = 0
START_TIME = time.time()
FREQ = 0


def init_tracer(service):
    tracer_logger = logging.getLogger("mico")
    tracer_logger.setLevel(logging.DEBUG)

    f_handler = logging.FileHandler("mico.log")
    s_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '[%(levelname)s][%(date)s] %(name)s %(span)s %(event)s %(message)s')
    s_handler.setFormatter(formatter)
    s_handler.setLevel(logging.DEBUG)
    f_handler.setFormatter(formatter)
    f_handler.setLevel(logging.DEBUG)

    tracer_logger.addHandler(s_handler)
    tracer_logger.addHandler(f_handler)

    config = LoggerTraceConfig(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'logging': True,
            'max_tag_value_length': sys.maxsize,
        },
        service_name=service
    )

    return config.initialize_tracer(logger_reporter=LoggerTracerReporter(logger=tracer_logger))


# tracer = init_tracer('testapp-svc')

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


@app.route("/health_check", methods=["GET"])
def health_check():
    return "OK\n"


@app.route("/statistics", methods=['GET'])
def get_stats() -> dict:
    """ Get data about CPU and memory usage """
    return {'cpu': cpu_usage(),
            'mem': mem_usage(),
            'local_response_time':  LOCAL_RESPONSE_TIME,
            'total_response_time': TOTAL_RESPONSE_TIME,
            'time': FREQ
            }


def failure_response(url: str, status: int) -> Response:
    """ Send failure response """
    return Response('Error: failed to access {}\n'.format(url), status=status)


IS_BAD_SERVER = -1
tracer = None


def http_get(url: str, headers) -> requests.models.Response:
    """ This is a helper function so we can instrument the calls """
    global tracer
    with tracer.start_active_span('http_get', child_of=get_current_span()) as scope:
        # span = tracer.active_span
        if not headers:
            scope.span.set_tag(tags.HTTP_METHOD, 'GET')
            scope.span.set_tag(tags.HTTP_URL, url)
            scope.span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_CLIENT)
            headers = {}
            tracer.inject(span_context=scope.span,
                          format=Format.HTTP_HEADERS, carrier=headers)
            scope.span.log_kv({'event': 'http_get'})
        return requests.get(url, headers=headers)


def serve_fn(start, cost, urls, index, headers=None):
    global TOTAL_RESPONSE_TIME
    global LOCAL_RESPONSE_TIME
    p = 1_000
    global tracer
    # span = tracer.active_span
    with tracer.start_active_span('http_get', child_of=get_current_span()) as scope:
        scope.span.log_kv(
            {'index': index, 'event': 'ranging-over-cost', 'cost': cost})
        for i in range(cost):
            largestPrime(p)
        LOCAL_RESPONSE_TIME = time.time() - start

        # url list is empty => this is a leaf node
        if urls is None or len(urls) == 0:
            TOTAL_RESPONSE_TIME = time.time() - start
            scope.span.log_kv({'index': index, 'event': 'url-none',
                               'local-response-time': LOCAL_RESPONSE_TIME, 'total-response-time': TOTAL_RESPONSE_TIME})
            return {'urls': None, 'cost': cost}
        else:  # non-leaf node
            try:  # request might fail
                _ = joblib.Parallel(prefer="threads", n_jobs=len(urls))(
                    (delayed(http_get)("http://{}".format(url), headers) for url in urls))
            except ConnectionError as e:  # send page not found if it does
                s = e.args[0].args[0].split()
                host = s[0].split('=')[1].split(',')[0]
                port = s[1].split('=')[1].split(')')[0]

                TOTAL_RESPONSE_TIME = time.time() - start

                return failure_response("{}:{}".format(host, port), 404)

            TOTAL_RESPONSE_TIME = time.time() - start

            # doesn't matter what is returned
            return {'urls': list(urls), 'cost': cost}


@app.route('/svc/<int:index>', methods=['GET'])
def serve(index) -> dict:
    """ Main workhorse function of the app """
    # global LOCAL_RESPONSE_TIME
    global START_TIME
    global FREQ

    # measure how many requests are we getting
    tmp = time.time()
    FREQ = tmp - START_TIME
    START_TIME = tmp

    start = time.time()

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

    global tracer
    name = 'testapp-svc-%s' % index
    if not tracer:
        tracer = init_tracer(name)

    if index == 0:
        with tracer.start_active_span('svc-0') as _span:
            return serve_fn(start, cost, urls, index)
    else:
        span_ctx = tracer.extract(Format.HTTP_HEADERS, request.headers)
        span_tags = {tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER}
        headers = request.headers
        with tracer.start_active_span('svc-non%s' % index, child_of=span_ctx, tags=span_tags) as _span:
            return serve_fn(start, cost, urls, index, headers)


if __name__ == "__main__":
    app.run(host='0.0.0.0')
