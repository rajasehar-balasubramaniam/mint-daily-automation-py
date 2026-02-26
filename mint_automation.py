import asyncio
import os
import requests
from playwright.async_api import async_playwright

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


async def run():

    async with async_playwright() as p:

        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        print("Opening website...")

        await page.goto(
            "https://www.tradingref.com/mint",
            wait_until="domcontentloaded",
            timeout=60000
        )

        # Wait until internal JS objects exist
        await page.wait_for_function(
            "typeof AppState !== 'undefined' && typeof PDFManager !== 'undefined'",
            timeout=30000
        )

        await page.wait_for_timeout(3000)

        print("Website ready. Injecting generation script...")

        # Inject controlled generation logic
        await page.evaluate("""
        async () => {

            const sleep = (ms) => new Promise(r => setTimeout(r, ms));

            const today = new Date().toISOString().split("T")[0];
            AppState.selectedDate = today;

            console.log("Loading editions...");
            await DataManager.loadEditions(today);

            // Wait until Mint Bengaluru exists
            let retries = 0;
            while ((!DataManager.editionsData ||
                   !DataManager.editionsData["English"] ||
                   !DataManager.editionsData["English"]["Mint"] ||
                   !DataManager.editionsData["English"]["Mint"]["Bengaluru"])
                   && retries < 25) {

                await sleep(1000);
                retries++;
            }

            if (!DataManager.editionsData ||
                !DataManager.editionsData["English"] ||
                !DataManager.editionsData["English"]["Mint"] ||
                !DataManager.editionsData["English"]["Mint"]["Bengaluru"]) {

                throw new Error("Mint Bengaluru edition not available.");
            }

            AppState.selectedLanguage = "English";
            AppState.selectedNewspaper = "Mint";
            AppState.selectedEdition = "Bengaluru";

            console.log("Generating PDF...");
            await PDFManager.generate();
        }
        """)

        print("Waiting for download event...")

        download = await page.wait_for_event("download", timeout=300000)

        path = await download.path()
        filename = download.suggested_filename

        print("Download completed:", filename)

        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            send_to_telegram(path, filename)
        else:
            print("Telegram credentials missing. Skipping send.")

        await browser.close()


def send_to_telegram(file_path, filename):

    print("Sending to Telegram...")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"

    with open(file_path, "rb") as f:
        response = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID},
            files={"document": (filename, f)}
        )

    print("Telegram response:", response.text)


if __name__ == "__main__":
    asyncio.run(run())
