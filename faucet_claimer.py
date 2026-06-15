#!/usr/bin/env python3
"""
Faucet Claimer Bot - Automated hourly claiming with CAPTCHA solving.
Run with CAPTCHA solver API key for fully automated operation.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# Import CAPTCHA solver
sys.path.insert(0, str(Path(__file__).parent))
from captcha_solver import (
    CaptchaChallenge, CaptchaType, create_solver, detect_captcha_type,
    inject_recaptcha_solution, inject_image_captcha_solution
)


class FaucetClaimer:
    def __init__(
        self,
        credentials_file: str = "faucet_credentials.json",
        sessions_dir: str = "sessions",
        headless: bool = True,
        captcha_solver: Optional[object] = None,  # CaptchaSolver instance
    ):
        self.credentials_file = Path(credentials_file)
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)
        self.headless = headless
        self.captcha_solver = captcha_solver
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.accounts = self._load_accounts()

    def _load_accounts(self) -> dict:
        if self.credentials_file.exists():
            try:
                return json.loads(self.credentials_file.read_text())
            except Exception:
                return {}
        return {}

    def _session_file(self, site_name: str) -> Path:
        safe_name = site_name.lower().replace(" ", "_")
        return self.sessions_dir / f"{safe_name}_session.json"

    async def _init_browser(self) -> None:
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

    async def _close_browser(self) -> None:
        if self.browser:
            await self.browser.close()
        if self.captcha_solver:
            await self.captcha_solver.close()

    async def _save_session(self, site_name: str) -> None:
        cookies = await self.context.cookies()
        self._session_file(site_name).write_text(json.dumps(cookies, indent=2))
        print(f"  💾 Saved session for {site_name}")

    async def _load_session(self, site_name: str) -> bool:
        session_file = self._session_file(site_name)
        if not session_file.exists():
            return False
        cookies = json.loads(session_file.read_text())
        await self.context.add_cookies(cookies)
        print(f"  ♻️  Loaded session for {site_name}")
        return True

    async def login_and_save_session(self, site_name: str, account: dict) -> bool:
        """Manual login flow - run once per site to establish session."""
        base_url = self._get_base_url(site_name)
        login_url = f"{base_url}/login.php"

        await self._load_session(site_name)
        page = await self.context.new_page()
        await page.goto(base_url, wait_until="networkidle", timeout=30000)

        # Check if already logged in
        content = await page.content()
        if "logout" in content.lower() or "dashboard" in content.lower():
            print(f"  ✓ Already logged in to {site_name} (session valid)")
            await page.close()
            return True

        # Need to login - may have CAPTCHA
        print(f"  → Logging into {site_name}")
        await page.goto(login_url, wait_until="networkidle", timeout=30000)

        await page.fill('input[name="username"]', account["username"])
        await page.fill('input[name="password"]', account["password"])

        # Handle CAPTCHA on login if solver available
        if self.captcha_solver:
            await self._handle_captcha(page, "login")
        else:
            print(f"  ⚠ Manual CAPTCHA required - complete in browser...")
            await page.wait_for_load_state("networkidle", timeout=60000)

        # Verify login
        content = await page.content()
        if "logout" in content.lower() or "dashboard" in content.lower() or "faucet" in content.lower():
            await self._save_session(site_name)
            print(f"  ✓ Logged in & session saved for {site_name}")
            await page.close()
            return True
        else:
            print(f"  ✗ Login failed for {site_name}")
            await page.close()
            return False

    async def _handle_captcha(self, page: Page, context: str) -> bool:
        """Detect and solve CAPTCHA on current page."""
        if not self.captcha_solver:
            return False
        
        try:
            challenge = await detect_captcha_type(page)
            if not challenge:
                print(f"  ℹ No CAPTCHA detected")
                return True
            
            print(f"  🔍 Detected {challenge.type.value} CAPTCHA, solving...")
            solution = await self.captcha_solver.solve(challenge)
            print(f"  ✓ CAPTCHA solved (cost: ${solution.cost:.4f})")
            
            # Inject solution based on type
            if challenge.type in (CaptchaType.RECAPTCHA_V2, CaptchaType.RECAPTCHA_V3, 
                                   CaptchaType.HCAPTCHA, CaptchaType.TURNSTILE):
                await inject_recaptcha_solution(page, solution.token)
            elif challenge.type == CaptchaType.IMAGE_CAPTCHA:
                await inject_image_captcha_solution(page, solution.token)
            
            # Small wait for injection to take effect
            await asyncio.sleep(1)
            return True
            
        except Exception as e:
            print(f"  ✗ CAPTCHA solve failed: {e}")
            return False

    async def claim_faucet(self, page: Page, site_name: str) -> bool:
        """Claim the hourly faucet reward - handles CAPTCHA on claim."""
        base_url = self._get_base_url(site_name)

        try:
            print(f"  → Visiting faucet page for {site_name}")
            await page.goto(base_url, wait_until="networkidle", timeout=30000)

            # Check if logged in
            content = await page.content()
            if "login" in content.lower() and "logout" not in content.lower():
                print(f"  ⚠ Session expired for {site_name}")
                return False

            # Look for claim button
            claim_selectors = [
                'button:has-text("Claim")',
                'input[value="Claim"]',
                'a:has-text("Claim")',
                'button:has-text("Roll")',
                'input[value="Roll"]',
                '.claim-button',
                '#claim-button',
                'button:has-text("Get")',
                'input[value="Get"]',
                'button:has-text("FREE")',
            ]

            claimed = False
            for selector in claim_selectors:
                try:
                    if await page.is_visible(selector, timeout=2000):
                        print(f"  → Clicking claim button: {selector}")
                        await page.click(selector)
                        await page.wait_for_load_state("networkidle", timeout=10000)
                        
                        # Check if CAPTCHA appeared after click
                        if self.captcha_solver:
                            await self._handle_captcha(page, "claim")
                            # May need to click again after CAPTCHA
                            await page.click(selector)
                            await page.wait_for_load_state("networkidle", timeout=10000)
                        
                        print(f"  ✓ Claimed faucet on {site_name}")
                        claimed = True
                        break
                except Exception:
                    continue

            if not claimed:
                print(f"  ⚠ Could not find claim button on {site_name}")
                content = await page.content()
                if any(kw in content.lower() for kw in ["wait", "timer", "next claim", "cooldown", "hour"]):
                    print(f"  ⏳ Faucet on cooldown for {site_name}")

            return claimed

        except Exception as e:
            print(f"  ✗ Claim error for {site_name}: {e}")
            return False

    def _get_base_url(self, site_name: str) -> str:
        url_map = {
            "BNB Pick": "https://bnbpick.io",
            "LTC Pick": "https://litepick.io",
            "TRX Pick": "https://tronpick.io",
            "DOGE Pick": "https://dogepick.io",
            "SUI Pick": "https://suipick.io",
            "POL Pick": "https://polpick.io",
            "TON Pick": "https://tonpick.game",
            "BCH Pick": "https://bchpick.io",
            "SOL Pick": "https://solpick.io",
        }
        return url_map.get(site_name, "")

    async def run_claim_cycle(self) -> dict:
        """Run one claim cycle for all accounts."""
        if not self.accounts:
            print("No accounts found. Run registrar first.")
            return {}

        await self._init_browser()
        results = {}

        for site_name, account in self.accounts.items():
            print(f"\n[{site_name}] ({account.get('coin', '?')})")
            page = await self.context.new_page()

            try:
                # Load session
                await self._load_session(site_name)
                
                # Try claim (will handle CAPTCHA if solver configured)
                claimed = await self.claim_faucet(page, site_name)
                results[site_name] = {"claimed": claimed}
                
            finally:
                await page.close()

        await self._close_browser()
        return results

    async def setup_sessions(self) -> dict:
        """Interactive setup: login to each site manually, save sessions."""
        if not self.accounts:
            print("No accounts found. Run registrar first.")
            return {}

        self.headless = False
        await self._init_browser()
        results = {}

        print(f"\n{'='*60}")
        print(f"SESSION SETUP - Login to each site manually")
        print(f"{'='*60}\n")

        for site_name, account in self.accounts.items():
            print(f"\n[{site_name}] ({account.get('coin', '?')})")
            success = await self.login_and_save_session(site_name, account)
            results[site_name] = {"session_saved": success}

        await self._close_browser()
        return results


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Auto-claim faucet rewards with CAPTCHA solving")
    parser.add_argument("--credentials-file", default="faucet_credentials.json")
    parser.add_argument("--sessions-dir", default="sessions")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--setup", action="store_true", help="Interactive login to save sessions (run once)")
    parser.add_argument("--daemon", action="store_true", help="Run continuously every hour")
    
    # CAPTCHA solver options
    parser.add_argument("--captcha-provider", choices=["2captcha", "anticaptcha", "capmonster"],
                       help="CAPTCHA solving service to use")
    parser.add_argument("--captcha-api-key", help="API key for CAPTCHA solver")
    parser.add_argument("--captcha-env-var", default="CAPTCHA_API_KEY",
                       help="Environment variable name for API key")
    
    args = parser.parse_args()

    # Initialize CAPTCHA solver if provider specified
    captcha_solver = None
    if args.captcha_provider:
        api_key = args.captcha_api_key or os.environ.get(args.captcha_env_var)
        if not api_key:
            parser.error(f"CAPTCHA API key required. Use --captcha-api-key or set {args.captcha_env_var}")
        captcha_solver = create_solver(args.captcha_provider, api_key)
        print(f"🔐 CAPTCHA solver initialized: {args.captcha_provider}")

    claimer = FaucetClaimer(
        credentials_file=args.credentials_file,
        sessions_dir=args.sessions_dir,
        headless=args.headless,
        captcha_solver=captcha_solver,
    )

    if args.setup:
        await claimer.setup_sessions()
    elif args.daemon:
        print("Starting daemon mode - claiming every hour...")
        while True:
            print(f"\n{'='*60}")
            print(f"CLAIM CYCLE START")
            print(f"{'='*60}")
            results = await claimer.run_claim_cycle()
            print(f"\nCycle complete. Waiting 1 hour...")
            await asyncio.sleep(3600)
    else:
        await claimer.run_claim_cycle()


if __name__ == "__main__":
    import os
    asyncio.run(main())