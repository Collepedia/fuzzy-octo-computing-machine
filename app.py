import asyncio
from playwright.async_api import async_playwright
import random
import os
from urllib.parse import urlparse, urljoin
from stem import Signal
from stem.control import Controller

URL_TO_VISIT = os.environ.get("TARGET_URL", "https://colle-pedia.blogspot.com/")
RUNNER_ID = os.environ.get("RUNNER_ID", "1")
TOR_SOCKS5 = os.environ.get("PROXY_URL", "socks5://127.0.0.1:9050")

async def signal_newnym():
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
            print(f"[Runner {RUNNER_ID}] Tor NEWNYM signal sent successfully.")
        await asyncio.sleep(5)
    except Exception as e:
        print(f"[Runner {RUNNER_ID}] Tor NEWNYM error: {e}")

async def visit_with_browser():
    base_netloc = urlparse(URL_TO_VISIT).netloc
    proxy_config = {"server": TOR_SOCKS5}

    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(
                headless=True,
                proxy=proxy_config,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            context = await browser.new_context(
                user_agent=f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.{random.randint(0,9999)} Safari/537.36"
            )
            page = await context.new_page()

            print(f"[Runner {RUNNER_ID}] Visiting main page: {URL_TO_VISIT}")
            await page.goto(URL_TO_VISIT, wait_until="domcontentloaded", timeout=60000)

            await page.wait_for_selector('a[href*=".html"]', timeout=20000)
            link_locators = page.locator('a[href*=".html"]')
            all_links = await link_locators.all()
            internal_links = [
                urljoin(URL_TO_VISIT, await link.get_attribute('href'))
                for link in all_links
                if await link.get_attribute('href') and urlparse(urljoin(URL_TO_VISIT, await link.get_attribute('href'))).netloc == base_netloc
            ]

            if not internal_links:
                print(f"[Runner {RUNNER_ID}] No valid internal links, closing browser.")
                await browser.close()
                return

            pages_to_visit = random.sample(internal_links, min(3, len(internal_links)))
            for link in pages_to_visit:
                print(f"[Runner {RUNNER_ID}] Visiting: {link}")
                await page.goto(link, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(random.uniform(1,3))

            print(f"[Runner {RUNNER_ID}] Done visiting 3 pages. Closing browser to change IP...")
            await browser.close()
        except Exception as e:
            print(f"[Runner {RUNNER_ID}] Error: {e}")
            if browser:
                await browser.close()

async def main():
    while True:
        await visit_with_browser()
        await signal_newnym()

if __name__ == "__main__":
    asyncio.run(main())
              
