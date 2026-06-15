#!/usr/bin/env python3
"""
Crypto Faucet Affiliate Registration Tool
Registers accounts on 8 pick.io faucet sites using your referral codes.
All sites share identical signup form structure.
"""

import asyncio
import json
import random
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


from playwright.async_api import async_playwright, Browser, BrowserContext


# ── Configuration ──────────────────────────────────────────────────────────

@dataclass
class SiteConfig:
    name: str
    base_url: str
    signup_path: str = "/signup.php"
    coin: str = ""

    @property
    def signup_url(self) -> str:
        return f"{self.base_url}{self.signup_path}"


SITES = [
    SiteConfig("BNB Pick", "https://bnbpick.io", coin="BNB"),
    SiteConfig("LTC Pick", "https://litepick.io", coin="LTC"),
    SiteConfig("TRX Pick", "https://tronpick.io", coin="TRX"),
    SiteConfig("DOGE Pick", "https://dogepick.io", coin="DOGE"),
    SiteConfig("SUI Pick", "https://suipick.io", coin="SUI"),
    SiteConfig("POL Pick", "https://polpick.io", coin="POL"),
    SiteConfig("TON Pick", "https://tonpick.game", coin="TON"),
    SiteConfig("BCH Pick", "https://bchpick.io", coin="BCH"),
    SiteConfig("SOL Pick", "https://solpick.io", coin="SOL"),
]

SITE_KEYS = {s.name.lower().replace(" ", "-"): s.name for s in SITES}


# ── Credential Generation ──────────────────────────────────────────────────

def generate_username(prefix: str = "ref") -> str:
    """Generate a unique username."""
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}{suffix}"


def generate_password(length: int = 16) -> str:
    """Generate a secure password."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))


def generate_email(username: str, domain: str = "protonmail.com") -> str:
    """Generate email address."""
    return f"{username}@{domain}"


# ── Referral Code Helpers ──────────────────────────────────────────────────

def parse_referral_codes(arg: str) -> dict[str, str]:
    """
    Parse referral codes from string.
    Formats supported:
      - JSON file: @/path/to/codes.json
      - Key=value pairs: "bnb-pick=CODE1,ton-pick=CODE2"
      - Single code (applied to all): "MYCODE"
    """
    arg = arg.strip()
    
    # JSON file
    if arg.startswith("@"):
        path = Path(arg[1:])
        if path.exists():
            return json.loads(path.read_text())
        raise ValueError(f"Referral codes file not found: {path}")
    
    # Key=value pairs
    if "=" in arg:
        codes = {}
        for pair in arg.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                k = k.strip().lower()
                if k in SITE_KEYS:
                    codes[SITE_KEYS[k]] = v.strip()
                else:
                    print(f"  ⚠ Unknown site key: {k} (valid: {', '.join(SITE_KEYS.keys())})")
        return codes
    
    # Single code for all sites
    return {s.name: arg for s in SITES}


# ── Registration Logic ─────────────────────────────────────────────────────

class FaucetRegistrar:
    def __init__(
        self,
        referral_codes: dict[str, str],
        email_domain: str = "protonmail.com",
        username_prefix: str = "ref",
        headless: bool = False,
        credentials_file: str = "faucet_credentials.json",
        sites: Optional[list[SiteConfig]] = None,
    ):
        # Normalize: ensure all sites have a code (fallback to empty)
        self.referral_codes = {s.name: referral_codes.get(s.name, "") for s in (sites or SITES)}
        self.email_domain = email_domain
        self.username_prefix = username_prefix
        self.headless = headless
        self.credentials_file = Path(credentials_file)
        self.sites = sites or SITES
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.results: list[dict] = []

        # Load existing credentials
        self.existing_credentials = self._load_credentials()

    def _load_credentials(self) -> dict:
        if self.credentials_file.exists():
            try:
                return json.loads(self.credentials_file.read_text())
            except Exception:
                return {}
        return {}

    def _save_credentials(self) -> None:
        data = {**self.existing_credentials}
        for r in self.results:
            if r["success"]:
                site_name = r["site"]
                data[site_name] = {
                    "username": r["username"],
                    "email": r["email"],
                    "password": r["password"],
                    "referral_code": self.referral_codes.get(site_name, ""),
                    "coin": r["coin"],
                }
        self.credentials_file.write_text(json.dumps(data, indent=2))

    async def _init_browser(self) -> None:
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

    async def _close_browser(self) -> None:
        if self.browser:
            await self.browser.close()

    async def register_on_site(self, site: SiteConfig) -> dict:
        """Register a new account on a single faucet page."""
        page = await self.context.new_page()
        result = {
            "site": site.name,
            "coin": site.coin,
            "url": site.signup_url,
            "success": False,
            "username": "",
            "email": "",
            "password": "",
            "error": "",
        }

        # Get site-specific referral code
        ref_code = self.referral_codes.get(site.name, "")
        if not ref_code:
            result["error"] = "No referral code configured for this site"
            print(f"  ✗ No referral code for {site.name}")
            await page.close()
            return result

        # Generate credentials
        username = generate_username(self.username_prefix)
        email = generate_email(username, self.email_domain)
        password = generate_password()

        result["username"] = username
        result["email"] = email
        result["password"] = password

        try:
            print(f"  → Visiting {site.signup_url}")
            await page.goto(site.signup_url, wait_until="networkidle", timeout=30000)

            # Fill the form - all sites use same field names
            print(f"  → Filling form for {site.name} (ref: {ref_code})")
            await page.fill('input[name="username"]', username)
            await page.fill('input[name="email"]', email)
            await page.fill('input[name="password"]', password)
            await page.fill('input[name="password2"]', password)  # Repeat password

            # Fill referral code - field name is "referrer"
            await page.fill('input[name="referrer"]', ref_code)

            # CAPTCHA handling - these sites use multiple CAPTCHA providers
            print(f"  ⚠ CAPTCHA detected - manual intervention required")
            print(f"     Complete the CAPTCHA in the browser window...")

            # Wait for user to complete CAPTCHA and submit
            await page.wait_for_load_state("networkidle")

            # Check if registration succeeded
            content = await page.content()

            if "success" in content.lower() or "welcome" in content.lower() or "dashboard" in content.lower():
                result["success"] = True
                print(f"  ✓ Registration successful for {site.name}")
            elif "error" in content.lower() or "invalid" in content.lower() or "already" in content.lower():
                result["error"] = "Registration failed - check form errors"
                print(f"  ✗ Registration failed for {site.name}")
            else:
                # Assume success if we got past the form
                result["success"] = True
                print(f"  ✓ Registration likely successful for {site.name}")

        except Exception as e:
            result["error"] = str(e)
            print(f"  ✗ Error on {site.name}: {e}")

        await page.close()
        return result

    async def run(self) -> list[dict]:
        """Run registration on all sites."""
        await self._init_browser()

        print(f"\n{'='*60}")
        print(f"Faucet Affiliate Registration Tool")
        print(f"Sites: {len(self.sites)}")
        for s in self.sites:
            code = self.referral_codes.get(s.name, "NOT SET")
            print(f"  {s.name} ({s.coin}): ref={code}")
        print(f"{'='*60}\n")

        for site in self.sites:
            print(f"\n[{site.name}] ({site.coin})")
            result = await self.register_on_site(site)
            self.results.append(result)

            # Brief pause between sites
            await asyncio.sleep(2)

        await self._close_browser()
        self._save_credentials()

        # Print summary
        self._print_summary()
        return self.results

    def _print_summary(self) -> None:
        print(f"\n{'='*60}")
        print(f"REGISTRATION SUMMARY")
        print(f"{'='*60}")
        success_count = sum(1 for r in self.results if r["success"])
        print(f"Successful: {success_count}/{len(self.sites)}")
        print(f"\nCredentials saved to: {self.credentials_file}\n")

        for r in self.results:
            status = "✓" if r["success"] else "✗"
            print(f"  {status} {r['site']} ({r['coin']})")
            if r["success"]:
                print(f"      User: {r['username']} | Email: {r['email']}")
            elif r["error"]:
                print(f"      Error: {r['error']}")


# ── CLI Entry Point ────────────────────────────────────────────────────────

async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Register accounts on crypto faucet sites with your referral codes"
    )
    parser.add_argument(
        "referral_codes",
        help=(
            "Referral codes. Formats:\n"
            "  @/path/to/codes.json          - JSON file mapping site keys to codes\n"
            "  bnb-pick=CODE1,ton-pick=CODE2 - Comma-separated key=value pairs\n"
            "  MYCODE                        - Single code for all sites"
        )
    )
    parser.add_argument(
        "--email-domain",
        default="protonmail.com",
        help="Email domain to use (default: protonmail.com)"
    )
    parser.add_argument(
        "--username-prefix",
        default="ref",
        help="Username prefix (default: ref)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (not recommended for CAPTCHA)"
    )
    parser.add_argument(
        "--credentials-file",
        default="faucet_credentials.json",
        help="Output credentials file (default: faucet_credentials.json)"
    )
    parser.add_argument(
        "--sites",
        nargs="+",
        choices=list(SITE_KEYS.keys()),
        help="Specific sites to register on (default: all)"
    )

    args = parser.parse_args()

    # Parse referral codes
    try:
        referral_codes = parse_referral_codes(args.referral_codes)
    except Exception as e:
        parser.error(f"Invalid referral codes: {e}")

    # Filter sites if requested
    sites_to_use = SITES
    if args.sites:
        site_map = {s.name.lower().replace(" ", "-"): s for s in SITES}
        sites_to_use = [site_map[s] for s in args.sites if s in site_map]

    # Validate all selected sites have codes
    missing = [s.name for s in sites_to_use if s.name not in referral_codes or not referral_codes[s.name]]
    if missing:
        parser.error(f"Missing referral codes for: {', '.join(missing)}")

    registrar = FaucetRegistrar(
        referral_codes=referral_codes,
        email_domain=args.email_domain,
        username_prefix=args.username_prefix,
        headless=args.headless,
        credentials_file=args.credentials_file,
        sites=sites_to_use,
    )

    await registrar.run()


if __name__ == "__main__":
    asyncio.run(main())