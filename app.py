import datetime

import streamlit as st
import streamlit.components.v1 as components

from dashboard import PERIODS, avatar_uri, build_html, ejada_uri, load_data, photo_uri

st.set_page_config(page_title="نجم التحصيل | إجادة", page_icon="🏆", layout="wide")

def show_html(page: str, height: int = 820):
    """نسخ استريملت الجديدة بتستخدم st.iframe، والقديمة components.html."""
    if hasattr(st, "iframe"):
        st.iframe(page, height=height)
    else:
        components.html(page, height=height, scrolling=False)


NAVY, ROYAL, GOLD = "#0B1D42", "#1E3A6B", "#F2B93B"

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800;900&display=swap');
    .stApp, .stMarkdown, .stMarkdown p, label, h1, h2, h3, button, input, textarea {{font-family:'Cairo','Segoe UI',Tahoma,sans-serif;}}
    .stApp {{background:linear-gradient(180deg,#E6EDF9 0%,#F5F8FD 60%);}}
    header[data-testid="stHeader"] {{background:transparent;}}
    .block-container {{direction:rtl;text-align:right;max-width:1180px;padding-top:1.4rem;padding-bottom:3rem;}}

    .hero {{display:flex;align-items:center;gap:26px;padding:22px 30px;border-radius:24px;color:#fff;
            background:linear-gradient(120deg,{NAVY} 0%,{ROYAL} 62%,#2D55A6 100%);
            border-bottom:5px solid {GOLD};box-shadow:0 18px 40px rgba(11,29,66,.28);margin-bottom:1.2rem;}}
    .hero .logo {{background:#fff;border-radius:18px;padding:10px 14px;box-shadow:0 8px 22px rgba(0,0,0,.25);}}
    .hero .logo img {{height:96px;display:block;}}
    .hero h1 {{margin:0;padding:0;font-size:2.1rem;font-weight:900;line-height:1.25;color:#FFE29A;}}
    .hero p {{margin:.35rem 0 0;font-size:1.05rem;color:#D6E1F7;}}

    .step {{display:flex;align-items:center;gap:12px;font-weight:800;font-size:1.25rem;color:{NAVY};margin-bottom:.4rem;}}
    .step i {{font-style:normal;display:grid;place-items:center;width:34px;height:34px;border-radius:50%;
              background:{ROYAL};color:#FFE29A;font-weight:900;box-shadow:0 0 0 4px rgba(30,58,107,.14);}}

    [class*="st-key-card"] {{background:#fff;border-radius:20px;border:1px solid #D3DEF1 !important;
            box-shadow:0 10px 28px rgba(30,58,107,.08);padding:.6rem .9rem;margin-bottom:.9rem;}}
    div[data-testid="stFileUploaderDropzone"] {{background:#F3F7FE;border:2px dashed #9FB4D9;border-radius:14px;}}

    .stButton > button[kind="primary"] {{background:linear-gradient(120deg,{ROYAL},#2D55A6);color:#fff;border:0;
            border-radius:14px;font-weight:900;font-size:1.15rem;padding:.8rem 1rem;
            box-shadow:0 10px 24px rgba(30,58,107,.35);border-bottom:4px solid {GOLD};}}
    .stButton > button[kind="primary"]:hover {{filter:brightness(1.12);}}
    .stDownloadButton > button {{background:#fff;color:{ROYAL};border:2px solid {ROYAL};border-radius:14px;font-weight:800;padding:.7rem 1rem;}}
    .stDownloadButton > button:hover {{background:{ROYAL};color:#fff;}}

    .champ-card {{display:flex;align-items:center;gap:18px;padding:14px 18px;border-radius:16px;
            background:linear-gradient(120deg,#FFF6DC,#FFFFFF);border:1.5px solid {GOLD};}}
    .champ-card img {{width:84px;height:84px;border-radius:50%;object-fit:cover;border:3px solid {GOLD};background:#fff;}}
    .champ-card b {{font-size:1.3rem;color:{NAVY};}}
    .champ-card span {{color:{ROYAL};font-weight:700;}}
    </style>
    <div class="hero">
      <div class="logo"><img src="{ejada_uri()}" alt="إجادة لتحصيل الديون"></div>
      <div>
        <h1>داشبورد أفضل موظف تحصيل</h1>
        <p>ارفع ملف التحصيل واختار الفترة والتارجت، ويطلعلك داشبورد جاهز للعرض على شاشة الشركة.</p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------ 1) الإعدادات
with st.container(border=True, key="card_settings"):
    st.markdown('<div class="step"><i>1</i> إعدادات الداشبورد</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    company = c1.text_input("اسم الشركة اللي بيشتغل عليها الموظف", placeholder="مثال: Mobaily")
    period = c2.radio("الفترة", list(PERIODS.keys()), horizontal=True)
    c3, c4 = st.columns(2)
    target = c3.number_input("التارجت لكل موظف", min_value=1.0, value=100000.0, step=1000.0, format="%.0f")
    currency = c4.text_input("العملة", value="ر.س")

# ------------------------------------------------------------ 2) الملفات
with st.container(border=True, key="card_files"):
    st.markdown('<div class="step"><i>2</i> الملفات</div>', unsafe_allow_html=True)
    f1, f2 = st.columns(2)
    company_logo = f1.file_uploader("لوجو الشركة (اختياري، أي حجم)", type=["png", "jpg", "jpeg", "webp"])
    excel = f2.file_uploader("ملف الإكسيل: عمود الموظف + عمود التحصيل", type=["xlsx", "xls"])

# ------------------------------------------------------------ 3) الموظف
if excel:
    try:
        df = load_data(excel)
    except Exception as e:  # noqa: BLE001
        st.error(f"مشكلة في قراءة الملف: {e}")
        st.stop()
    top = df.iloc[0]

    with st.container(border=True, key="card_employee"):
        st.markdown('<div class="step"><i>3</i> الموظف الأعلى تحصيلًا</div>', unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        gender = g1.radio("نوع الموظف", ["ذكر", "أنثى"], horizontal=True)
        photo = g2.file_uploader("صورة الموظف (اختياري)", type=["png", "jpg", "jpeg", "webp"])
        try:
            preview = photo_uri(photo.getvalue()) if photo else avatar_uri(gender)
        except Exception:  # noqa: BLE001
            preview = avatar_uri(gender)
        st.markdown(
            f'<div class="champ-card"><img src="{preview}" alt="">'
            f'<div><b>{top.emp}</b><br><span>{top.amount:,.0f} {currency}</span></div></div>',
            unsafe_allow_html=True,
        )
        if not photo:
            st.caption("لو ماترفعتش صورة، بيتستخدم أفاتار حسب النوع.")
        with st.expander("ترتيب كل الموظفين"):
            st.dataframe(df.rename(columns={"emp": "الموظف", "amount": "التحصيل"}), use_container_width=True)

        if st.button("✨ إنشاء الداشبورد", type="primary", use_container_width=True):
            if not company.strip():
                st.warning("اكتب اسم الشركة الأول.")
            else:
                logo = (company_logo.getvalue(), company_logo.type) if company_logo else None
                st.session_state["html"] = build_html(
                    df, company.strip(), period, target, currency.strip(), gender,
                    photo=photo.getvalue() if photo else None, company_logo=logo,
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
    st.caption("افتح الملف المحمّل في المتصفح على شاشة الشركة واضغط F11 للعرض بملء الشاشة.")
