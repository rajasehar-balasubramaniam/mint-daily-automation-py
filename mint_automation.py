import asyncio
import os
import requests
from playwright.async_api import async_playwright

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def run():
    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        context = await browser.new_context(
            accept_downloads=True
        )

        page = await context.new_page()

        print("Opening website...")
        await page.goto("https://www.tradingref.com/", timeout=60000)

        # Wait until core app is ready
        await page.wait_for_function(
            "() => window.DataManager && window.PDFManager && window.AppState",
            timeout=60000
        )

        print("Injecting internal generation script...")

        await page.evaluate("""
        async () => {

            const sleep = (ms) => new Promise(r => setTimeout(r, ms));

            function formatDate(d) {
                return d.toISOString().split("T")[0];
            }

            async function tryDate(dateStr) {

                AppState.selectedDate = dateStr;
                await DataManager.loadEditions(dateStr);

                let retries = 0;
                while (!DataManager.editionsData && retries < 15) {
                    await sleep(1000);
                    retries++;
                }

                if (!DataManager.editionsData) return false;

                if (
                    DataManager.editionsData["English"] &&
                    DataManager.editionsData["English"]["Mint"] &&
                    DataManager.editionsData["English"]["Mint"]["Bengaluru"]
                ) {
                    return true;
                }

                return false;
            }

            const today = new Date();
            const yesterday = new Date();
            yesterday.setDate(today.getDate() - 1);

            let finalDate = formatDate(today);

            console.log("Trying today:", finalDate);
            let available = await tryDate(finalDate);

            if (!available) {
                finalDate = formatDate(yesterday);
                console.log("Today unavailable. Trying yesterday:", finalDate);
                available = await tryDate(finalDate);
            }

            if (!available) {
                throw new Error("Mint Bengaluru not available for today or yesterday.");
            }

            AppState.selectedLanguage = "English";
            AppState.selectedNewspaper = "Mint";
            AppState.selectedEdition = "Bengaluru";

            console.log("Generating PDF for", finalDate);
            await PDFManager.generate();
        }
        """)

        print("Waiting for download...")

        download = await page.wait_for_event("download", timeout=120000)

        file_path = os.path.join(DOWNLOAD_DIR, download.suggested_filename)
        await download.save_as(file_path)

        print("Downloaded:", file_path)

        await browser.close()

        # Send to Telegram
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            print("Sending to Telegram...")
            send_to_telegram(file_path)
        else:
            print("Telegram credentials not configured.")


def send_to_telegram(file_path):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"

    with open(file_path, "rb") as f:
        response = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID},
            files={"document": f},
        )

    if response.status_code == 200:
        print("Telegram sent successfully.")
    else:
        print("Telegram failed:", response.text)


if __name__ == "__main__":
    asyncio.run(run())
