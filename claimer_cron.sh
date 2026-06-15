#!/usr/bin/env bash
# Cron wrapper - activates venv and runs claimer

cd /home/main/faucet_registrar
source venv/bin/activate
python faucet_claimer.py --headless --credentials-file faucet_credentials.json >> claimer.log 2>&1