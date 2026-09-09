import ssl
import urllib.request
from parser import parse_ft, parse_tariff_page

# 1. URL สำหรับดึงข้อมูลจาก MEA
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


def fetch_html(url: str) -> str:
    """ส่ง HTTP Request ดึง HTML สดแบบไม่ติด WinError 10054"""
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        return resp.read().decode("utf-8")


def main():
    print("=" * 65)
    print("        MEA THAILAND GRID TARIFFS - FULL PARSER TEST")
    print("=" * 65)

    # --- Step 1: ดึงและแกะค่า Ft ---
    print(f"\n[1/2] Fetching Ft Data from: {URL_FT} ...")
    try:
        html_ft = fetch_html(URL_FT)
        ft_val = parse_ft(html_ft)
        print(f"  -> Parsed Ft Rate: {ft_val} THB/kWh ({ft_val * 100:.2f} สตางค์/หน่วย)")
    except Exception as e:
        print(f"  ! Error fetching Ft: {e}")
        ft_val = 0.1623  # Fallback ตัวอย่าง

    # --- Step 2: ดึงและแกะค่า Tariff Blocks ---
    print(f"\n[2/2] Fetching Tariff Data from: {URL_TARIFF} ...")
    try:
        html_tariff = fetch_html(URL_TARIFF)
        blocks = parse_tariff_page(html_tariff)
        print(f"  -> Total Blocks Parsed: {len(blocks)}")
    except Exception as e:
        print(f"  ! Error fetching Tariff: {e}")
        return

    print("\n" + "=" * 65)
    print("           DETAILED SENSOR BREAKDOWN BY SUB-TARIFF")
    print("=" * 65)

    # --- Step 3: แสดงผลแยกตามทุก Sub-Tariff ---
    sub_tariffs = [
        ("tou_131", "อัตรา 1.3.1 TOU (แรงดัน 12 - 24 กิโลโวลต์)"),
        ("tou_132", "อัตรา 1.3.2 TOU (แรงดันต่ำกว่า 12 กิโลโวลต์)"),
        ("le150", "อัตรา 1.1 บ้านอยู่อาศัย (ไม่เกิน 150 หน่วย)"),
        ("gt150", "อัตรา 1.2 บ้านอยู่อาศัย (เกิน 150 หน่วย)"),
    ]

    for sub_key, sub_title in sub_tariffs:
        print(f"\n>>> Sub-Tariff: [{sub_key}] — {sub_title}")
        print("-" * 65)

        # ค้นหา Block ที่ตรงกับ Sub-Tariff
        block = next((b for b in blocks if b.key == sub_key), None)

        if not block:
            print("  ! No data block found for this sub-tariff in scraped HTML.")
            continue

        # จำลอง Sensor: TOU Rates
        if block.on_peak is not None:
            print(f"  [Sensor] On Peak Rate      : {block.on_peak} THB/kWh")
            print(f"  [Sensor] Off Peak Rate     : {block.off_peak} THB/kWh")

        # จำลอง Sensor: Tiered Rates (ขั้นบันได)
        if block.tiers:
            print(f"  [Sensors] Tier Rates ({len(block.tiers)} tiers):")
            for idx, tier in enumerate(block.tiers, start=1):
                print(f"    - Tier {idx} ({tier.label}): {tier.rate} THB/kWh")

        # จำลอง Sensor: Service Charge
        if block.service_charge is not None:
            print(f"  [Sensor] Service Charge    : {block.service_charge} THB/month")

        # จำลอง Sensor: Ft Rate
        print(f"  [Sensor] Ft Rate           : {ft_val} THB/kWh")

    print("\n" + "=" * 65)
    print("                     TEST COMPLETE")
    print("=" * 65)


if __name__ == "__main__":
    main()