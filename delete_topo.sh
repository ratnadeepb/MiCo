#!/bin/bash
kubectl delete -f k8s_deployment/
sleep 2
./rm_hpa_rules.py
