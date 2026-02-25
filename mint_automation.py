import os
import re
import requests
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
import telegram

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

print("Fetching Mint page...")

url = "https://www.tradingref.com/mint"
response = requests.get(url)
html = response.text

# Extract all S3 image URLs
pattern = r'https://ht-mint-epaper-fs\.s3\.ap-south-1\.amazonaws\.com[^"]+\.jpg'
image_urls = re.findall(pattern, html)

# Remove duplicates
image_urls = list(dict.fromkeys(image_urls))

if not image_urls:
    print("No images found.")
    exit()

print("Images found:", len(image_urls))

# Create PDF
pdf_filename = "mint.pdf"
doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
elements = []

for img_url in image_urls:
    r = requests.get(img_url)
    img_stream = BytesIO(r.content)
    img = Image(img_stream, width=6*inch, height=10*inch)
    elements.append(img)

doc.build(elements)

print("PDF created.")

# Send to Telegram
if TELEGRAM_TOKEN and CHAT_ID:
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    with open(pdf_filename, "rb") as f:
        bot.send_document(chat_id=CHAT_ID, document=f)
    print("Sent to Telegram.")
else:
    print("Telegram secrets missing.")
