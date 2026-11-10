"""ثوابت وهوية إجادة، من غير pandas عشان الصفحة تفتح بسرعة."""
import base64
import io
import os

from PIL import Image, ImageOps

BASE = os.path.dirname(os.path.abspath(__file__))
EJADA_LOGO = os.path.join(BASE, "assets", "ejada_logo.png")

PERIODS = {
    "يومي": ("نجم تحصيل اليوم", "التحصيل اليومي"),
    "أسبوعي": ("نجم تحصيل الأسبوع", "التحصيل الأسبوعي"),
    "شهري": ("نجم تحصيل الشهر", "التحصيل الشهري"),
}
# مصر: "سباق التحصيل" بدل نجم التحصيل، ومن غير لوجو
PERIODS_EG = {
    "يومي": ("نجم سباق اليوم", "التحصيل اليومي"),
    "أسبوعي": ("نجم سباق الأسبوع", "التحصيل الأسبوعي"),
    "شهري": ("نجم سباق الشهر", "التحصيل الشهري"),
}
REGIONS = {"داشبورد السعودية": "saudi", "داشبورد مصر": "egypt"}
BRANCH_VIEWS = {
    "كل فرع لوحده": "separate",
    "مقارنة الفروع مع بعض": "compare",
    "المقارنة + كل فرع لوحده": "all",
}
RANKS = {"إجمالي التحصيل": "total", "نسبة تحقيق التارجت": "pct"}
MODES = {
    "عرض التقدم": "progress",
    "عرض النهاية (الأفضل)": "finale",
    "الاتنين بالتبديل التلقائي": "both",
}


def ejada_white_uri() -> str:
    """لوجو إجادة أبيض (للخلفية الكحلي) مقصوص من الفراغات."""
    src = Image.open(EJADA_LOGO).convert("RGBA")
    alpha = src.split()[3]
    if alpha.getextrema()[0] == 255:  # لو الملف بخلفية بيضاء مش شفافة
        alpha = ImageOps.invert(src.convert("L")).point(lambda p: 0 if p < 30 else min(255, p * 2))
    white = Image.new("RGBA", src.size, (255, 255, 255, 255))
    white.putalpha(alpha)
    bbox = alpha.point(lambda p: 255 if p > 20 else 0).getbbox()
    if bbox:
        white = white.crop(bbox)
    white.thumbnail((520, 520))
    buf = io.BytesIO()
    white.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
