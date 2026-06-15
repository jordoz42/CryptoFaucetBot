#!/usr/bin/env python3
"""
CAPTCHA Solver Abstraction Layer
Supports multiple providers: 2Captcha, Anti-Captcha, CapMonster, etc.
"""

import asyncio
import base64
import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from urllib.parse import urljoin

import httpx


class CaptchaType(Enum):
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    TURNSTILE = "turnstile"
    IMAGE_CAPTCHA = "image_captcha"  # IconCaptcha, pCaptcha, etc.


@dataclass
class CaptchaChallenge:
    """A CAPTCHA challenge to solve."""
    type: CaptchaType
    site_key: Optional[str] = None
    page_url: Optional[str] = None
    image_base64: Optional[str] = None  # For image-based CAPTCHAs
    extra_params: Optional[dict] = None


@dataclass
class CaptchaSolution:
    """Solution returned by solver."""
    token: str
    challenge_id: str
    cost: float = 0.0


class CaptchaSolver(ABC):
    """Base class for CAPTCHA solving services."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=120.0)
    
    @abstractmethod
    async def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """Solve a CAPTCHA challenge."""
        pass
    
    @abstractmethod
    async def report_good(self, challenge_id: str) -> None:
        """Report successful solve (for refunds)."""
        pass
    
    @abstractmethod
    async def report_bad(self, challenge_id: str) -> None:
        """Report failed solve (for refunds)."""
        pass
    
    async def close(self):
        await self.client.aclose()


class TwoCaptchaSolver(CaptchaSolver):
    """2Captcha.com solver - supports reCAPTCHA v2/v3, hCaptcha, Turnstile, image CAPTCHAs."""
    
    BASE_URL = "http://2captcha.com"
    
    async def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        if challenge.type == CaptchaType.RECAPTCHA_V2:
            return await self._solve_recaptcha_v2(challenge)
        elif challenge.type == CaptchaType.RECAPTCHA_V3:
            return await self._solve_recaptcha_v3(challenge)
        elif challenge.type == CaptchaType.HCAPTCHA:
            return await self._solve_hcaptcha(challenge)
        elif challenge.type == CaptchaType.TURNSTILE:
            return await self._solve_turnstile(challenge)
        elif challenge.type == CaptchaType.IMAGE_CAPTCHA:
            return await self._solve_image(challenge)
        else:
            raise ValueError(f"Unsupported CAPTCHA type: {challenge.type}")
    
    async def _submit_task(self, payload: dict) -> str:
        """Submit task, return task ID."""
        resp = await self.client.post(f"{self.BASE_URL}/in.php", data=payload)
        result = resp.text
        if not result.startswith("OK|"):
            raise Exception(f"2Captcha submit failed: {result}")
        return result.split("|")[1]
    
    async def _poll_result(self, task_id: str, max_wait: int = 180) -> str:
        """Poll for result, return token."""
        start = time.time()
        while time.time() - start < max_wait:
            await asyncio.sleep(5)
            resp = await self.client.get(
                f"{self.BASE_URL}/res.php",
                params={"key": self.api_key, "action": "get", "id": task_id}
            )
            result = resp.text
            if result == "CAPCHA_NOT_READY":
                continue
            if result.startswith("OK|"):
                return result.split("|")[1]
            if "ERROR" in result:
                raise Exception(f"2Captcha error: {result}")
            raise Exception(f"Unexpected result: {result}")
        raise TimeoutError("2Captcha solve timeout")
    
    async def _solve_recaptcha_v2(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        task_id = await self._submit_task({
            "key": self.api_key,
            "method": "userrecaptcha",
            "googlekey": challenge.site_key,
            "pageurl": challenge.page_url,
            "json": 1,
        })
        token = await self._poll_result(task_id)
        return CaptchaSolution(token=token, challenge_id=task_id, cost=0.001)
    
    async def _solve_recaptcha_v3(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        task_id = await self._submit_task({
            "key": self.api_key,
            "method": "userrecaptcha",
            "version": "v3",
            "googlekey": challenge.site_key,
            "pageurl": challenge.page_url,
            "score": challenge.extra_params.get("score", 0.3) if challenge.extra_params else 0.3,
            "json": 1,
        })
        token = await self._poll_result(task_id)
        return CaptchaSolution(token=token, challenge_id=task_id, cost=0.001)
    
    async def _solve_hcaptcha(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        task_id = await self._submit_task({
            "key": self.api_key,
            "method": "hcaptcha",
            "sitekey": challenge.site_key,
            "pageurl": challenge.page_url,
            "json": 1,
        })
        token = await self._poll_result(task_id)
        return CaptchaSolution(token=token, challenge_id=task_id, cost=0.001)
    
    async def _solve_turnstile(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        task_id = await self._submit_task({
            "key": self.api_key,
            "method": "turnstile",
            "sitekey": challenge.site_key,
            "pageurl": challenge.page_url,
            "json": 1,
        })
        token = await self._poll_result(task_id)
        return CaptchaSolution(token=token, challenge_id=task_id, cost=0.001)
    
    async def _solve_image(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        # For image CAPTCHAs (IconCaptcha, etc.)
        task_id = await self._submit_task({
            "key": self.api_key,
            "method": "base64",
            "body": challenge.image_base64,
            "json": 1,
        })
        token = await self._poll_result(task_id)
        return CaptchaSolution(token=token, challenge_id=task_id, cost=0.0005)
    
    async def report_good(self, challenge_id: str) -> None:
        await self.client.get(f"{self.BASE_URL}/res.php", params={
            "key": self.api_key, "action": "reportgood", "id": challenge_id
        })
    
    async def report_bad(self, challenge_id: str) -> None:
        await self.client.get(f"{self.BASE_URL}/res.php", params={
            "key": self.api_key, "action": "reportbad", "id": challenge_id
        })


class AntiCaptchaSolver(CaptchaSolver):
    """Anti-Captcha.com solver."""
    
    BASE_URL = "https://api.anti-captcha.com"
    
    async def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        if challenge.type == CaptchaType.RECAPTCHA_V2:
            return await self._solve_recaptcha_v2(challenge)
        elif challenge.type == CaptchaType.HCAPTCHA:
            return await self._solve_hcaptcha(challenge)
        elif challenge.type == CaptchaType.IMAGE_CAPTCHA:
            return await self._solve_image(challenge)
        else:
            raise ValueError(f"Unsupported CAPTCHA type: {challenge.type}")
    
    async def _create_task(self, task_data: dict) -> int:
        resp = await self.client.post(f"{self.BASE_URL}/createTask", json={
            "clientKey": self.api_key,
            "task": task_data,
        })
        result = resp.json()
        if result.get("errorId") != 0:
            raise Exception(f"Anti-Captcha create failed: {result.get('errorDescription')}")
        return result["taskId"]
    
    async def _wait_for_result(self, task_id: int, max_wait: int = 180) -> dict:
        start = time.time()
        while time.time() - start < max_wait:
            await asyncio.sleep(3)
            resp = await self.client.post(f"{self.BASE_URL}/getTaskResult", json={
                "clientKey": self.api_key, "taskId": task_id
            })
            result = resp.json()
            if result.get("errorId") != 0:
                raise Exception(f"Anti-Captcha error: {result.get('errorDescription')}")
            if result.get("status") == "ready":
                return result["solution"]
        raise TimeoutError("Anti-Captcha solve timeout")
    
    async def _solve_recaptcha_v2(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        task_id = await self._create_task({
            "type": "NoCaptchaTaskProxyless",
            "websiteURL": challenge.page_url,
            "websiteKey": challenge.site_key,
        })
        solution = await self._wait_for_result(task_id)
        return CaptchaSolution(
            token=solution["gRecaptchaResponse"],
            challenge_id=str(task_id),
            cost=0.001
        )
    
    async def _solve_hcaptcha(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        task_id = await self._create_task({
            "type": "HCaptchaTaskProxyless",
            "websiteURL": challenge.page_url,
            "websiteKey": challenge.site_key,
        })
        solution = await self._wait_for_result(task_id)
        return CaptchaSolution(
            token=solution["gRecaptchaResponse"],
            challenge_id=str(task_id),
            cost=0.001
        )
    
    async def _solve_image(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        task_id = await self._create_task({
            "type": "ImageToTextTask",
            "body": challenge.image_base64,
        })
        solution = await self._wait_for_result(task_id)
        return CaptchaSolution(
            token=solution["text"],
            challenge_id=str(task_id),
            cost=0.0005
        )
    
    async def report_good(self, challenge_id: str) -> None:
        pass  # Anti-Captcha doesn't have report good
    
    async def report_bad(self, challenge_id: str) -> None:
        await self.client.post(f"{self.BASE_URL}/reportIncorrectTaskResult", json={
            "clientKey": self.api_key, "taskId": int(challenge_id)
        })


class CapMonsterSolver(CaptchaSolver):
    """CapMonster.cloud solver - same API as Anti-Captcha."""
    
    BASE_URL = "https://api.capmonster.cloud"
    
    # Inherits same methods as AntiCaptchaSolver
    async def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        solver = AntiCaptchaSolver(self.api_key)
        solver.client = self.client
        solver.BASE_URL = self.BASE_URL
        return await solver.solve(challenge)
    
    async def report_good(self, challenge_id: str) -> None:
        pass
    
    async def report_bad(self, challenge_id: str) -> None:
        pass


# Factory
def create_solver(provider: str, api_key: str) -> CaptchaSolver:
    """Create solver instance by provider name."""
    providers = {
        "2captcha": TwoCaptchaSolver,
        "anticaptcha": AntiCaptchaSolver,
        "capmonster": CapMonsterSolver,
    }
    provider = provider.lower()
    if provider not in providers:
        raise ValueError(f"Unknown provider: {provider}. Options: {list(providers.keys())}")
    return providers[provider](api_key)


# Auto-detect CAPTCHA type from page
async def detect_captcha_type(page) -> Optional[CaptchaChallenge]:
    """Detect CAPTCHA on page and return challenge."""
    
    # Check for reCAPTCHA v2
    recaptcha = await page.query_selector('iframe[src*="recaptcha"]')
    if recaptcha:
        src = await recaptcha.get_attribute("src")
        # Extract site key from URL
        import re
        match = re.search(r'k=([^&]+)', src)
        if match:
            return CaptchaChallenge(
                type=CaptchaType.RECAPTCHA_V2,
                site_key=match.group(1),
                page_url=page.url,
            )
    
    # Check for hCaptcha
    hcaptcha = await page.query_selector('iframe[src*="hcaptcha"]')
    if hcaptcha:
        src = await hcaptcha.get_attribute("src")
        import re
        match = re.search(r'sitekey=([^&]+)', src)
        if match:
            return CaptchaChallenge(
                type=CaptchaType.HCAPTCHA,
                site_key=match.group(1),
                page_url=page.url,
            )
    
    # Check for Turnstile
    turnstile = await page.query_selector('iframe[src*="turnstile"]')
    if turnstile:
        src = await turnstile.get_attribute("src")
        import re
        match = re.search(r'sitekey=([^&]+)', src)
        if match:
            return CaptchaChallenge(
                type=CaptchaType.TURNSTILE,
                site_key=match.group(1),
                page_url=page.url,
            )
    
    # Check for IconCaptcha / image CAPTCHA (look for CAPTCHA image)
    captcha_img = await page.query_selector('img[src*="captcha"], img[id*="captcha"], img[class*="captcha"]')
    if captcha_img:
        # Screenshot the CAPTCHA area
        img_bytes = await captcha_img.screenshot()
        img_b64 = base64.b64encode(img_bytes).decode()
        return CaptchaChallenge(
            type=CaptchaType.IMAGE_CAPTCHA,
            image_base64=img_b64,
            page_url=page.url,
        )
    
    return None


# Inject solution into page
async def inject_recaptcha_solution(page, token: str) -> None:
    """Inject reCAPTCHA/hCaptcha/Turnstile solution."""
    await page.evaluate(f"""
        document.getElementById('g-recaptcha-response').innerHTML = '{token}';
        document.getElementById('g-recaptcha-response').style.display = 'block';
        if (typeof ___grecaptcha_cfg !== 'undefined') {{
            Object.entries(___grecaptcha_cfg.clients).forEach(([key, client]) => {{
                if (client.callback) client.callback('{token}');
            }});
        }}
        if (typeof hcaptcha !== 'undefined') {{
            hcaptcha.getResponse = () => '{token}';
        }}
        if (typeof turnstile !== 'undefined') {{
            // Turnstile uses callback
        }}
    """)


async def inject_image_captcha_solution(page, token: str) -> None:
    """Fill image CAPTCHA input."""
    # Try common input selectors
    selectors = [
        'input[name="captcha"]',
        'input[name="captcha_code"]',
        'input[id*="captcha"]',
        'input[class*="captcha"]',
        '#captcha',
        '.captcha-input',
    ]
    for sel in selectors:
        try:
            await page.fill(sel, token)
            break
        except:
            continue