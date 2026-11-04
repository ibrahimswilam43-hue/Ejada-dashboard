"""بناء داشبورد HTML (أبيض على كحلي) لأفضل موظف تحصيل، يدعم أكتر من شركة (شيت لكل شركة)."""
import base64
import datetime
import html
import io
import math
import os

import pandas as pd
from PIL import Image, ImageOps

BASE = os.path.dirname(os.path.abspath(__file__))
EJADA_LOGO = os.path.join(BASE, "assets", "ejada_logo.png")

PERIODS = {
    "يومي": ("نجم تحصيل اليوم", "التحصيل اليومي"),
    "أسبوعي": ("نجم تحصيل الأسبوع", "التحصيل الأسبوعي"),
    "شهري": ("نجم تحصيل الشهر", "التحصيل الشهري"),
}
MODES = {
    "عرض التقدم": "progress",
    "عرض النهاية (الأفضل)": "finale",
    "الاتنين بالتبديل التلقائي": "both",
}
TOTAL_WORDS = {"الإجمالي", "الاجمالي", "اجمالي", "إجمالي", "المجموع", "مجموع",
               "total", "grand total", "sum"}


# ---------------------------------------------------------------- البيانات
def _clean(df: pd.DataFrame) -> pd.DataFrame:
    if df.shape[1] < 2:
        raise ValueError("لازم عمودين: الموظف والتحصيل.")
    df = df.iloc[:, :2].copy()
    df.columns = ["emp", "amount"]
    df["emp"] = df["emp"].astype(str).str.strip()
    df["amount"] = pd.to_numeric(
        df["amount"].astype(str).str.replace(",", "", regex=False)
        .str.replace("٬", "", regex=False).str.strip(),
        errors="coerce",
    )
    df = df.dropna(subset=["amount"])
    df = df[~df["emp"].str.lower().isin(TOTAL_WORDS | {"", "nan", "none"})]
    if df.empty:
        raise ValueError("مفيش بيانات صالحة (تأكد إن العمود التاني أرقام).")
    df = df.groupby("emp", as_index=False, sort=False)["amount"].sum()
    return df.sort_values("amount", ascending=False).reset_index(drop=True)


def load_workbook(file):
    """كل شيت = شركة. يرجع ({اسم الشيت: جدول مرتب}, {اسم الشيت: سبب التجاهل})."""
    xl = pd.ExcelFile(file)
    ok, bad = {}, {}
    for sh in xl.sheet_names:
        try:
            ok[sh] = _clean(xl.parse(sh))
        except Exception as e:  # noqa: BLE001
            bad[sh] = str(e)
    return ok, bad


def _buf(file):
    """UploadedFile -> BytesIO جديد (عشان القراءة المتكررة مع كل rerun)."""
    return io.BytesIO(file.getvalue()) if hasattr(file, "getvalue") else file


def norm_name(s) -> str:
    """مطابقة اسم الشركة بالاسم: تجاهل المسافات الزايدة والحروف الكبيرة وشكل الهمزة والياء."""
    s = " ".join(str(s).split()).lower()
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي")):
        s = s.replace(a, b)
    return s


def target_sheets(file):
    return pd.ExcelFile(_buf(file)).sheet_names


def load_targets(file, sheet=0):
    """شيت من عمودين: الشركة | التارجت. يرجع {اسم مُطبَّع: (الاسم الأصلي, التارجت)}."""
    df = pd.read_excel(_buf(file), sheet_name=sheet)
    if df.shape[1] < 2:
        raise ValueError("شيت التارجت لازم يكون فيه عمودين: الشركة والتارجت.")
    df = df.iloc[:, :2].copy()
    df.columns = ["co", "target"]
    df["co"] = df["co"].astype(str).str.strip()
    df["target"] = pd.to_numeric(
        df["target"].astype(str).str.replace(",", "", regex=False).str.replace("٬", "", regex=False).str.strip(),
        errors="coerce",
    )
    df = df.dropna(subset=["target"])
    df = df[(df["target"] > 0) & ~df["co"].str.lower().isin({"", "nan", "none"})]
    if df.empty:
        raise ValueError("مفيش تارجت صالح في الشيت (تأكد إن العمود التاني أرقام أكبر من صفر).")
    return {norm_name(r.co): (r.co, float(r.target)) for r in df.itertuples()}


# ---------------------------------------------------------------- الصور
def _data_uri(raw: bytes, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


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
    white.thumbnail((700, 700))
    buf = io.BytesIO()
    white.save(buf, "PNG")
    return _data_uri(buf.getvalue(), "image/png")


def photo_uri(raw: bytes) -> str:
    """صورة الموظف المرفوعة: قص مربع."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    img = ImageOps.fit(img, (600, 600), centering=(0.5, 0.35))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return _data_uri(buf.getvalue(), "image/jpeg")


# ---------------------------------------------------------------- أدوات
def _fmt(v: float) -> str:
    return f"{v:,.0f}"


def _pct(v: float, target: float) -> int:
    return int(math.floor(v / target * 100)) if target > 0 else 0


def _short(name: str) -> str:
    parts = name.split()
    if not parts:
        return name
    if parts[0] in ("عبد", "أبو", "ابو", "أم", "ام") and len(parts) > 1:
        return f"{parts[0]} {parts[1]}"
    return parts[0]


def _avatar(photo_src=None) -> str:
    if photo_src:
        return f'<img src="{photo_src}" alt="">'
    return '<svg class="ua" aria-hidden="true"><use href="#user"/></svg>'


# ---------------------------------------------------------------- الشرائح
def _finale(df, target, cur, photo_src, title, sub, winners=3):
    esc = html.escape
    m = min(max(1, winners), len(df))
    cols = []
    order = (1, 0, 2) if m == 3 else tuple(range(m))  # RTL: الثاني يمين، الأول وسط، الثالث شمال
    for k in order:
        r = df.iloc[k]
        p = _pct(r.amount, target)
        rank = k + 1
        crown = pill = ""
        if rank == 1:
            crown = ('<svg class="crown" viewBox="0 0 72 48" aria-hidden="true"><path d="M6 40 L12 12 L26 26 L36 6 L46 26 L60 12 L66 40 Z"/>'
                     '<path d="M6 45 H66"/></svg>')
            pill = '<span class="pill">أفضل موظف تحصيل</span>'
            meta = f'<b>{p}%</b> من التارجت البالغ {_fmt(target)} {esc(cur)}'
        else:
            meta = f'<b>{p}%</b> من التارجت'
        cols.append(f"""
        <div class="pod r{rank}">
          {crown}
          <div class="halo"><div class="avring">{_avatar(photo_src if rank == 1 else None)}</div></div>
          {pill}
          <h3 class="pn">{esc(r.emp)}</h3>
          <div class="pa"><b>{_fmt(r.amount)}</b><small>{esc(cur)}</small></div>
          <div class="pbar"><i style="--w:{min(p, 100)}%"></i></div>
          <p class="pm">{meta}</p>
          <div class="block">{rank}</div>
        </div>""")
    return (f'<div class="slide" data-k="finale" data-title="{esc(title, True)}" data-sub="{esc(sub, True)}">'
            f'<div class="podium">{"".join(cols)}</div></div>')


def _cheer_html(text):
    esc = html.escape
    for sep in ("…", "..."):
        if sep in text:
            a, b = text.split(sep, 1)
            return f"{esc(a.strip())}{sep} <b>{esc(b.strip())}</b>"
    return esc(text)


def _progress(df, target, cur, top_n, photo_src, sub, cheer):
    esc = html.escape
    rows = df.head(top_n)
    pcts = [r.amount / target * 100 for r in rows.itertuples()]
    scale = max(100.0, max(pcts))
    over = scale > 100
    cols = []
    for idx, (r, p) in enumerate(zip(rows.itertuples(), pcts)):
        cols.append(f"""
        <div class="col">
          <span class="pct">{int(math.floor(p))}%</span>
          <div class="track{' tl' if over else ''}" style="--tl:{100 / scale * 100:.2f}%"><i style="--h:{p / scale * 100:.2f}%"></i></div>
          <div class="avs">{_avatar(photo_src if idx == 0 else None)}</div>
          <span class="nm" title="{esc(r.emp, True)}">{esc(_short(r.emp))}</span>
        </div>""")
    legend = '<span class="legend"><u></u> الخط المتقطع = التارجت</span>' if over else ""
    return (f'<div class="slide" data-k="progress" data-title="أرقام تتحرك... ونتائج تقول مين الأقوى" data-sub="{esc(sub, True)}">'
            f'<div class="chart">{legend}<div class="bars"><div class="arrow"></div>{"".join(cols)}</div>'
            f'<p class="cheer">{_cheer_html(cheer)}</p></div></div>')


# ---------------------------------------------------------------- الصفحة
DEFAULT_CHEER = "السباق بدأ… ومين بيوصل للقمة أول؟"


def build_html(companies, period, mode, currency, top_n=15, confetti=False, date=None,
               cheer=DEFAULT_CHEER, auto_secs=15, auto_start=False, winners=3) -> str:
    """companies = [{name, df, target, photo(bytes|None)}] بالترتيب اللي هيتعرض."""
    esc = html.escape
    date = date or datetime.date.today()
    headline, period_label = PERIODS[period]
    start = "finale" if mode == "finale" else "progress"
    ds = date.strftime("%d/%m/%Y")

    sections, first_title, first_sub = [], "", ""
    for i, c in enumerate(companies):
        df, target = c["df"], c["target"]
        photo_src = photo_uri(c["photo"]) if c.get("photo") else None
        n = len(df)
        shown = min(top_n, n)
        count_txt = f"أعلى {shown} من {n} موظف" if n > shown else f"{n} موظف"
        sub_p = f"{period_label} · {count_txt} · إجمالي التحصيل {_fmt(df.amount.sum())} {currency}"
        m_w = min(max(1, winners), n)
        top_txt = "الأعلى تحصيلًا" if m_w == 1 else f"أعلى {m_w} في التحصيل"
        sub_f = f"{period_label} · {top_txt} · بتاريخ {ds}"
        slides = ""
        if mode in ("progress", "both"):
            slides += _progress(df, target, currency, top_n, photo_src, sub_p, cheer)
        if mode in ("finale", "both"):
            slides += _finale(df, target, currency, photo_src, headline, sub_f, winners)
        sections.append(f'<section class="co" data-name="{esc(c["name"], True)}">{slides}</section>')
        if i == 0:
            first_title = "أرقام تتحرك... ونتائج تقول مين الأقوى" if start == "progress" else headline
            first_sub = sub_p if start == "progress" else sub_f

    names = [c["name"] for c in companies]
    chev_r = '<svg viewBox="0 0 24 24"><polyline points="9 5 16 12 9 19"/></svg>'
    chev_l = '<svg viewBox="0 0 24 24"><polyline points="15 5 8 12 15 19"/></svg>'
    caret = '<svg class="caret" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>'
    if len(names) == 1:
        switch = f'<div class="switch"><span class="name static"><span class="nt" id="coName">{esc(names[0])}</span></span></div>'
    else:
        items = "".join(f'<li data-i="{i}"><button type="button">{esc(n)}</button></li>' for i, n in enumerate(names))
        switch = (
            '<div class="switch">'
            f'<button class="nav" id="prev" type="button" aria-label="الشركة السابقة">{chev_r}</button>'
            f'<div class="pick"><button class="name" id="coBtn" type="button" aria-haspopup="true">'
            f'<span class="nt" id="coName">{esc(names[0])}</span>{caret}</button>'
            f'<ul class="list" id="coList" hidden>{items}</ul></div>'
            f'<button class="nav" id="next" type="button" aria-label="الشركة التالية">{chev_l}</button>'
            f'<span class="cnt" id="coCnt">1 / {len(names)}</span>'
            '<button class="nav clk off" id="clk" type="button" aria-pressed="false" title="تبديل تلقائي بين الشركات">'
            '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><polyline points="12 7.5 12 12 15.5 14"/>'
            '<line class="sl" x1="4" y1="20" x2="20" y2="4"/></svg></button></div>')

    tabs = ""
    if mode == "both":
        tabs = ('<div class="tabs"><button type="button" data-k="progress" class="on">التقدم</button>'
                '<button type="button" data-k="finale">النهاية</button></div>')

    canvas = '<canvas id="cf"></canvas>' if confetti else ""

    page = TEMPLATE
    for k, v in {
        "__TITLE__": esc(f"{headline} - {', '.join(names)}"),
        "__LOGO__": ejada_white_uri(),
        "__SWITCH__": switch,
        "__H1__": esc(first_title),
        "__SUB__": esc(first_sub),
        "__TABS__": tabs,
        "__SECTIONS__": "".join(sections),
        "__CANVAS__": canvas,
        "__MODE__": mode,
        "__CONF__": "true" if confetti else "false",
        "__SECS__": str(max(1, int(auto_secs))),
        "__AUTO__": "true" if auto_start else "false",
    }.items():
        page = page.replace(k, v)
    return page


TEMPLATE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@500;700;900&display=swap" rel="stylesheet">
<style>
:root{--navy:#13204F;--deep:#0A1330;--mist:#C7D4F0;--line:rgba(255,255,255,.22);--soft:rgba(255,255,255,.10)}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{font-family:'Cairo','Segoe UI',Tahoma,sans-serif;background:var(--deep);color:#fff;overflow:hidden}
button{font:inherit;color:inherit;background:none;border:0;cursor:pointer}
.page{position:relative;height:100vh;min-height:560px;display:flex;flex-direction:column;padding:2.4vh 3.5vw 0;overflow:hidden;
  background:linear-gradient(160deg,#1A2C6E 0%,var(--navy) 46%,var(--deep) 100%)}
.orb{position:absolute;border-radius:50%;background:rgba(255,255,255,.05);pointer-events:none}
.orb.a{width:62vh;height:62vh;left:-14vh;top:-26vh}
.orb.b{width:82vh;height:82vh;right:-24vh;bottom:-36vh}

/* ---- الفريم الرسمي: معينات ---- */
.dm{position:absolute;width:3.4vh;height:3.4vh;background:#fff;opacity:.92;pointer-events:none;
  clip-path:polygon(50% 0,100% 50%,50% 100%,0 50%)}
.d1{left:calc(6.5vw - 1.7vh);top:3vh}
.d2{left:calc(20.4vw - 1.7vh);top:3vh}.d3{left:calc(20.4vw + 1.7vh);top:3vh}
.d4{left:calc(20.4vw + 5.1vh);top:3vh}.d5{left:calc(20.4vw + 8.5vh);top:3vh}
.d6{left:calc(6.5vw - 1.7vh);top:78.6vh}
.d7{left:calc(6.5vw - 1.7vh);top:91.8vh}.d8{left:calc(6.5vw - 1.7vh);top:95.2vh}
.d9{left:calc(92.1vw - 1.7vh);top:87.2vh}.d10{left:calc(92.1vw - 1.7vh);top:90.6vh}

/* ---- الرأس ---- */
.head{display:flex;align-items:flex-start;gap:2.2vw;height:16vh;position:relative;z-index:3}
.logo img{height:14vh;width:auto;display:block}
.tb{min-width:0;padding-top:.4vh}
.switch{display:inline-flex;align-items:center;gap:.6vw}
.nav{width:4vh;height:4vh;border-radius:50%;border:1.5px solid var(--line);display:grid;place-items:center;transition:background .2s,color .2s}
.nav:hover,.nav:focus-visible{background:#fff;color:var(--navy);outline:none}
.nav svg{width:52%;height:52%;fill:none;stroke:currentColor;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.clk .sl{display:none}
.clk.off .sl{display:block}
.clk:not(.off){background:#fff;color:var(--navy)}
.pick{position:relative}
.name{display:inline-flex;align-items:center;gap:.7vw;font-weight:800;font-size:clamp(1rem,2.6vh,1.6rem);
  padding:.4vh 1.3vw;border-radius:999px;background:var(--soft);border:1.5px solid var(--line);transition:background .2s}
button.name:hover{background:rgba(255,255,255,.2)}
.name .caret{width:1.5vh;height:1.5vh;fill:none;stroke:#fff;stroke-width:3.4;stroke-linecap:round;stroke-linejoin:round}
.cnt{font-size:clamp(.75rem,1.9vh,1.1rem);color:var(--mist);font-variant-numeric:tabular-nums;direction:ltr;unicode-bidi:isolate}
.list{position:absolute;top:calc(100% + 1vh);inset-inline-start:0;min-width:16vw;max-height:52vh;overflow:auto;list-style:none;
  background:#fff;color:var(--navy);border-radius:14px;padding:.8vh;box-shadow:0 18px 40px rgba(0,0,0,.45);z-index:30}
.list[hidden]{display:none}
.list button{display:block;width:100%;text-align:start;padding:1vh 1vw;border-radius:10px;font-weight:700;font-size:clamp(.9rem,2.2vh,1.3rem)}
.list button:hover,.list li.cur button{background:#E4EAFA}
h1{font-size:clamp(1.6rem,5.6vh,3.6rem);font-weight:900;line-height:1.15;margin-top:.9vh}
.sub{margin-top:.3vh;font-size:clamp(.85rem,2.1vh,1.3rem);color:var(--mist)}
.tabs{position:absolute;left:calc(6.5vw - 1.7vh);top:9.4vh;display:flex;gap:.3vw;padding:.4vh;border-radius:999px;
  background:var(--soft);border:1px solid var(--line);z-index:5}
.tabs button{padding:.5vh 1.2vw;border-radius:999px;font-weight:700;font-size:clamp(.8rem,1.9vh,1.1rem);color:var(--mist)}
.tabs button.on{background:#fff;color:var(--navy)}

/* ---- المنطقة الرئيسية ---- */
.stage{flex:1;min-height:0;display:flex;padding:0 9vw;position:relative;z-index:2}
.co{display:none;flex:1;min-width:0;min-height:0}
.co.on{display:flex}
.slide{display:none;flex:1;min-width:0;min-height:0;flex-direction:column}
.slide.on{display:flex}

/* ---- النهاية: البوديوم ---- */
.podium{flex:1;min-height:0;display:flex;align-items:flex-end;justify-content:center;gap:2.6vw}
.pod{flex:1 1 0;max-width:27vw;min-width:0;display:flex;flex-direction:column;align-items:center;text-align:center}
.r1{--av:20vh}.r2,.r3{--av:14.5vh}
.crown{width:5.6vh;height:auto;margin-bottom:.6vh;fill:none;stroke:#fff;stroke-width:3.2;stroke-linejoin:round;stroke-linecap:round}
.halo{padding:.9vh;border-radius:50%}
.r1 .halo{background:rgba(255,255,255,.14)}
.avring{width:var(--av);height:var(--av);border-radius:50%;border:.5vh solid #fff;background:var(--soft);overflow:hidden;display:grid}
.avring img{width:100%;height:100%;object-fit:cover}
.ua{width:100%;height:100%;fill:#fff}
.pill{margin-top:1.2vh;padding:.5vh 1.4vw;border-radius:999px;background:#fff;color:var(--navy);font-weight:800;font-size:clamp(.8rem,2vh,1.2rem)}
.pn{margin-top:1vh;font-weight:900;font-size:clamp(1.1rem,3.4vh,2.2rem);line-height:1.2;overflow-wrap:anywhere}
.r1 .pn{font-size:clamp(1.4rem,4.6vh,3rem)}
.pa{margin-top:.4vh;display:flex;align-items:baseline;gap:.5vw}
.pa b{font-size:clamp(1.4rem,4.6vh,3rem);font-weight:900;line-height:1.1;font-variant-numeric:tabular-nums}
.r1 .pa b{font-size:clamp(1.8rem,6vh,4rem)}
.pa small{font-size:clamp(.8rem,2vh,1.2rem);color:var(--mist);font-weight:700}
.pbar{width:80%;height:.9vh;min-height:5px;border-radius:99px;background:rgba(255,255,255,.22);overflow:hidden;margin-top:.9vh}
.pbar i{display:block;height:100%;width:var(--w);background:#fff;border-radius:inherit;animation:grow 1.4s .2s cubic-bezier(.2,.8,.2,1) backwards}
@keyframes grow{from{width:0}}
.pm{margin-top:.7vh;font-size:clamp(.75rem,1.9vh,1.15rem);color:var(--mist)}
.pm b{color:#fff;font-weight:900}
.block{margin-top:1.6vh;width:100%;border-radius:22px 22px 0 0;display:grid;place-items:center;font-weight:900;line-height:1;
  background:rgba(255,255,255,.14);border-top:2px solid rgba(255,255,255,.4)}
.r1 .block{height:17vh;background:#fff;color:var(--navy);font-size:clamp(2.4rem,9vh,6rem);border-top:0}
.r2 .block{height:11.5vh;font-size:clamp(1.8rem,6.5vh,4.4rem)}
.r3 .block{height:8vh;font-size:clamp(1.4rem,4.8vh,3.2rem)}

/* ---- التقدم: أعمدة ---- */
.chart{flex:1;min-height:0;display:flex;flex-direction:column;position:relative;padding-top:1vh}
.legend{align-self:flex-start;margin-bottom:.8vh;font-size:clamp(.7rem,1.7vh,1rem);color:var(--mist);display:flex;align-items:center;gap:.5vw}
.legend u{display:inline-block;width:2.4vw;border-top:2px dashed rgba(255,255,255,.7)}
.bars{flex:1;min-height:0;display:flex;justify-content:center;gap:1vw;position:relative}
.col{position:relative;z-index:1;flex:1 1 0;max-width:8vw;min-width:0;display:flex;flex-direction:column;align-items:center}
.pct{font-weight:900;font-size:clamp(.75rem,2.1vh,1.3rem);margin-bottom:.8vh;font-variant-numeric:tabular-nums}
.track{flex:1;width:100%;min-height:0;border-radius:2vh;background:rgba(255,255,255,.12);position:relative;display:flex;align-items:flex-end;overflow:hidden}
.track i{display:block;width:100%;height:var(--h);min-height:.5vh;border-radius:2vh 2vh .6vh .6vh;background:#fff;animation:rise 1.3s cubic-bezier(.2,.8,.2,1) backwards}
@keyframes rise{from{height:0}}
.track.tl::after{content:"";position:absolute;left:0;right:0;bottom:var(--tl);border-top:2px dashed rgba(255,255,255,.65)}
.avs{margin-top:1.2vh;width:min(5.6vh,100%);aspect-ratio:1;border-radius:50%;border:.35vh solid #fff;background:var(--soft);overflow:hidden;display:grid;flex:none}
.avs img{width:100%;height:100%;object-fit:cover}
.nm{margin-top:.6vh;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:700;font-size:clamp(.7rem,1.8vh,1.1rem)}
.arrow{position:absolute;left:2%;top:64%;width:84%;height:1.6vh;border-radius:2vh;background:rgba(255,255,255,.2);
  transform-origin:left center;transform:rotate(-13deg);pointer-events:none}
.arrow::after{content:"";position:absolute;right:-2.4vh;top:50%;transform:translateY(-50%);
  border-left:5vh solid rgba(255,255,255,.2);border-top:3.2vh solid transparent;border-bottom:3.2vh solid transparent}
.cheer{margin-top:1.6vh;padding-top:1.4vh;border-top:1px solid var(--line);text-align:center;font-weight:700;font-size:clamp(.95rem,2.6vh,1.6rem)}
.cheer b{font-weight:900}

/* ---- الفوتر (للفريم بس) ---- */
.foot{height:5vh;flex:none}
#cf{position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:40}

@media (max-width:900px){
  body{overflow:auto}.page{height:auto;min-height:100vh}
  .stage{padding:0 4vw}.podium{flex-direction:column;align-items:center}
  .pod{max-width:90vw}
}
@media (prefers-reduced-motion:reduce){.pbar i,.track i{animation:none}}
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><symbol id="user" viewBox="0 0 100 100">
  <circle cx="50" cy="40" r="16"/><path d="M12 100c0-21 17-35 38-35s38 14 38 35z"/></symbol></svg>
__CANVAS__
<div class="page">
  <div class="orb a"></div><div class="orb b"></div>
  <i class="dm d1"></i><i class="dm d2"></i><i class="dm d3"></i><i class="dm d4"></i><i class="dm d5"></i>
  <i class="dm d6"></i><i class="dm d7"></i><i class="dm d8"></i><i class="dm d9"></i><i class="dm d10"></i>

  <header class="head">
    <div class="logo"><img src="__LOGO__" alt="إجادة لتحصيل الديون"></div>
    <div class="tb">
      __SWITCH__
      <h1 id="ttl">__H1__</h1>
      <p class="sub" id="sub">__SUB__</p>
    </div>
  </header>
  __TABS__

  <main class="stage">__SECTIONS__</main>

  <footer class="foot"></footer>
</div>

<script>
(function(){
  var MODE='__MODE__', CONF=__CONF__;
  var cos=[].slice.call(document.querySelectorAll('.co')), n=cos.length, ci=0;
  var cur=(MODE==='finale')?'finale':'progress', timer=null;
  var $=function(id){return document.getElementById(id)};
  var nameEl=$('coName'), cntEl=$('coCnt'), list=$('coList'), btn=$('coBtn');
  var tabs=[].slice.call(document.querySelectorAll('.tabs button'));

  /* كونفيتي هادي (اختياري) */
  var cv=$('cf'), cx=cv&&cv.getContext('2d'), P=[], run=false, W=0, H=0;
  var colors=['#FFFFFF','#C7D4F0','#8FA8E0'];
  function burst(){
    if(!cv||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
    W=cv.width=innerWidth;H=cv.height=innerHeight;
    for(var i=0;i<140;i++)P.push({x:Math.random()*W,y:-20-Math.random()*H*.3,vx:(Math.random()-.5)*2.4,vy:2+Math.random()*3,
      s:5+Math.random()*7,r:Math.random()*6.28,vr:(Math.random()-.5)*.25,c:colors[(Math.random()*3)|0]});
    if(!run){run=true;tick();}
  }
  function tick(){
    cx.clearRect(0,0,W,H);
    P.forEach(function(p){p.x+=p.vx;p.y+=p.vy;p.r+=p.vr;cx.save();cx.translate(p.x,p.y);cx.rotate(p.r);
      cx.fillStyle=p.c;cx.fillRect(-p.s/2,-p.s/4,p.s,p.s/2);cx.restore();});
    P=P.filter(function(p){return p.y<H+30});
    if(P.length)requestAnimationFrame(tick);else{run=false;cx.clearRect(0,0,W,H);}
  }

  function show(){
    cos.forEach(function(c,i){c.classList.toggle('on',i===ci)});
    var act=cos[ci];
    [].forEach.call(act.querySelectorAll('.slide'),function(s){s.classList.toggle('on',s.getAttribute('data-k')===cur)});
    var s=act.querySelector('.slide.on');
    if(s){$('ttl').textContent=s.getAttribute('data-title');$('sub').textContent=s.getAttribute('data-sub');}
    if(nameEl)nameEl.textContent=act.getAttribute('data-name');
    if(cntEl)cntEl.textContent=(ci+1)+' / '+n;
    if(list){list.hidden=true;[].forEach.call(list.children,function(li,i){li.classList.toggle('cur',i===ci)});}
    tabs.forEach(function(b){b.classList.toggle('on',b.getAttribute('data-k')===cur)});
    if(cur==='finale'&&CONF)burst();
  }
  var SECS=__SECS__*1000, auto=__AUTO__, clk=$('clk');
  function setClk(){if(clk){clk.classList.toggle('off',!auto);clk.setAttribute('aria-pressed',auto?'true':'false');}}
  function schedule(){
    clearTimeout(timer);
    if(!(MODE==='both'||(auto&&n>1)))return;
    timer=setTimeout(function(){
      if(MODE==='both'){
        if(cur==='progress'){cur='finale';}
        else if(auto&&n>1){ci=(ci+1)%n;cur='progress';}
        else{cur='progress';}
      }else{ci=(ci+1)%n;}
      show();schedule();
    },SECS);
  }
  function go(d){ci=(ci+d+n)%n;cur=(MODE==='finale')?'finale':'progress';show();schedule();}
  function pick(i){ci=i;cur=(MODE==='finale')?'finale':'progress';show();schedule();}

  if($('prev'))$('prev').addEventListener('click',function(){go(-1)});
  if($('next'))$('next').addEventListener('click',function(){go(1)});
  if(btn)btn.addEventListener('click',function(e){e.stopPropagation();list.hidden=!list.hidden});
  if(list)[].forEach.call(list.children,function(li,i){li.firstChild.addEventListener('click',function(){pick(i)})});
  document.addEventListener('click',function(){if(list)list.hidden=true});
  tabs.forEach(function(b){b.addEventListener('click',function(){cur=b.getAttribute('data-k');show();schedule();})});
  document.addEventListener('keydown',function(e){
    if(n<2)return;
    if(e.key==='ArrowLeft')go(1);else if(e.key==='ArrowRight')go(-1);
  });
  if(clk)clk.addEventListener('click',function(){auto=!auto;setClk();schedule();});
  setClk();show();schedule();
})();
</script>
</body>
</html>
"""
