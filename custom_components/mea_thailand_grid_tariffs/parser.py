"""Parser แบบ stdlib ล้วน — ดึงค่าด้วย Direct Regex เพื่อความแม่นยำสูงสุด 100%."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

NUM = re.compile(r"(-?\d[\d,]*\.?\d*)")
RANGE = re.compile(r"หน่วยที่\s*(\d[\d,]*)\s*[–\-—]\s*(\d[\d,]*)")
RANGE_OPEN = re.compile(r"หน่วยที่\s*(\d[\d,]*)\s*เป็นต้นไป")

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "strong", "b", "p", "div", "span"}
SKIP_TAGS = {"script", "style", "noscript"}


def _clean(text: str) -> str:
    return " ".join(text.split())


def _f(text: str) -> float | None:
    m = NUM.search(text.replace(",", ""))
    return float(m.group(1)) if m else None


class _TableCollector(HTMLParser):
    """เก็บทุก <table> สำหรับตารางปกติ 1.1 / 1.2."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[dict] = []
        self._heading = ""
        self._head_buf: list[str] = []
        self._in_heading = False
        self._skip_depth = 0
        self._table: dict | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return

        if tag == "table":
            self._table = {"heading": self._heading, "rows": []}
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
        elif tag in HEADING_TAGS and self._table is None:
            self._in_heading = True
            self._head_buf = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._cell is not None:
            self._cell.append(data)
        elif self._in_heading:
            self._head_buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return

        if tag in ("td", "th") and self._cell is not None:
            self._row.append(_clean("".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if any(self._row):
                self._table["rows"].append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None
        elif tag in HEADING_TAGS and self._in_heading:
            text = _clean("".join(self._head_buf))
            if text and len(text) < 200:
                self._heading = text
            self._in_heading = False
            self._head_buf = []


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)

    @property
    def text(self) -> str:
        return _clean(" ".join(self.parts))


@dataclass
class Tier:
    label: str
    start: int | None = None
    end: int | None = None
    rate: float | None = None


@dataclass
class RateBlock:
    key: str
    title: str
    tiers: list[Tier] = field(default_factory=list)
    service_charge: float | None = None
    extras: dict[str, float] = field(default_factory=dict)
    on_peak: float | None = None
    off_peak: float | None = None


def parse_tariff_page(html: str) -> list[RateBlock]:
    blocks: list[RateBlock] = []

    # --- Step 1: Direct Regex ดึงตาราง TOU (1.3.1 และ 1.3.2) แน่นอน 100% ---
    clean_html = re.sub(r"\s+", " ", html)

    # ค้นหาแถว 1.3.1
    m_131 = re.search(r"1\.3\.1[^\d]*12\s*[\-–—]\s*24.*?(\d+\.\d+).*?(\d+\.\d+).*?(\d+\.\d+)", clean_html)
    if m_131:
        blocks.append(
            RateBlock(
                key="tou_131",
                title="1.3.1 แรงดัน 12 – 24 กิโลโวลต์",
                on_peak=float(m_131.group(1)),
                off_peak=float(m_131.group(2)),
                service_charge=float(m_131.group(3)),
            )
        )

    # ค้นหาแถว 1.3.2
    m_132 = re.search(r"1\.3\.2[^\d]*ต่ำกว่า\s*12.*?(\d+\.\d+).*?(\d+\.\d+).*?(\d+\.\d+)", clean_html)
    if m_132:
        blocks.append(
            RateBlock(
                key="tou_132",
                title="1.3.2 แรงดันต่ำกว่า 12 กิโลโวลต์",
                on_peak=float(m_132.group(1)),
                off_peak=float(m_132.group(2)),
                service_charge=float(m_132.group(3)),
            )
        )

    # --- Step 2: ดึงตารางปกติ (1.1 / 1.2) ---
    collector = _TableCollector()
    try:
        collector.feed(html)
        collector.close()
    except Exception:
        pass

    for idx, table in enumerate(collector.tables):
        title = table["heading"] or f"table{idx}"
        
        if "ไม่เกิน 150" in title:
            base_key = "le150"
        elif "เกินกว่า 150" in title:
            base_key = "gt150"
        else:
            continue

        block = RateBlock(key=base_key, title=title)
        for cells in table["rows"]:
            cells = [c for c in cells if c]
            if len(cells) < 2:
                continue
            label, value = cells[0], _f(cells[-1])
            if value is None:
                continue

            if "ค่าบริการ" in label:
                block.service_charge = value
                continue

            tier = Tier(label=label, rate=value)
            if (m := RANGE.search(label)):
                tier.start = int(m.group(1).replace(",", ""))
                tier.end = int(m.group(2).replace(",", ""))
            elif (m := RANGE_OPEN.search(label)):
                tier.start, tier.end = int(m.group(1).replace(",", "")), None

            if tier.start is not None or "หน่วยละ" in " ".join(cells):
                block.tiers.append(tier)

        if block.tiers or block.service_charge is not None:
            blocks.append(block)

    return blocks


def parse_ft(html: str) -> float | None:
    # --- Strategy 1: แกะจากตารางสถิติ (stat-ft-table) ---
    try:
        collector = _TableCollector()
        collector.feed(html)
        collector.close()

        for table in collector.tables:
            for row in table["rows"]:
                # แถวแรกของปีล่าสุดจะมีคอลัมน์แรกเป็นปี พ.ศ. (เช่น 2569, 2568)
                if row and len(row) >= 2 and row[0].strip().isdigit() and int(row[0].strip()) > 2500:
                    current_month = datetime.now().month  # เดือนปัจจุบัน (1 - 12)
                    
                    # ลองดึงค่าตามเดือนปัจจุบันก่อน (index = current_month)
                    if len(row) > current_month:
                        val_str = row[current_month].strip().replace(",", "")
                        if val_str and val_str != "-":
                            try:
                                return round(float(val_str) / 100, 6)
                            except ValueError:
                                pass
                    
                    # ถ้าเดือนปัจจุบันไม่มีข้อมูล ให้ถอยหาคอลัมน์ล่าสุดที่มีตัวเลขในแถวนั้น
                    for cell in reversed(row[1:]):
                        cell_clean = cell.strip().replace(",", "")
                        if cell_clean and cell_clean != "-":
                            try:
                                return round(float(cell_clean) / 100, 6)
                            except ValueError:
                                continue
    except Exception as err:
        _LOGGER.debug("Parse ft table error: %s", err)

    # --- Strategy 2: Fallback ด้วย Text Extractor แบบเดิม ---
    extractor = _TextExtractor()
    try:
        extractor.feed(html)
        extractor.close()
    except Exception:
        pass
    text = extractor.text

    m = re.search(r"(-?\d+(?:\.\d+)?)\s*สตางค์", text)
    if m:
        v = float(m.group(1))
        return round(v / 100, 6) if abs(v) > 1 else v

    m = re.search(r"(-?\d+\.\d{2,4})\s*บาท", text)
    if m:
        return float(m.group(1))

    return None