import os
import time
import requests
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import telegram

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Chrome setup
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# DO NOT set chromedriver path manually
driver = webdriver.Chrome(options=chrome_options)

print("Opening tradingref.com")
driver.get("https://www.tradingref.com/")
time.sleep(5)

print("Clicking Generate button")
button = driver.find_element(By.XPATH, "//button[contains(text(),'Generate')]")
button.click()

time.sleep(25)

print("Extracting image URLs")
imgs = driver.find_elements(By.TAG_NAME, "img")
image_urls = []

for img in imgs:
    src = img.get_attribute("src")
    if src and "ht-mint-epaper-fs.s3" in src:
        image_urls.append(src)

driver.quit()

image_urls = list(dict.fromkeys(image_urls))

if not image_urls:
    print("No images found.")
    exit()

print("Images found:", len(image_urls))

pdf_filename = "mint.pdf"
doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
elements = []

for url in image_urls:
    r = requests.get(url)
    image_stream = BytesIO(r.content)
    img = Image(image_stream, width=6*inch, height=10*inch)
    elements.append(img)

doc.build(elements)

print("PDF created.")

if TELEGRAM_TOKEN and CHAT_ID:
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    with open(pdf_filename, "rb") as f:
        bot.send_document(chat_id=CHAT_ID, document=f)
    print("Sent to Telegram.")
else:
    print("Telegram secrets missing.")
