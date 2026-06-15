#!/usr/bin/env bash
# Cron wrapper - activates venv and runs claimer with saved sessions

cd /home/main/faucet_registrar
source venv/bin/activate
python faucet_claimer.py --headless --credentials-file faucet_credentials.json --sessions-dir sessions >> claimer.log 2>&1