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

## Automated Hourly Claiming (Main Function)
After registering accounts, **save login sessions once**, then cron claims automatically.

### Option A: Manual Sessions (Free, Semi-Automated)
Session persistence handles login, but **each hourly claim still requires CAPTCHA**.
```bash
# 1. Initial Session Setup (run once)
cd /home/main/faucet_registrar
source venv/bin/activate
python faucet_claimer.py --setup

# 2. Test Claim (manual CAPTCHA each time)
python faucet_claimer.py --headless=false

# 3. Cron runs but you'll need to handle CAPTCHAs manually
```

### Option B: Fully Automated with CAPTCHA Solver (Recommended)
Integrate a CAPTCHA solving service for **fully automated hourly claims**.

**Supported providers**: 2Captcha, Anti-Captcha, CapMonster.cloud

**Cost**: ~$0.50-2.00 per 1000 solves (9 sites × 24hr = 216 solves/day ≈ $0.10-0.40/day)

#### Setup
```bash
# 1. Get API key from provider (2captcha.com, anti-captcha.com, capmonster.cloud)
# 2. Set environment variable
export CAPTCHA_API_KEY="your_api_key_here"

# 3. Test with solver
python faucet_claimer.py --captcha-provider 2captcha --captcha-env-var CAPTCHA_API_KEY
```

#### Cron Job (Automatic Hourly)
Pre-configured cron job runs hourly with solver:
- **Job ID**: `4fc0c2b51c80` (faucet-hourly-claimer)
- **Schedule**: Every hour at minute 0
- **Runs**: `claimer_cron.sh` (uses CAPTCHA_API_KEY env var)

Check logs:
```bash
cat /home/main/faucet_registrar/claimer.log
```

#### Session Management
- Sessions stored in `sessions/` directory (one JSON per site)
- If a session expires, re-run `--setup` for that site
- Sessions persist across restarts

---

## Claimer Options

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

# Basic options
  --credentials-file FILE     Accounts file (default: faucet_credentials.json)
  --sessions-dir DIR          Sessions directory (default: sessions)
  --headless                  Run headless (default: true)
  --setup                     Interactive login to save sessions (run once)
  --daemon                    Run continuously every hour

# CAPTCHA Solver options (for fully automated claiming)
  --captcha-provider PROVIDER  CAPTCHA service: 2captcha, anticaptcha, capmonster
  --captcha-api-key KEY        API key for solver (or use env var)
  --captcha-env-var NAME       Env var name for API key (default: CAPTCHA_API_KEY)
```

### CAPTCHA Solver Examples
```bash
# Test with 2Captcha (uses CAPTCHA_API_KEY env var)
export CAPTCHA_API_KEY="your_2captcha_key"
python faucet_claimer.py --captcha-provider 2captcha

# Test with Anti-Captcha via CLI arg
python faucet_claimer.py --captcha-provider anticaptcha --captcha-api-key YOUR_KEY

# Run daemon with solver
python faucet_claimer.py --daemon --captcha-provider 2captcha
```

---

## File Structure
```
faucet_registrar/
├── faucet_registrar.py       # Registration tool
├── faucet_claimer.py         # Automated claimer with session persistence
├── captcha_solver.py         # CAPTCHA solver abstraction layer
├── run.sh                    # Launcher script
├── claimer_cron.sh           # Cron wrapper script
├── requirements.txt          # Python deps
├── referral_codes_example.json  # Referral codes template
├── faucet_credentials.json   # Generated accounts (gitignored)
├── sessions/                 # Saved login sessions (gitignored)
└── venv/                     # Virtual environment
```

---

## CAPTCHA Solver Implementation

### Architecture

The CAPTCHA solving system is built as a **plug-and-play abstraction layer** in `captcha_solver.py`:

```
┌─────────────────────────────────────────────────────────────┐
│                    FaucetClaimer                            │
│  1. Detect CAPTCHA on page (iframe, image, etc.)           │
│  2. Build CaptchaChallenge object                          │
│  3. Call solver.solve(challenge) → CaptchaSolution         │
│  4. Inject solution into page (token or input fill)        │
└─────────────────────┬───────────────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
   ┌──────────┐ ┌───────────┐ ┌────────────┐
   │ 2Captcha │ │Anti-Captcha│ │ CapMonster │
   └──────────┘ └───────────┘ └────────────┘
```

### Key Components

#### 1. `CaptchaChallenge` - Input Data
```python
@dataclass
class CaptchaChallenge:
    type: CaptchaType           # RECAPTCHA_V2, RECAPTCHA_V3, HCAPTCHA, TURNSTILE, IMAGE_CAPTCHA
    site_key: Optional[str]     # For reCAPTCHA/hCaptcha/Turnstile (extracted from iframe)
    page_url: Optional[str]     # Current page URL
    image_base64: Optional[str] # For image CAPTCHAs (screenshot)
    extra_params: Optional[dict]# e.g., {"score": 0.3} for reCAPTCHA v3
```

#### 2. `CaptchaSolver` - Abstract Base Class
```python
class CaptchaSolver(ABC):
    async def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution
    async def report_good(self, challenge_id: str) -> None  # For refunds
    async def report_bad(self, challenge_id: str) -> None   # For refunds
```

#### 3. Provider Implementations
| Provider | Class | Supported Types | API Style |
|----------|-------|-----------------|-----------|
| **2Captcha** | `TwoCaptchaSolver` | All | Polling (in.php/res.php) |
| **Anti-Captcha** | `AntiCaptchaSolver` | reCAPTCHA, hCaptcha, Image | Task-based (createTask/getTaskResult) |
| **CapMonster** | `CapMonsterSolver` | Same as Anti-Captcha | Same API, different endpoint |

#### 4. Auto-Detection (`detect_captcha_type`)
```python
async def detect_captcha_type(page) -> Optional[CaptchaChallenge]:
    # 1. Check for reCAPTCHA iframe → extract sitekey from src
    # 2. Check for hCaptcha iframe → extract sitekey
    # 3. Check for Turnstile iframe → extract sitekey
    # 4. Check for image CAPTCHA (img[src*="captcha"]) → screenshot
```

#### 5. Solution Injection
```python
# For token-based (reCAPTCHA, hCaptcha, Turnstile):
await inject_recaptcha_solution(page, token)
# - Fills g-recaptcha-response textarea
# - Triggers callback if present

# For image CAPTCHAs:
await inject_image_captcha_solution(page, token)
# - Fills common input selectors (name="captcha", id*="captcha", etc.)
```

### Supported CAPTCHA Types on pick.io Sites

| CAPTCHA Type | Selector Detected | Solve Method | Providers |
|--------------|-------------------|--------------|-----------|
| **reCAPTCHA v2** | `iframe[src*="recaptcha"]` | Token injection | 2Captcha, Anti-Captcha, CapMonster |
| **reCAPTCHA v3** | `iframe[src*="recaptcha"]` + score param | Token injection | 2Captcha, Anti-Captcha, CapMonster |
| **hCaptcha** | `iframe[src*="hcaptcha"]` | Token injection | 2Captcha, Anti-Captcha, CapMonster |
| **Cloudflare Turnstile** | `iframe[src*="turnstile"]` | Token injection | 2Captcha, Anti-Captcha, CapMonster |
| **IconCaptcha / pCaptcha** | `img[src*="captcha"]` | Image OCR | 2Captcha, Anti-Captcha |

### Integration Flow (Per Claim)

```python
async def claim_faucet(self, page, site_name):
    # 1. Navigate to faucet page
    await page.goto(base_url)
    
    # 2. Find & click claim button
    await page.click(claim_selector)
    
    # 3. CAPTCHA appears → detect
    challenge = await detect_captcha_type(page)
    if challenge:
        # 4. Solve via API
        solution = await self.captcha_solver.solve(challenge)
        
        # 5. Inject solution
        if challenge.type in token_types:
            await inject_recaptcha_solution(page, solution.token)
        else:
            await inject_image_captcha_solution(page, solution.token)
        
        # 6. Re-click claim button (form now valid)
        await page.click(claim_selector)
```

### Provider Setup Details

#### 2Captcha (Recommended)
- **Cost**: ~$0.50-1.00/1000 solves
- **API**: `http://2captcha.com/in.php` + `res.php`
- **Features**: Supports all types, good success rate, refunds via reportgood/reportbad

```bash
# 1. Sign up at 2captcha.com
# 2. Add funds ($1 min)
# 3. Get API key
export CAPTCHA_API_KEY="your_2captcha_key"
python faucet_claimer.py --captcha-provider 2captcha
```

#### Anti-Captcha
- **Cost**: ~$0.50-2.00/1000 solves
- **API**: `https://api.anti-captcha.com/createTask` + `getTaskResult`
- **Features**: Task-based, supports proxy, good for enterprise

```bash
export CAPTCHA_API_KEY="your_anticaptcha_key"
python faucet_claimer.py --captcha-provider anticaptcha
```

#### CapMonster.cloud
- **Cost**: Similar to Anti-Captcha
- **API**: Compatible with Anti-Captcha (drop-in replacement)
- **Features**: Cloud-based, fast

```bash
export CAPTCHA_API_KEY="your_capmonster_key"
python faucet_claimer.py --captcha-provider capmonster
```

### Cost Calculation

```
9 sites × 24 hours = 216 claims/day
216 claims × 1 CAPTCHA each = 216 solves/day

2Captcha ($0.80/1000):  216 × 0.0008 = $0.17/day ≈ $5.10/month
Anti-Captcha ($1.50/1000): 216 × 0.0015 = $0.32/day ≈ $9.60/month
```

### Error Handling & Retries

- **Timeout**: 180s max wait for solve
- **Retries**: Automatic retry on "CAPCHA_NOT_READY"
- **Refunds**: `report_bad()` called if claim fails after solve
- **Fallback**: If solver fails, falls back to manual (with `--headless=false`)

### Security Notes

- **API Keys**: Never commit to git; use environment variables
- **Solver Credits**: Monitor balance; set up low-balance alerts
- **Rate Limits**: Providers have rate limits; 9 sites/hour is well within limits
- **ToS**: Check faucet site ToS for automated claiming policies

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
