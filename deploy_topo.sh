#!/bin/bash
kubectl apply -f k8s_deployment/
sleep 5
export PORT_NUM=$(kubectl get svc testapp-svc-0 -o go-template='{{range.spec.ports}}{{if .nodePort}}{{.nodePort}}{{"\n"}}{{end}}{{end}}')
