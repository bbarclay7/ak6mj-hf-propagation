# Infrastructure Documentation

Infrastructure-specific documentation (server configurations, deployment procedures, network topology) is maintained in a separate private repository to keep sensitive details secure.

## Private Operations Repository

**Repository**: https://github.com/bbarclay7/homelab-ops (private)

This repo contains:
- Server hostnames, IP addresses, and network topology
- Detailed deployment procedures for specific infrastructure
- Service configurations and systemd unit files
- Monitoring and backup strategies
- Troubleshooting guides for specific servers

## What's Public (This Repo)

This repository contains:
- WSPR/antenna analysis tools and libraries
- Generic deployment documentation
- Web interface and CLI tools
- Test suites

## For Contributors

If you're deploying these tools to your own infrastructure:
1. Follow the generic deployment guides in `docs/DEPLOYMENT.md` and `docs/DEPLOYMENT_TEST.md`
2. Adapt the procedures to your specific setup
3. Keep your own infrastructure details in a private location (not this repo)

## For Maintainer

Infrastructure-specific setup for the production deployment at shoeph.one is documented in the private homelab-ops repository under `hf-tools/`.
