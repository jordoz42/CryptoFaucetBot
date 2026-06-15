#!/usr/bin/env python3
"""
Faucet Claimer Bot - Automated hourly claiming with session persistence.
Run once manually to login & save cookies, then cron runs headless using saved sessions.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class FaucetClaimer:
    def __init__(
        self,
        credentials_file: str = "faucet_credentials.json",
        sessions_dir: str = "sessions",
        headless: bool = True,
    ):
        self.credentials_file = Path(credentials_file)
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)
        self.headless = headless
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

    async def _save_session(self, site_name: str) -> None:
        """Save browser context cookies to file."""
        cookies = await self.context.cookies()
        self._session_file(site_name).write_text(json.dumps(cookies, indent=2))
        print(f"  💾 Saved session for {site_name}")

    async def _load_session(self, site_name: str) -> bool:
        """Load cookies from file into context."""
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

        # Try loading existing session first
        await self._load_session(site_name)
        page = await self.context.new_page()
        await page.goto(base_url, wait_until="networkidle", timeout=30000)

        # Check if already logged in
        content = await page.content()
        if "logout" in content.lower() or "dashboard" in content.lower():
            print(f"  ✓ Already logged in to {site_name} (session valid)")
            await page.close()
            return True

        # Need to login
        print(f"  → Logging into {site_name} (manual CAPTCHA required)")
        await page.goto(login_url, wait_until="networkidle", timeout=30000)

        await page.fill('input[name="username"]', account["username"])
        await page.fill('input[name="password"]', account["password"])

        print(f"  ⚠ Complete CAPTCHA and click Login in the browser...")
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

    async def claim_faucet(self, page: Page, site_name: str) -> bool:
        """Claim the hourly faucet reward."""
        base_url = self._get_base_url(site_name)

        try:
            print(f"  → Visiting faucet page for {site_name}")
            await page.goto(base_url, wait_until="networkidle", timeout=30000)

            # Check if still logged in
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
            ]

            claimed = False
            for selector in claim_selectors:
                try:
                    if await page.is_visible(selector, timeout=2000):
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
        """Run one claim cycle for all accounts (headless, uses saved sessions)."""
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
                
                # Try claim
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

        # Run non-headless for manual CAPTCHA
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

    parser = argparse.ArgumentParser(description="Auto-claim faucet rewards with session persistence")
    parser.add_argument("--credentials-file", default="faucet_credentials.json")
    parser.add_argument("--sessions-dir", default="sessions")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--setup", action="store_true", help="Interactive login to save sessions (run once)")
    parser.add_argument("--daemon", action="store_true", help="Run continuously every hour")
    args = parser.parse_args()

    claimer = FaucetClaimer(
        credentials_file=args.credentials_file,
        sessions_dir=args.sessions_dir,
        headless=args.headless,
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
    asyncio.run(main())