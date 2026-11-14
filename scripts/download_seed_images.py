import os
import urllib.request
from PIL import Image, ImageDraw, ImageFont

TARGET_DIR = r"F:\CLFP\app\static\uploads\seed"
os.makedirs(TARGET_DIR, exist_ok=True)

IMAGES = {
    "wallet.jpg": [
        "https://images.unsplash.com/photo-1627123424574-724758594e93?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1606503825008-909a67e766e4?w=600&auto=format&fit=crop&q=80"
    ],
    "iphone.jpg": [
        "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&auto=format&fit=crop&q=80"
    ],
    "macbook.jpg": [
        "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?w=600&auto=format&fit=crop&q=80"
    ],
    "calculus.jpg": [
        "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1532012164546-f432f2e3777f?w=600&auto=format&fit=crop&q=80"
    ],
    "hydroflask.jpg": [
        "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1544816155-12df9643f363?w=600&auto=format&fit=crop&q=80"
    ],
    "idcard.jpg": [
        "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1589330694653-ded6df03f754?w=600&auto=format&fit=crop&q=80"
    ],
    "headphones.jpg": [
        "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=600&auto=format&fit=crop&q=80"
    ],
    "carkey.jpg": [
        "https://images.unsplash.com/photo-1582139329536-e7284fece509?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1616788494707-ec28f08d05a1?w=600&auto=format&fit=crop&q=80"
    ],
    "watch.jpg": [
        "https://images.unsplash.com/photo-1524805444758-089113d48a6d?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=600&auto=format&fit=crop&q=80"
    ],
    "jacket.jpg": [
        "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1544441893-675973e31985?w=600&auto=format&fit=crop&q=80"
    ],
    "calculator.jpg": [
        "https://images.unsplash.com/photo-1587145820266-a5951ee6f620?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1611125832047-1d7ad1e8e48f?w=600&auto=format&fit=crop&q=80"
    ],
    "backpack.jpg": [
        "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1622560480605-d83c853bc5c3?w=600&auto=format&fit=crop&q=80"
    ],
    "bracelet.jpg": [
        "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=600&auto=format&fit=crop&q=80"
    ],
    "basketball.jpg": [
        "https://images.unsplash.com/photo-1519766304817-4f37bda74a29?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=600&auto=format&fit=crop&q=80"
    ],
    "powerbank.jpg": [
        "https://images.unsplash.com/photo-1622445262464-84b1456045b6?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop&q=80"
    ]
}

def create_fallback_image(filename, label):
    img = Image.new('RGB', (600, 450), color='#E8DDD1')
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 580, 430], outline='#4F7C72', width=4)
    draw.text((300, 225), label, fill='#243B53', anchor="mm")
    out_path = os.path.join(TARGET_DIR, filename)
    img.save(out_path, format="JPEG", quality=85)
    print(f"Fallback created: {filename}")

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

for fname, urls in IMAGES.items():
    dest = os.path.join(TARGET_DIR, fname)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        print(f"Already exists: {fname} ({os.path.getsize(dest)} bytes)")
        continue
    success = False
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp, open(dest, 'wb') as out:
                out.write(resp.read())
            # Verify image is valid
            with Image.open(dest) as img:
                img.verify()
            print(f"Successfully downloaded: {fname} from {url[:45]}...")
            success = True
            break
        except Exception as e:
            print(f"Failed {url[:40]} for {fname}: {e}")
            if os.path.exists(dest):
                os.remove(dest)
    if not success:
        create_fallback_image(fname, fname.split('.')[0].capitalize())

print("All 15 product images verified in:", TARGET_DIR)

