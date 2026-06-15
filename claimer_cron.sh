#!/usr/bin/env bash
# Cron wrapper - activates venv and runs claimer with CAPTCHA solver

cd /home/main/faucet_registrar
source venv/bin/activate
# CAPTCHA_API_KEY should be set in environment or pass --captcha-api-key
python faucet_claimer.py --headless \
    --credentials-file faucet_credentials.json \
    --sessions-dir sessions \
    --captcha-provider 2captcha \
    --captcha-env-var CAPTCHA_API_KEY \
    >> claimer.log 2>&1