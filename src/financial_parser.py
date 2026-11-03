"""Extract auditable *candidates* from Vietnamese financial-statement PDFs.

No candidate is promoted to verified_observations without independent review.
Page numbers, raw row snippets and extraction methods are retained.
"""
import re
import unicodedata

def normalize(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d")

LABELS = {
    "revenue": [
        r"doanh thu thuan ve ban hang va cung cap dich vu",
        r"doanh thu thuan",
        r"doanh thu ban hang va cung cap dich vu",
    ],
    "profit": [
        r"loi nhuan sau thue thu nhap doanh nghiep",
        r"loi nhuan sau thue",
    ],
}
# Keep exact raw tokens. Do not interpret amounts or columns before reviewing headings.
NUMBER = re.compile(r"(?<![A-Za-z])(?:\\(?-:[-+]?\\d[\\d., ]*\\)|[-+]?\\d[\\d.,]*)(?![A-Za-z])")
# Simpler token pattern with decimal/group separators.
AMOUNT = re.compile(r"(?<![A-Za-z0-9])(?:\\([-+]?\\d[\\d.,]*\\)|[-+]?\\d[\\d.,]*)(?![A-Za-z])")

def candidates_from_pdf(pdf):
    result = {"revenue": [], "profit": [], "pages_scanned_or_image_only": [], "page_count": len(pdf)}
    for index in range(min(len(pdf), 60)):
        page = pdf[index]
        text = page.get_text("text", sort=True)
        if len(text.strip()) < 80:
            result["pages_scanned_or_image_only"].append(index + 1)
        lines = [s.strip() for s in text.splitlines() if s.strip()]
        for pos, line in enumerate(lines):
            folded = normalize(line)
            for key, phrases in LABELS.items():
                if any(p in folded for p in phrases):
                    # Neighboring rows may hold amounts when PDF layout is columnar.
                    excerpt = " | ".join(lines[max(0,pos-1):pos+9])[:1000]
                    if len(result[key]) < 12:
                        result[key].append({
                            "page": index+1, "label": line[:180],
                            "raw_excerpt": excerpt,
                            "number_tokens": AMOUNT.findall(excerpt)[:18],
                            "method": "pymupdf-text",
                            "verified": False,
                        })
    result["status"] = ("candidate_rows_found" if result["revenue"] and result["profit"]
                        else "image_only_or_no_matching_rows" if result["pages_scanned_or_image_only"]
                        else "missing_revenue_or_profit_rows")
    return result
