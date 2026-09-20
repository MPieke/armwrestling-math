# Armwrestling Math Infrastructure

## Current architecture

Hetzner CX23
- Ubuntu 26.04
- 2 vCPU / 4 GB RAM
- k3s single-node Kubernetes cluster
- Traefik ingress controller
- Hetzner Cloud Firewall

## Security

SSH:
- TCP 22 exposed
- SSH key authentication only
- password authentication disabled
- root SSH disabled
- `armmath` is admin user with sudo

Public ports:
- 22 SSH
- 80/443 not yet opened

Postgres:
- not deployed
- never expose 5432 publicly

## Kubernetes

Single-node k3s cluster.

Currently learning with:
- `test` Deployment
- nginx container
- `test` ClusterIP Service
- Traefik installed by k3s
- `test` Ingress being configured

Traffic goal:

Internet
  ↓
Traefik
  ↓
Ingress
  ↓
Service
  ↓
Pod

## Useful commands

SSH:

    ssh armmath@<server-ip>

Cluster:

    sudo kubectl get nodes
    sudo kubectl get pods -A
    sudo kubectl get services -A
    sudo kubectl get ingress -A

k3s:

    sudo systemctl status k3s

See most resources:

    sudo kubectl get all -A§
