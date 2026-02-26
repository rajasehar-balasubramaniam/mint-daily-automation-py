import asyncio
import os
import requests
from playwright.async_api import async_playwright

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def run():

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        print("Opening website...")
        await page.goto("https://www.tradingref.com/mint", timeout=60000)

        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(5000)

        print("Injecting internal generation script...")

        await page.evaluate("""
        async () => {
        
            const sleep = (ms) => new Promise(r => setTimeout(r, ms));
        
            const today = new Date().toISOString().split("T")[0];
            AppState.selectedDate = today;
        
            console.log("Loading editions...");
            await DataManager.loadEditions(today);
        
            // WAIT until editionsData is ready
            let retries = 0;
            while ((!DataManager.editionsData || 
                   !DataManager.editionsData["English"] ||
                   !DataManager.editionsData["English"]["Mint"] ||
                   !DataManager.editionsData["English"]["Mint"]["Bengaluru"]) 
                   && retries < 20) {
        
                await sleep(1000);
                retries++;
            }
        
            if (!DataManager.editionsData ||
                !DataManager.editionsData["English"] ||
                !DataManager.editionsData["English"]["Mint"] ||
                !DataManager.editionsData["English"]["Mint"]["Bengaluru"]) {
        
                throw new Error("Mint Bengaluru edition not available yet.");
            }
        
            AppState.selectedLanguage = "English";
            AppState.selectedNewspaper = "Mint";
            AppState.selectedEdition = "Bengaluru";
        
            console.log("Generating PDF...");
            await PDFManager.generate();
        }
        """)

        print("Waiting for download...")

        download = await page.wait_for_event("download", timeout=180000)

        path = await download.path()
        filename = download.suggested_filename

        print("Downloaded:", filename)

        send_to_telegram(path, filename)

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
