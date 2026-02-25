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
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import telegram

# ===== TELEGRAM SECRETS =====
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ===== CHROME OPTIONS =====
chrome_options = Options()
chrome_options.binary_location = "/usr/bin/chromium-browser"
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Auto-manage correct chromedriver version
service = Service(ChromeDriverManager().install())

driver = webdriver.Chrome(service=service, options=chrome_options)

print("Opening tradingref.com")
driver.get("https://www.tradingref.com/")

time.sleep(5)

print("Clicking Generate button")
button = driver.find_element(By.XPATH, "//button[contains(text(),'Generate & Download PDF')]")
button.click()

# Wait for images to load
time.sleep(25)

print("Extracting image URLs")
imgs = driver.find_elements(By.TAG_NAME, "img")

image_urls = []
for img in imgs:
    src = img.get_attribute("src")
    if src and "ht-mint-epaper-fs.s3" in src:
        image_urls.append(src)

driver.quit()

# Remove duplicates
image_urls = list(dict.fromkeys(image_urls))

if not image_urls:
    print("No images found.")
    exit()

print("Images found:", len(image_urls))

# ===== CREATE PDF =====
pdf_filename = "mint.pdf"
doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
elements = []

for url in image_urls:
    r = requests.get(url)
    img_stream = BytesIO(r.content)
    img = Image(img_stream, width=6*inch, height=10*inch)
    elements.append(img)

doc.build(elements)

print("PDF created.")

# ===== SEND TO TELEGRAM =====
if TELEGRAM_TOKEN and CHAT_ID:
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    with open(pdf_filename, "rb") as f:
        bot.send_document(chat_id=CHAT_ID, document=f)
    print("Sent to Telegram.")
else:
    print("Telegram secrets missing.")
