import datetime

import streamlit as st
import streamlit.components.v1 as components

from dashboard import MODES, PERIODS, build_html, ejada_white_uri, load_workbook

st.set_page_config(page_title="نجم التحصيل | إجادة", page_icon="🏆", layout="wide")


def show_html(page: str, height: int = 820):
    """نسخ استريملت الجديدة بتستخدم st.iframe، والقديمة components.html."""
    if hasattr(st, "iframe"):
        st.iframe(page, height=height)
    else:
        components.html(page, height=height, scrolling=False)


NAVY, DEEP = "#13204F", "#0A1330"

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800;900&display=swap');
    .stApp, .stMarkdown, .stMarkdown p, label, h1, h2, h3, button, input, textarea {{font-family:'Cairo','Segoe UI',Tahoma,sans-serif;}}
    .stApp {{background:linear-gradient(180deg,#E4E9F6 0%,#F5F7FC 60%);}}
    header[data-testid="stHeader"] {{background:transparent;}}
    .block-container {{direction:rtl;text-align:right;max-width:1180px;padding-top:1.4rem;padding-bottom:3rem;}}

    .hero {{display:flex;align-items:center;gap:26px;padding:20px 30px;border-radius:24px;color:#fff;position:relative;overflow:hidden;
            background:linear-gradient(135deg,#1A2C6E 0%,{NAVY} 50%,{DEEP} 100%);
            box-shadow:0 18px 40px rgba(10,19,48,.30);margin-bottom:1.2rem;}}
    .hero::after {{content:"";position:absolute;left:-40px;top:-60px;width:220px;height:220px;border-radius:50%;background:rgba(255,255,255,.06);}}
    .hero img {{height:100px;display:block;}}
    .hero h1 {{margin:0;padding:0;font-size:2.1rem;font-weight:900;line-height:1.25;color:#fff;}}
    .hero p {{margin:.35rem 0 0;font-size:1.05rem;color:#C7D4F0;}}
    .dm {{display:inline-block;width:14px;height:14px;background:#fff;clip-path:polygon(50% 0,100% 50%,50% 100%,0 50%);margin-inline-end:3px;}}

    .step {{display:flex;align-items:center;gap:12px;font-weight:800;font-size:1.25rem;color:{NAVY};margin-bottom:.4rem;}}
    .step i {{font-style:normal;display:grid;place-items:center;width:34px;height:34px;border-radius:50%;
              background:{NAVY};color:#fff;font-weight:900;box-shadow:0 0 0 4px rgba(19,32,79,.14);}}

    [class*="st-key-card"] {{background:#fff;border-radius:20px;border:1px solid #D3DBEE !important;
            box-shadow:0 10px 28px rgba(19,32,79,.08);padding:.6rem .9rem;margin-bottom:.9rem;}}
    div[data-testid="stFileUploaderDropzone"] {{background:#F2F5FC;border:2px dashed #9FB0D6;border-radius:14px;}}

    .stButton > button[kind="primary"] {{background:linear-gradient(120deg,{NAVY},#2A3F8C);color:#fff;border:0;
            border-radius:14px;font-weight:900;font-size:1.15rem;padding:.8rem 1rem;box-shadow:0 10px 24px rgba(19,32,79,.35);}}
    .stButton > button[kind="primary"]:hover {{filter:brightness(1.15);}}
    .stDownloadButton > button {{background:#fff;color:{NAVY};border:2px solid {NAVY};border-radius:14px;font-weight:800;padding:.7rem 1rem;}}
    .stDownloadButton > button:hover {{background:{NAVY};color:#fff;}}

    .co-top {{display:flex;align-items:center;gap:14px;padding:10px 14px;border-radius:14px;background:#F2F5FC;border:1px solid #D3DBEE;}}
    .co-top b {{font-size:1.15rem;color:{NAVY};}}
    .co-top span {{color:#4A5A8A;font-weight:600;}}
    </style>
    <div class="hero">
      <img src="{ejada_white_uri()}" alt="إجادة لتحصيل الديون">
      <div>
        <h1>داشبورد أفضل موظف تحصيل</h1>
        <p>ارفع ملف الإكسيل (شيت لكل شركة)، حدّد التارجت، واختار طريقة العرض على شاشة الشركة.</p>
        <span class="dm"></span><span class="dm"></span><span class="dm"></span><span class="dm"></span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------ 1) الإعدادات
with st.container(border=True, key="card_settings"):
    st.markdown('<div class="step"><i>1</i> إعدادات العرض</div>', unsafe_allow_html=True)
    a, b = st.columns(2)
    period = a.radio("الفترة", list(PERIODS.keys()), horizontal=True, index=1)
    mode_label = b.radio("طريقة العرض", list(MODES.keys()), horizontal=True)
    mode = MODES[mode_label]
    c1, c2, c3 = st.columns(3)
    currency = c1.text_input("العملة", value="ر.س")
    top_n = c2.slider("عدد الموظفين في عرض التقدم", 5, 30, 15, disabled=(mode == "finale"))
    confetti = c3.checkbox("كونفيتي هادي عند عرض الفائزين", value=False, disabled=(mode == "progress"))

# ------------------------------------------------------------ 2) الملف
with st.container(border=True, key="card_file"):
    st.markdown('<div class="step"><i>2</i> ملف الإكسيل</div>', unsafe_allow_html=True)
    excel = st.file_uploader(
        "كل شيت = شركة (اسم الشيت هو اسم الشركة)، وفي كل شيت عمودين: الموظف + التحصيل",
        type=["xlsx", "xls"],
    )

# ------------------------------------------------------------ 3) الشركات
if excel:
    try:
        sheets, bad = load_workbook(excel)
    except Exception as e:  # noqa: BLE001
        st.error(f"مشكلة في قراءة الملف: {e}")
        st.stop()
    for sh, why in bad.items():
        st.warning(f"الشيت «{sh}» اتجاهل: {why}")
    if not sheets:
        st.error("مفيش شيت صالح في الملف.")
        st.stop()

    st.markdown('<div class="step" style="margin-top:.6rem"><i>3</i> الشركات والتارجت</div>', unsafe_allow_html=True)
    st.caption(f"لقيت {len(sheets)} شركة. اكتب التارجت لكل شركة (والصورة اختيارية للموظف الأعلى).")

    inputs = {}
    for i, (name, df) in enumerate(sheets.items()):
        top = df.iloc[0]
        with st.container(border=True, key=f"card_co_{i}"):
            st.markdown(
                f'<div class="co-top"><b>{name}</b><span>الأعلى: {top.emp} · {top.amount:,.0f} {currency}'
                f' · {len(df)} موظف</span></div>',
                unsafe_allow_html=True,
            )
            t_col, p_col = st.columns(2)
            target = t_col.number_input(
                "التارجت لكل موظف", min_value=1.0, value=None, step=1000.0, format="%.0f",
                placeholder="اكتب التارجت", key=f"target_{i}",
            )
            photo = p_col.file_uploader("صورة الموظف الأعلى (اختياري)", type=["png", "jpg", "jpeg", "webp"], key=f"photo_{i}")
            inputs[name] = (df, target, photo)

    if st.button("✨ إنشاء الداشبورد", type="primary", use_container_width=True):
        missing = [n for n, (_, t, _) in inputs.items() if not t]
        if missing:
            st.warning("لازم تكتب التارجت للشركات دي: " + "، ".join(missing))
        else:
            companies = [
                {"name": n, "df": df, "target": float(t), "photo": ph.getvalue() if ph else None}
                for n, (df, t, ph) in inputs.items()
            ]
            st.session_state["html"] = build_html(
                companies, period, mode, currency.strip(), top_n=top_n, confetti=confetti,
            )
            st.session_state["fname"] = f"top_collector_{datetime.date.today():%Y%m%d}.html"

if "html" in st.session_state:
    st.markdown('<div class="step" style="margin-top:.8rem"><i>★</i> الداشبورد</div>', unsafe_allow_html=True)
    show_html(st.session_state["html"], 820)
    st.download_button(
        "⬇️ تحميل الداشبورد (HTML) للعرض على الشاشة",
        data=st.session_state["html"],
        file_name=st.session_state["fname"],
        mime="text/html",
        use_container_width=True,
    )
    st.caption("افتح الملف المحمّل في المتصفح على شاشة الشركة واضغط F11. للتنقل بين الشركات: الأسهم أو اضغط على الاسم، أو أسهم الكيبورد.")
