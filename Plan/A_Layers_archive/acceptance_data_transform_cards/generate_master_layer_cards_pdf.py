#!/usr/bin/env python3
# ============================================================================
# ARCHIVED — historical snapshot. DO NOT RUN. (See ../README.md in A_Layers_archive.)
# The live A_Layers no longer builds acceptance cards or a PDF and has NO `fpdf`
# dependency; this file is kept only as a reference of the former build step.
# ============================================================================
"""Generate printable A4 PDF with one Master Layer Card per page.

Usage: python3 generate_master_layer_cards_pdf.py
Output: Master_Layer_Cards_Print_A4.pdf in the same folder.

Archived helper. Cards are auto-discovered (00 overview first, then L01..L10 by glob)
so the list and page count can never drift from the files on disk. Live number
generation now belongs to ../A_Layers/config/numerical-amounts.json and
../A_Layers/tools/numbers.py; this archived helper is not part of the live build.
"""

from fpdf import FPDF
from pathlib import Path
import re

CARDS_DIR = Path(__file__).parent
OUTPUT_PDF = CARDS_DIR / "Master_Layer_Cards_Print_A4.pdf"

PAGE_WIDTH = 210  # A4 mm
PAGE_HEIGHT = 297
MARGIN = 12  # mm

# Historical marker cleanup; archived cards should already contain plain values.
_NA_REGION = re.compile(r"<!--na:\w+-->(.*?)<!--/na-->")
_NA_TAG = re.compile(r"<!--/?na(?::\w+)?-->")


def strip_na(text: str) -> str:
    text = _NA_REGION.sub(lambda m: m.group(1), text)
    return _NA_TAG.sub("", text)


def discover_cards():
    """00 overview first, then L01..L10 by glob — no hardcoded list, no fixed page count."""
    cards = []
    overview = CARDS_DIR / "00_Crosscutting_Overview_Card.md"
    if overview.exists():
        cards.append(overview)
    cards.extend(sorted(CARDS_DIR.glob("L[0-9][0-9]_*_Card.md")))
    return cards


class CardsPDF(FPDF):
    def __init__(self, total_pages=0):
        super().__init__(format="A4", unit="mm")
        self.total_pages = total_pages
        self.set_auto_page_break(auto=True, margin=15)
        self.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        self.add_font("DejaVu", "B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

    def header(self):
        self.set_font("DejaVu", "", 8)
        self.set_text_color(100)
        self.cell(0, 6, "S&P 500 ML Pipeline A — Master Layer Cards (printable, A4)", align="C")
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(120)
        total = self.total_pages or self.page_no()
        self.cell(0, 10, f"Page {self.page_no()} / {total}   |   Pin to 3D model   |   Source: ENG/Layers_Short_SOT", align="C")

    def render_card(self, md_path: Path):
        """Render one card file to current page."""
        content = strip_na(md_path.read_text(encoding="utf-8"))
        lines = content.splitlines()

        # Title from the first '# ' heading (no magic-string dependency).
        title = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("# ")), md_path.stem)

        self.set_font("DejaVu", "B", 14)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 7, title, align="L")
        self.ln(2)

        self.set_draw_color(180)
        self.line(MARGIN, self.get_y(), PAGE_WIDTH - MARGIN, self.get_y())
        self.ln(3)

        self.set_font("DejaVu", "", 9)
        self.set_text_color(40)

        in_list = False
        for raw_line in lines:
            line = raw_line.rstrip()
            if not line or line.startswith("---") or line.startswith("# "):
                if in_list:
                    self.ln(1)
                    in_list = False
                continue

            if line.startswith("## "):
                if in_list:
                    self.ln(1)
                    in_list = False
                self.set_font("DejaVu", "B", 10)
                self.set_text_color(20, 60, 120)
                self.set_x(self.l_margin)
                self.multi_cell(0, 5.5, line[3:].strip())
                self.set_font("DejaVu", "", 9)
                self.set_text_color(40)
                self.ln(0.5)
                continue

            if line.startswith("**") and line.endswith("**") and ":" not in line[2:-2]:
                self.set_font("DejaVu", "B", 9)
                self.set_x(self.l_margin)
                self.multi_cell(0, 5, line.strip("*"))
                self.set_font("DejaVu", "", 9)
                continue

            if line.startswith("- "):
                in_list = True
                self._render_inline(line[2:], bullet=True)
                continue

            self._render_inline(line)
            in_list = False

        self.ln(3)

    def _render_inline(self, text: str, bullet: bool = False):
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = text.replace("`", "").replace("**", "")
        self.set_x(self.l_margin)
        if bullet:
            self.cell(4, 5, "•", ln=0)
            self.set_x(self.get_x() + 4)
        self.multi_cell(0, 5, text)


def main():
    cards = discover_cards()
    if not cards:
        print("WARNING: no cards discovered")
        return
    pdf = CardsPDF(total_pages=len(cards))
    pdf.set_margins(MARGIN, 14, MARGIN)
    for card_path in cards:
        pdf.add_page()
        pdf.render_card(card_path)
        print(f"Added: {card_path.name}")
    pdf.output(str(OUTPUT_PDF))
    print(f"\nPDF created: {OUTPUT_PDF}")
    print(f"Total pages: {len(cards)} (one card per A4 page)")


if __name__ == "__main__":
    main()
