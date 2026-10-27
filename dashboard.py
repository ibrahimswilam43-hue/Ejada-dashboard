"""بناء داشبورد HTML تحفيزي لأفضل موظف تحصيل (ملف واحد مستقل يُعرض على شاشة الشركة)."""
import base64
import datetime
import html
import io
import math
import os

import pandas as pd
from PIL import Image, ImageOps

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")
EJADA_LOGO = os.path.join(ASSETS, "ejada_logo.png")
AVATARS = {"ذكر": os.path.join(ASSETS, "avatar_male.jpg"),
           "أنثى": os.path.join(ASSETS, "avatar_female.jpg")}

PERIODS = {
    "يومي": ("نجم تحصيل اليوم", "التحصيل اليومي"),
    "أسبوعي": ("نجم تحصيل الأسبوع", "التحصيل الأسبوعي"),
    "شهري": ("نجم تحصيل الشهر", "التحصيل الشهري"),
}
TOTAL_WORDS = {"الإجمالي", "الاجمالي", "اجمالي", "إجمالي", "المجموع", "مجموع",
               "total", "grand total", "sum"}


# ---------------------------------------------------------------- البيانات
def load_data(file) -> pd.DataFrame:
    """أول عمودين: الموظف - التحصيل. يرجع الجدول مرتبًا من الأعلى للأقل."""
    df = pd.read_excel(file)
    if df.shape[1] < 2:
        raise ValueError("الملف لازم يحتوي على عمودين: الموظف والتحصيل.")
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
        raise ValueError("مفيش بيانات صالحة في الملف (تأكد إن العمود التاني أرقام).")
    df = df.groupby("emp", as_index=False, sort=False)["amount"].sum()
    return df.sort_values("amount", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------- الصور
def _data_uri(raw: bytes, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


def file_uri(path: str, mime: str) -> str:
    with open(path, "rb") as f:
        return _data_uri(f.read(), mime)


def _jpeg_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return _data_uri(buf.getvalue(), "image/jpeg")


def ejada_uri() -> str:
    """لوجو إجادة بعد قص المساحة البيضاء الزايدة حواليه."""
    src = Image.open(EJADA_LOGO).convert("RGBA")
    img = Image.new("RGB", src.size, (255, 255, 255))  # الخلفية الشفافة -> بيضاء
    img.paste(src, mask=src.split()[3])
    bbox = ImageOps.invert(img.convert("L")).point(lambda p: 255 if p > 40 else 0).getbbox()
    if bbox:
        pad = 14
        l, t, r, b = bbox
        img = img.crop((max(l - pad, 0), max(t - pad, 0), min(r + pad, img.width), min(b + pad, img.height)))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return _data_uri(buf.getvalue(), "image/png")


def company_logo_uri(raw: bytes) -> str:
    """أي لوجو: يتشال منه الفراغ (الأبيض/الشفاف) حواليه، وبعدين يتحط في إطار ثابت بالـ contain."""
    src = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGBA")
    flat = Image.new("RGBA", src.size, (255, 255, 255, 255))
    flat.alpha_composite(src)
    rgb = flat.convert("RGB")
    bbox = ImageOps.invert(rgb.convert("L")).point(lambda p: 255 if p > 25 else 0).getbbox()
    if bbox:
        l, t, r, b = bbox
        pad = int(max(r - l, b - t) * 0.03)
        rgb = rgb.crop((max(l - pad, 0), max(t - pad, 0), min(r + pad, rgb.width), min(b + pad, rgb.height)))
    rgb.thumbnail((900, 900))
    buf = io.BytesIO()
    rgb.save(buf, "PNG")
    return _data_uri(buf.getvalue(), "image/png")


def avatar_uri(gender: str) -> str:
    """يقص الأفاتار حوالين الشكل نفسه عشان يبان كبير ومتوسّط جوه الدايرة."""
    img = Image.open(AVATARS[gender]).convert("RGB")
    mask = img.convert("L").point(lambda p: 255 if p < 140 else 0)
    bbox = mask.getbbox() or (0, 0, img.width, img.height)
    l, t, r, b = bbox
    cx, cy = (l + r) // 2, (t + b) // 2
    side = int(max(r - l, b - t) * 1.3)
    canvas = Image.new("RGB", (side, side), (255, 255, 255))
    canvas.paste(img, (-(cx - side // 2), -(cy - side // 2)))
    return _jpeg_uri(canvas.resize((600, 600)))


def photo_uri(raw: bytes) -> str:
    """صورة الموظف المرفوعة: قص مربع من المنتصف."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    return _jpeg_uri(ImageOps.fit(img, (600, 600), centering=(0.5, 0.35)))


# ---------------------------------------------------------------- الداشبورد
def _fmt(v: float) -> str:
    return f"{v:,.0f}"


def _pct(v: float, target: float) -> int:
    return int(math.floor(v / target * 100)) if target > 0 else 0


def _cheer(pct: int) -> str:
    if pct >= 100:
        return "تجاوز التارجت! أداء استثنائي يستحق التصفيق"
    if pct >= 80:
        return "على بُعد خطوة واحدة من التارجت، ما شاء الله"
    if pct >= 50:
        return "أداء قوي وإصرار واضح، كمّل يا بطل"
    return "الأعلى تحصيلًا هذه الفترة، والقادم أجمل"


def build_html(df: pd.DataFrame, company: str, period: str, target: float,
               currency: str, gender: str, photo: bytes | None = None,
               company_logo: tuple | None = None, date: datetime.date | None = None) -> str:
    """company_logo = (bytes, mime) أو None. photo = bytes أو None."""
    esc = html.escape
    date = date or datetime.date.today()
    headline, period_label = PERIODS[period]

    top = df.iloc[0]
    champ_pct = _pct(top.amount, target)
    champ_img = photo_uri(photo) if photo else avatar_uri(gender)
    ejada = ejada_uri()

    # شعار/اسم الشركة على جنب
    if company_logo:
        client_block = (f'<div class="client-logo"><img alt="{esc(company)}" '
                        f'src="{company_logo_uri(company_logo[0])}"></div>')
    else:
        client_block = f'<div class="client-logo text">{esc(company)}</div>'

    # أعلى 3
    medals = ["gold", "silver", "bronze"]
    rows = []
    for i, r in df.head(3).iterrows():
        p = _pct(r.amount, target)
        rows.append(f"""
        <li class="row {medals[i]}{' lead' if i == 0 else ''}">
          <span class="medal">{i + 1}</span>
          <div class="who"><b>{esc(r.emp)}</b>
            <span class="meter"><i style="width:{min(p, 100)}%"></i></span></div>
          <div class="val"><b>{_fmt(r.amount)}</b><small>{p}% من التارجت</small></div>
        </li>""")

    total = df.amount.sum()
    page = TEMPLATE
    for k, v in {
        "__TITLE__": esc(f"{headline} - {company}"),
        "__EJADA__": ejada,
        "__HEADLINE__": esc(headline),
        "__SUBTITLE__": esc(f"{period_label} بتاريخ {date.strftime('%d/%m/%Y')}"),
        "__COMPANY__": esc(company),
        "__CLIENT_BLOCK__": client_block,
        "__CHAMP_IMG__": champ_img,
        "__NAME__": esc(top.emp),
        "__AMOUNT__": _fmt(top.amount),
        "__CUR__": esc(currency),
        "__BAR__": str(min(champ_pct, 100)),
        "__PCT__": str(champ_pct),
        "__TARGET__": _fmt(target),
        "__CHEER__": esc(_cheer(champ_pct)),
        "__ROWS__": "".join(rows),
        "__COUNT__": str(len(df)),
        "__TOTAL__": _fmt(total),
        "__TOTAL_PCT__": str(_pct(total, target * len(df))),
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
:root{
  --ink:#050F26; --navy:#0B1D42; --royal:#1E3A6B; --sky:#6FA8FF;
  --gold:#F2B93B; --gold-hi:#FFE29A; --gold-lo:#B9801A; --ivory:#FFF8E8;
  --silver:#C9D3E6; --bronze:#D58F55;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{font-family:'Cairo','Segoe UI',Tahoma,sans-serif;color:var(--ivory);background:var(--ink);overflow:hidden}
img{display:block}

.stage{
  position:relative;height:100vh;min-height:560px;
  display:grid;grid-template-rows:auto 1fr auto;gap:2vh;padding:2vh 2.4vw;
  background:radial-gradient(110% 90% at 68% 42%,#1B3B7A 0%,#0B1D42 46%,#050F26 100%);
}
#confetti{position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:20}

/* ---------- الشريط العلوي ---------- */
.top{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:2vw;position:relative;z-index:2}
.ejada{background:#fff;border-radius:14px;padding:.8vh 1vw;box-shadow:0 6px 24px rgba(0,0,0,.35)}
.ejada img{height:13vh;max-height:140px;width:auto}
.heading{text-align:center}
.heading h1{font-size:clamp(1.8rem,5.6vh,3.6rem);font-weight:900;line-height:1.15;
  background:linear-gradient(180deg,var(--gold-hi),var(--gold) 55%,var(--gold-lo));
  -webkit-background-clip:text;background-clip:text;color:transparent;
  filter:drop-shadow(0 2px 14px rgba(242,185,59,.35))}
.heading p{margin-top:.4vh;font-size:clamp(.9rem,2.2vh,1.4rem);color:#B9C9E8;font-weight:500}
.company-pill{font-size:clamp(1rem,2.8vh,1.8rem);font-weight:700;padding:1vh 1.6vw;border-radius:999px;
  border:1.5px solid rgba(242,185,59,.55);background:rgba(255,255,255,.06);white-space:nowrap}

/* ---------- المنطقة الرئيسية ---------- */
.main{display:grid;grid-template-columns:1.9fr 1fr;gap:2vw;min-height:0;position:relative;z-index:2}

.hero{position:relative;display:grid;grid-template-columns:auto 1fr;align-items:center;gap:2.4vw;
  padding:3vh 2.4vw;border-radius:28px;min-height:0;overflow:hidden;
  background:linear-gradient(135deg,rgba(255,255,255,.10),rgba(255,255,255,.03));
  border:1.5px solid rgba(242,185,59,.5);
  box-shadow:0 0 0 6px rgba(242,185,59,.06),0 30px 80px rgba(0,0,0,.45),inset 0 0 80px rgba(242,185,59,.06)}
.rays{position:absolute;width:150vh;height:150vh;inset-inline-start:-38vh;top:50%;margin-top:-75vh;
  background:repeating-conic-gradient(from 0deg,rgba(255,226,154,.20) 0 6deg,transparent 6deg 18deg);
  -webkit-mask:radial-gradient(circle,#000 8%,transparent 62%);mask:radial-gradient(circle,#000 8%,transparent 62%);
  animation:spin 60s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

.champ{position:relative;width:min(34vh,21vw);aspect-ratio:1;margin-inline-start:3%}
.champ .ring{position:absolute;inset:0;border-radius:50%;padding:7px;
  background:conic-gradient(from 200deg,var(--gold-hi),var(--gold),var(--gold-lo),var(--gold-hi),var(--gold),var(--gold-hi));
  box-shadow:0 0 60px rgba(242,185,59,.55),0 18px 50px rgba(0,0,0,.5)}
.champ .ring img{width:100%;height:100%;border-radius:50%;object-fit:cover;background:#fff;border:5px solid #fff}
.crown{position:absolute;top:-13%;left:50%;width:34%;transform:translateX(-50%);z-index:3;
  filter:drop-shadow(0 6px 10px rgba(0,0,0,.45))}
.trophy{position:absolute;bottom:-5%;inset-inline-start:-14%;width:40%;z-index:3;
  filter:drop-shadow(0 10px 18px rgba(0,0,0,.5)) drop-shadow(0 0 22px rgba(242,185,59,.55));
  animation:float 4s ease-in-out infinite}
@keyframes float{50%{transform:translateY(-1.2vh)}}

.info{position:relative;z-index:2;min-width:0}
.tag{display:inline-block;font-weight:900;font-size:clamp(1rem,2.8vh,1.7rem);color:#2A1B00;
  padding:.5vh 1.3vw;border-radius:999px;background:linear-gradient(180deg,var(--gold-hi),var(--gold));
  box-shadow:0 6px 18px rgba(242,185,59,.4)}
.name{margin-top:1.6vh;font-size:clamp(2rem,7vh,4.6rem);font-weight:900;line-height:1.15;color:#fff;
  text-shadow:0 4px 24px rgba(0,0,0,.45);overflow-wrap:anywhere}
.amount{margin-top:1.4vh;display:flex;align-items:baseline;gap:.7vw;flex-wrap:wrap}
.amount .num{font-size:clamp(2.2rem,7.6vh,5rem);font-weight:900;line-height:1;color:var(--gold);
  text-shadow:0 0 30px rgba(242,185,59,.5);font-variant-numeric:tabular-nums}
.amount .cur{font-size:clamp(1rem,3vh,2rem);font-weight:700;color:var(--gold-hi)}

.progress{margin-top:2.4vh}
.bar{height:2.4vh;min-height:14px;border-radius:999px;background:rgba(255,255,255,.14);overflow:hidden;
  box-shadow:inset 0 2px 6px rgba(0,0,0,.4)}
.bar i{display:block;height:100%;border-radius:inherit;width:0;
  background:linear-gradient(90deg,var(--gold-lo),var(--gold),var(--gold-hi));
  box-shadow:0 0 18px rgba(242,185,59,.8);animation:fill 2.2s .4s cubic-bezier(.2,.8,.2,1) forwards}
@keyframes fill{to{width:__BAR__%}}
.bar-meta{margin-top:1vh;font-size:clamp(.95rem,2.6vh,1.6rem);color:#D6E1F7;font-weight:500}
.bar-meta b{font-size:1.5em;color:var(--gold-hi);font-weight:900;margin-inline-end:.4em}
.cheer{margin-top:1.6vh;font-size:clamp(1rem,2.8vh,1.8rem);font-weight:700;color:#fff}

/* ---------- لوحة أعلى 3 ---------- */
.board{display:flex;flex-direction:column;gap:2vh;padding:2.4vh 1.6vw;border-radius:28px;min-height:0;
  background:linear-gradient(180deg,rgba(255,255,255,.09),rgba(255,255,255,.03));
  border:1.5px solid rgba(159,180,217,.3);box-shadow:0 30px 80px rgba(0,0,0,.4)}
.client-logo{background:#fff;border-radius:18px;padding:1.6vh 1.6vw;display:flex;align-items:center;justify-content:center;
  height:17vh;flex:none;overflow:hidden;box-shadow:0 8px 24px rgba(0,0,0,.35)}
.client-logo img{width:100%;height:100%;object-fit:contain}
.client-logo.text{color:var(--royal);font-weight:900;font-size:clamp(1.3rem,4vh,2.6rem);text-align:center}
.board h3{font-size:clamp(1.1rem,3.2vh,2rem);font-weight:900;color:var(--gold-hi);text-align:center}
.rows{list-style:none;display:flex;flex-direction:column;gap:1.6vh;flex:1;min-height:0}
.row{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:1vw;flex:1;max-height:16vh;
  padding:1.2vh 1vw;border-radius:18px;background:rgba(5,15,38,.55);border:1px solid rgba(255,255,255,.1)}
.row.lead{background:linear-gradient(135deg,rgba(242,185,59,.28),rgba(242,185,59,.08));border-color:rgba(242,185,59,.7)}
.medal{width:clamp(36px,6.4vh,64px);aspect-ratio:1;border-radius:50%;display:grid;place-items:center;
  font-weight:900;font-size:clamp(1.1rem,3.2vh,2rem);color:#1d1400;box-shadow:0 4px 12px rgba(0,0,0,.4)}
.gold .medal{background:radial-gradient(circle at 30% 25%,var(--gold-hi),var(--gold) 60%,var(--gold-lo))}
.silver .medal{background:radial-gradient(circle at 30% 25%,#fff,var(--silver) 60%,#8392AE)}
.bronze .medal{background:radial-gradient(circle at 30% 25%,#F6C9A0,var(--bronze) 60%,#94582B)}
.who{min-width:0}
.who b{display:block;font-size:clamp(1rem,2.7vh,1.7rem);font-weight:700;overflow-wrap:anywhere;line-height:1.2}
.meter{display:block;margin-top:.8vh;height:.9vh;min-height:6px;border-radius:99px;background:rgba(255,255,255,.14);overflow:hidden}
.meter i{display:block;height:100%;background:linear-gradient(90deg,var(--sky),#B8D2FF);border-radius:inherit}
.gold .meter i{background:linear-gradient(90deg,var(--gold-lo),var(--gold-hi))}
.val{text-align:end}
.val b{display:block;font-size:clamp(1rem,2.8vh,1.8rem);font-weight:900;color:var(--gold);font-variant-numeric:tabular-nums}
.val small{font-size:clamp(.7rem,1.7vh,1rem);color:#B9C9E8}

/* ---------- الشريط السفلي ---------- */
.foot{display:flex;justify-content:space-between;align-items:center;gap:2vw;position:relative;z-index:2;
  padding:1.4vh 1.8vw;border-radius:18px;background:rgba(5,15,38,.6);border:1px solid rgba(159,180,217,.25);
  font-size:clamp(.85rem,2.2vh,1.4rem);color:#D6E1F7}
.foot b{color:var(--gold-hi);font-weight:900;font-size:1.2em;margin-inline-start:.35em}
.foot .stats{display:flex;gap:2.4vw;flex-wrap:wrap}
.foot .motto{font-weight:700;color:#fff}

/* ---------- شاشات صغيرة ---------- */
@media (max-width:900px){
  body{overflow:auto}
  .stage{height:auto}
  .main{grid-template-columns:1fr}
  .hero{grid-template-columns:1fr;justify-items:center;text-align:center;padding:4vh 4vw}
  .champ{width:min(60vw,320px)}
  .amount{justify-content:center}
  .top{grid-template-columns:1fr;justify-items:center}
  .foot{flex-direction:column;text-align:center}
}
@media (prefers-reduced-motion:reduce){
  .rays,.trophy{animation:none}
  .bar i{animation:none;width:__BAR__%}
}
</style>
</head>
<body>
<div class="stage">
  <canvas id="confetti"></canvas>

  <header class="top">
    <div class="ejada"><img src="__EJADA__" alt="إجادة لتحصيل الديون"></div>
    <div class="heading">
      <h1>__HEADLINE__</h1>
      <p>__SUBTITLE__</p>
    </div>
    <div class="company-pill">__COMPANY__</div>
  </header>

  <main class="main">
    <section class="hero">
      <div class="rays" aria-hidden="true"></div>
      <div class="champ">
        <svg class="crown" viewBox="0 0 120 72" aria-hidden="true">
          <defs><linearGradient id="gc" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#FFE29A"/><stop offset=".6" stop-color="#F2B93B"/><stop offset="1" stop-color="#B9801A"/>
          </linearGradient></defs>
          <path d="M8 62 L16 18 L42 42 L60 8 L78 42 L104 18 L112 62 Z" fill="url(#gc)"/>
          <rect x="8" y="60" width="104" height="10" rx="4" fill="url(#gc)"/>
          <circle cx="16" cy="15" r="6" fill="#FFE29A"/><circle cx="60" cy="6" r="7" fill="#FFE29A"/><circle cx="104" cy="15" r="6" fill="#FFE29A"/>
        </svg>
        <div class="ring"><img src="__CHAMP_IMG__" alt="__NAME__"></div>
        <svg class="trophy" viewBox="0 0 200 240" aria-hidden="true">
          <defs><linearGradient id="gt" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#FFE29A"/><stop offset=".5" stop-color="#F2B93B"/><stop offset="1" stop-color="#B9801A"/>
          </linearGradient></defs>
          <path d="M50 38 H24 C24 86 40 104 64 108" fill="none" stroke="url(#gt)" stroke-width="11" stroke-linecap="round"/>
          <path d="M150 38 H176 C176 86 160 104 136 108" fill="none" stroke="url(#gt)" stroke-width="11" stroke-linecap="round"/>
          <path d="M46 16 H154 V80 C154 126 128 152 100 152 C72 152 46 126 46 80 Z" fill="url(#gt)"/>
          <path d="M60 28 H76 V82 C76 112 86 128 98 138 C72 134 60 112 60 82 Z" fill="#fff" opacity=".35"/>
          <polygon points="100,46 109,67 132,69 114,84 120,106 100,94 80,106 86,84 68,69 91,67" fill="#FFF8E8"/>
          <rect x="86" y="150" width="28" height="36" fill="url(#gt)"/>
          <path d="M58 188 H142 L152 214 H48 Z" fill="url(#gt)"/>
          <rect x="40" y="212" width="120" height="20" rx="6" fill="#B9801A"/>
          <rect x="40" y="212" width="120" height="8" rx="4" fill="#F2B93B"/>
        </svg>
      </div>
      <div class="info">
        <span class="tag">أفضل موظف تحصيل</span>
        <h2 class="name">__NAME__</h2>
        <div class="amount"><span class="num">__AMOUNT__</span><span class="cur">__CUR__</span></div>
        <div class="progress">
          <div class="bar"><i></i></div>
          <p class="bar-meta"><b>__PCT__%</b> من التارجت البالغ __TARGET__ __CUR__</p>
        </div>
        <p class="cheer">__CHEER__</p>
      </div>
    </section>

    <aside class="board">
      __CLIENT_BLOCK__
      <h3>أعلى 3 في التحصيل</h3>
      <ul class="rows">__ROWS__</ul>
    </aside>
  </main>

  <footer class="foot">
    <div class="stats">
      <span>عدد المحصّلين<b>__COUNT__</b></span>
      <span>إجمالي التحصيل<b>__TOTAL__ __CUR__</b></span>
    </div>
    <div class="motto">كل تحصيل خطوة، وكل خطوة تصنع فرقًا للفريق كله</div>
  </footer>
</div>

<script>
(function(){
  if(window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var c=document.getElementById('confetti'), x=c.getContext('2d'), W, H, P=[];
  var colors=['#F2B93B','#FFE29A','#FFFFFF','#6FA8FF','#3F6FD1'];
  function size(){W=c.width=innerWidth;H=c.height=innerHeight}
  addEventListener('resize',size); size();
  function burst(n){
    for(var i=0;i<n;i++) P.push({x:Math.random()*W,y:-20-Math.random()*H*.35,
      vx:(Math.random()-.5)*3,vy:2+Math.random()*4,s:6+Math.random()*8,r:Math.random()*6.28,
      vr:(Math.random()-.5)*.3,c:colors[(Math.random()*colors.length)|0]});
  }
  function tick(){
    x.clearRect(0,0,W,H);
    for(var i=0;i<P.length;i++){var p=P[i];p.x+=p.vx;p.y+=p.vy;p.r+=p.vr;
      x.save();x.translate(p.x,p.y);x.rotate(p.r);x.fillStyle=p.c;x.fillRect(-p.s/2,-p.s/4,p.s,p.s/2);x.restore();}
    P=P.filter(function(p){return p.y<H+30});
    requestAnimationFrame(tick);
  }
  burst(240); setInterval(function(){burst(110)},15000); tick();
})();
</script>
</body>
</html>
"""
