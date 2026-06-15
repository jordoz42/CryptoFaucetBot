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

### 2. Claim Faucets (hourly)
```bash
# One-time claim
python faucet_claimer.py

# Daemon mode - runs every hour automatically
python faucet_claimer.py --daemon
```

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
# Register on all 6 sites
./run.sh myrefcode123

# Register only on BNB and DOGE
./run.sh myrefcode123 --sites bnb-pick doge-pick

# Use custom email domain
./run.sh myrefcode123 --email-domain mydomain.com

# Custom credentials file
./run.sh myrefcode123 --credentials-file my_accounts.json
```

---

## Claimer Options

```bash
python faucet_claimer.py [OPTIONS]

Options:
  --credentials-file FILE     Accounts file (default: faucet_credentials.json)
  --headless                  Run headless (default: true)
  --daemon                    Run continuously every hour
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

## File Structure
```
faucet_registrar/
├── faucet_registrar.py    # Registration tool
├── faucet_claimer.py      # Automated claimer
├── run.sh                 # Launcher script
├── requirements.txt       # Python deps
├── faucet_credentials.json  # Generated accounts (gitignored)
└── venv/                  # Virtual environment
```

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
- Consider CAPTCHA solving services for automation

### Login Failures
- Clear cookies/cache in browser context
- Check if site structure changed
- Verify credentials in `faucet_credentials.json`

### Sites Unreachable
- `tongame.io` and `bchgame.io` appear defunct/not resolving
- Tool only works on the 6 active pick.io sites# CryptoFaucetBot
