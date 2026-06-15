#!/usr/bin/env bash
# Quick launcher for faucet registrar

cd "$(dirname "$0")"
source venv/bin/activate
python faucet_registrar.py "$@"