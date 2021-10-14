#!/bin/bash
export dir=$(dirname $(realpath $0))
kubectl delete -f $dir/k8s_deployment/
sleep 2
$dir/rm_hpa_rules.py $dir
