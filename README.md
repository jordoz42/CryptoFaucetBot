# Crypto Faucet Affiliate Toolkit

Tools for managing affiliate registrations and automated claiming on the "pick.io" family of crypto faucet sites.

## Sites Supported
All 9 sites share identical structure:
- **bnbpick.io** (BNB)
- **litepick.io** (LTC)
- **tronpick.io** (TRX)
- **dogepick.io** (DOGE)
- **suipick.io** (SUI)
- **polpick.io** (POL)
- **tonpick.game** (TON)
- **bchpick.io** (BCH)
- **solpick.io** (SOL)

Each offers: **50% referral commission** on faucet claims + 0.4% on games + 5% on gift cards.

---

## Quick Start

### 1. Prepare Your Referral Codes
Each site needs its own referral code. Three ways to provide them:

**Option A: JSON file (recommended)**
```bash
cp referral_codes_example.json my_codes.json
# Edit my_codes.json with your codes
./run.sh @my_codes.json
```

**Option B: Command line (key=value pairs)**
```bash
./run.sh "bnb-pick=CODE1,ltc-pick=CODE2,ton-pick=CODE3,..."
```

**Option C: Single code for all sites** (if you use the same code everywhere)
```bash
./run.sh YOUR_UNIVERSAL_CODE
```

### 2. Register Accounts
```bash
cd /home/main/faucet_registrar
./run.sh @my_codes.json
```

This opens browser windows for each site. You'll need to:
1. Complete the CAPTCHA manually on each site
2. Submit the registration form

Credentials are saved to `faucet_credentials.json`.

### 3. Automated Hourly Claiming (Main Function)
After registering accounts, **save login sessions once**, then cron claims automatically.

#### 1. Initial Session Setup (run once)
```bash
cd /home/main/faucet_registrar
source venv/bin/activate
python faucet_claimer.py --setup
```
Opens browser windows for each site. You:
1. Complete CAPTCHA manually
2. Login with saved credentials
3. Session cookies saved to `sessions/`

#### 2. Test Claim (verify sessions work)
```bash
python faucet_claimer.py
```
Runs one claim cycle headless using saved sessions.

#### 3. Cron Job (automatic hourly)
Pre-configured cron job runs hourly:
- **Job ID**: `4fc0c2b51c80` (faucet-hourly-claimer)
- **Schedule**: Every hour at minute 0
- **Runs**: `claimer_cron.sh` (activates venv, runs claimer headless)

Check logs:
```bash
cat /home/main/faucet_registrar/claimer.log
```

#### Session Management
- Sessions stored in `sessions/` directory (one JSON per site)
- If a session expires, re-run `--setup` for that site
- Sessions persist across restarts

---

## Registration Options

```bash
./run.sh YOUR_REF_CODE [OPTIONS]

Options:
  --email-domain DOMAIN       Email domain (default: protonmail.com)
  --username-prefix PREFIX    Username prefix (default: ref)
  --headless                  Run headless (not recommended - CAPTCHA)
  --credentials-file FILE     Output file (default: faucet_credentials.json)
  --sites SITE1 SITE2 ...     Specific sites only
```

### Examples
```bash
# Register on all 9 sites
./run.sh @my_codes.json

# Register only on BNB and DOGE
./run.sh @my_codes.json --sites bnb-pick doge-pick

# Use custom email domain
./run.sh @my_codes.json --email-domain mydomain.com

# Custom credentials file
./run.sh @my_codes.json --credentials-file my_accounts.json
```

---

## Claimer Options

```bash
python faucet_claimer.py [OPTIONS]

Options:
  --credentials-file FILE     Accounts file (default: faucet_credentials.json)
  --sessions-dir DIR          Sessions directory (default: sessions)
  --headless                  Run headless (default: true)
  --setup                     Interactive login to save sessions (run once)
  --daemon                    Run continuously every hour
```

---

## File Structure
```
faucet_registrar/
├── faucet_registrar.py       # Registration tool
├── faucet_claimer.py         # Automated claimer with session persistence
├── run.sh                    # Launcher script
├── claimer_cron.sh           # Cron wrapper script
├── requirements.txt          # Python deps
├── referral_codes_example.json  # Referral codes template
├── faucet_credentials.json   # Generated accounts (gitignored)
├── sessions/                 # Saved login sessions (gitignored)
└── venv/                     # Virtual environment
```

---

## Affiliate Marketing Strategy

### Generating Referrals
1. **Content Marketing** - Write guides/tutorials about each faucet
2. **Social Media** - Share referral links with proof of payments
3. **Faucet Lists** - Submit to faucet directories (faucetpay.io, etc.)
4. **YouTube/TikTok** - Show earnings, explain how to maximize claims
5. **Referral Contests** - Offer bonuses for signups under your link

### Encouraging Ongoing Participation
1. **Email Automation** - Send hourly claim reminders
2. **Telegram/Discord Bot** - Notify when faucet ready
3. **Leaderboard** - Track top referrers, reward them
4. **Bonus Pool** - Share portion of your earnings with active referrals
5. **Tutorial Content** - Teach how to maximize faucet + game earnings

---

## Security Notes
- **Never commit** `faucet_credentials.json` - contains passwords
- Use unique passwords per site (auto-generated)
- Consider using a password manager for long-term storage
- Email domain: use a catch-all or alias service

---

## Troubleshooting

### CAPTCHA Issues
Sites use multiple CAPTCHA providers (IconCaptcha, reCAPTCHA, hCaptcha, Turnstile, pCaptcha).
- Run in non-headless mode (default)
- Complete CAPTCHA manually in each browser window
- Consider CAPTCHA solving services for automation**
** Auto Captcha solver in pipeline, commit due very soon**
