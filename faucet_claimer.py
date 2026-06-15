#!/usr/bin/env python3
"""
Faucet Claimer Bot - Automated hourly claiming for registered accounts.
Run as a cron job or background service to claim faucet rewards automatically.
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
        headless: bool = True,
    ):
        self.credentials_file = Path(credentials_file)
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

    async def _init_browser(self) -> None:
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

    async def _close_browser(self) -> None:
        if self.browser:
            await self.browser.close()

    async def login(self, page: Page, site_name: str, account: dict) -> bool:
        """Log into a faucet site."""
        base_url = self._get_base_url(site_name)
        login_url = f"{base_url}/login.php"

        try:
            print(f"  → Logging into {site_name}")
            await page.goto(login_url, wait_until="networkidle", timeout=30000)

            # Fill login form
            await page.fill('input[name="username"]', account["username"])
            await page.fill('input[name="password"]', account["password"])

            # Handle CAPTCHA if present
            print(f"  ⚠ CAPTCHA may be required - manual intervention needed")
            await page.wait_for_load_state("networkidle")

            # Check if logged in
            content = await page.content()
            if "logout" in content.lower() or "dashboard" in content.lower() or "faucet" in content.lower():
                print(f"  ✓ Logged into {site_name}")
                return True
            else:
                print(f"  ✗ Login failed for {site_name}")
                return False

        except Exception as e:
            print(f"  ✗ Login error for {site_name}: {e}")
            return False

    async def claim_faucet(self, page: Page, site_name: str) -> bool:
        """Claim the hourly faucet reward."""
        base_url = self._get_base_url(site_name)
        faucet_url = base_url  # Main page usually has the faucet

        try:
            print(f"  → Visiting faucet page for {site_name}")
            await page.goto(faucet_url, wait_until="networkidle", timeout=30000)

            # Look for claim button - typically "Claim" or "Roll" button
            claim_selectors = [
                'button:has-text("Claim")',
                'input[value="Claim"]',
                'a:has-text("Claim")',
                'button:has-text("Roll")',
                'input[value="Roll"]',
                '.claim-button',
                '#claim-button',
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
                # Could check for countdown timer here
                content = await page.content()
                if "wait" in content.lower() or "timer" in content.lower() or "next claim" in content.lower():
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

    async def run_once(self) -> dict:
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
                logged_in = await self.login(page, site_name, account)
                if logged_in:
                    claimed = await self.claim_faucet(page, site_name)
                    results[site_name] = {"logged_in": True, "claimed": claimed}
                else:
                    results[site_name] = {"logged_in": False, "claimed": False}
            finally:
                await page.close()

        await self._close_browser()
        return results


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Auto-claim faucet rewards for registered accounts")
    parser.add_argument("--credentials-file", default="faucet_credentials.json")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--daemon", action="store_true", help="Run continuously every hour")
    args = parser.parse_args()

    claimer = FaucetClaimer(
        credentials_file=args.credentials_file,
        headless=args.headless,
    )

    if args.daemon:
        print("Starting daemon mode - claiming every hour...")
        while True:
            print(f"\n{'='*60}")
            print(f"CLAIM CYCLE START")
            print(f"{'='*60}")
            results = await claimer.run_once()
            print(f"\nCycle complete. Waiting 1 hour...")
            await asyncio.sleep(3600)
    else:
        await claimer.run_once()


if __name__ == "__main__":
    asyncio.run(main())