import ssl
import urllib.request
from parser import parse_ft, parse_tariff_page

# แยก 2 URL ชัดเจน
URL_TARIFF = "https://www.mea.or.th/our-services/service-rates/other/D5xEaEwgU"
URL_FT = "https://www.mea.or.th/our-services/service-rates/ft/statistics"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "th,en;q=0.9",
    "Connection": "keep-alive",
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        return resp.read().decode("utf-8")

print("--- 1. Testing FT (จากหน้าสถิติ) ---")
try:
    html_ft = fetch(URL_FT)
    ft = parse_ft(html_ft)
    print(f"Ft Rate: {ft} THB/kWh")
except Exception as e:
    print(f"Error fetching FT: {e}")

print("\n--- 2. Testing Tariff Blocks (จากหน้าอัตราค่าไฟ) ---")
try:
    html_tariff = fetch(URL_TARIFF)
    blocks = parse_tariff_page(html_tariff)
    print(f"Found {len(blocks)} block(s)\n")
    for b in blocks:
        print(f"[Block Key]: {b.key} | [Title]: {b.title}")
        if b.on_peak is not None:
            print(f"  - On Peak: {b.on_peak} | Off Peak: {b.off_peak} | Service: {b.service_charge}")
        if b.tiers:
            print(f"  - Tiers count: {len(b.tiers)}")
except Exception as e:
    print(f"Error fetching Tariff: {e}")