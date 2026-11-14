import base64
import io
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

st.set_page_config(page_title="LunaPilot", page_icon="🌙", layout="wide")

ASSETS = Path(__file__).parent / "assets"


@st.cache_resource
def img_uri(name, max_px):
    img = Image.open(ASSETS / name).convert("RGB")
    img.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


CSS = """
<style>
:root, .stApp {color-scheme: dark;}
.stApp {background:
  radial-gradient(ellipse at 15% 10%, rgba(90,60,200,.30) 0%, transparent 45%),
  radial-gradient(ellipse at 85% 30%, rgba(0,170,255,.20) 0%, transparent 50%),
  radial-gradient(ellipse at 50% 100%, rgba(180,60,200,.18) 0%, transparent 55%),
  radial-gradient(ellipse at 20% 0%, #0e1f52 0%, #070d24 45%, #02040d 100%) !important;}
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"], [data-testid="stBottom"] > div {background: transparent !important;}
.block-container {position: relative; z-index: 1;}
.stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label, .stApp li, .stApp span,
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] p, [data-testid="stCaptionContainer"],
[data-testid="stMetricLabel"], [data-testid="stMetricValue"], [data-testid="stToolbar"] *,
button[data-baseweb="tab"] p {color: #eaf2ff !important;}

/* stars */
.stApp::before, .stApp::after {content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;}
.stApp::before {
  background-image:
    radial-gradient(1.5px 1.5px at 20px 30px, #fff, transparent),
    radial-gradient(1px 1px at 90px 120px, #bfe9ff, transparent),
    radial-gradient(1.5px 1.5px at 160px 60px, #fff, transparent),
    radial-gradient(1px 1px at 230px 180px, #e6ff7a, transparent),
    radial-gradient(1.5px 1.5px at 300px 90px, #fff, transparent);
  background-size: 340px 220px; animation: twinkle 4s ease-in-out infinite alternate;}
.stApp::after {
  background-image:
    radial-gradient(1px 1px at 50px 70px, #fff, transparent),
    radial-gradient(2px 2px at 140px 150px, #9fd8ff, transparent),
    radial-gradient(1px 1px at 260px 40px, #fff, transparent),
    radial-gradient(1.5px 1.5px at 330px 200px, #fff, transparent);
  background-size: 410px 260px; animation: twinkle 6s ease-in-out infinite alternate-reverse;}

/* soft nebula (blurred, faint) */
.nebula {position: fixed; inset: -5%; z-index: 0; pointer-events: none; opacity: .22; mix-blend-mode: screen;
  filter: blur(7px) saturate(.85);
  background: url(__NEBULA__) 0% 0% / 140% auto; animation: drift 140s ease-in-out infinite alternate;}
/* soft sun glow, no hard edge */
.sunglow {position: fixed; left: -220px; top: -220px; width: 520px; height: 520px; z-index: 0; pointer-events: none;
  mix-blend-mode: screen; border-radius: 50%; filter: blur(18px);
  background: radial-gradient(circle, rgba(255,190,90,.65) 0%, rgba(255,130,50,.28) 38%, rgba(255,90,30,0) 70%);
  animation: breathe 9s ease-in-out infinite;}

/* shooting stars */
.shoot {position: fixed; top: -10px; width: 150px; height: 2px; z-index: 0; pointer-events: none; opacity: 0; border-radius: 2px;
  background: linear-gradient(90deg, #fff, rgba(255,255,255,0)); animation: shoot 9s linear infinite;}
.shoot.s1 {left: 75%; animation-delay: 2s;}
.shoot.s2 {left: 45%; top: 4%; animation-delay: 6s; animation-duration: 12s;}
.shoot.s3 {left: 95%; top: 22%; animation-delay: 9s; animation-duration: 14s;}

@keyframes twinkle {from {opacity: .3;} to {opacity: 1;}}
@keyframes drift {from {background-position: 0% 0%;} to {background-position: 100% 100%;}}
@keyframes breathe {0%, 100% {transform: scale(1); opacity: .65;} 50% {transform: scale(1.1); opacity: .9;}}
@keyframes pulse {0%, 100% {transform: scale(1);} 50% {transform: scale(1.04);}}
@keyframes spin {to {transform: rotate(360deg);}}
@keyframes kenburns {from {transform: scale(1);} to {transform: scale(1.12);}}
@keyframes floaty {0%, 100% {transform: translateY(0);} 50% {transform: translateY(-9px);}}
@keyframes shimmer {to {background-position: 300% center;}}
@keyframes rise {from {opacity: 0; transform: translateY(18px);} to {opacity: 1; transform: none;}}
@keyframes edgeglow {0%, 100% {box-shadow: 0 0 18px rgba(80,170,255,.15);} 50% {box-shadow: 0 0 34px rgba(120,200,255,.38);}}
@keyframes shoot {
  0% {opacity: 0; transform: translate(0, 0) rotate(-35deg);}
  2% {opacity: 1;}
  10% {opacity: 0; transform: translate(-480px, 340px) rotate(-35deg);}
  100% {opacity: 0; transform: translate(-480px, 340px) rotate(-35deg);}}

/* hero */
.hero {position: relative; height: 260px; border-radius: 20px; overflow: hidden; margin-bottom: 18px;
  border: 1px solid rgba(120,200,255,.25); animation: rise .9s ease-out both, edgeglow 6s ease-in-out infinite;}
.hero-bg {position: absolute; inset: 0; animation: kenburns 40s ease-in-out infinite alternate;
  background: linear-gradient(90deg, rgba(2,4,13,.92) 0%, rgba(2,4,13,.5) 60%, rgba(2,4,13,.2) 100%), url(__LANDER__) center/cover;}
.hero-text {position: absolute; left: 32px; top: 50%; transform: translateY(-50%); z-index: 2;}
.hero-text .title {font-size: 3.2rem; font-weight: 700; line-height: 1.1;
  background: linear-gradient(90deg, #eaf2ff, #9fe8ff, #d6ff3f, #9fe8ff, #eaf2ff); background-size: 300% auto;
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; color: transparent;
  filter: drop-shadow(0 0 14px rgba(120,200,255,.55)); animation: shimmer 9s linear infinite;}
.hero-text .tag {font-size: 1.15rem; color: #d6ff3f; margin-top: 6px;}
.hero-text .chip {display: inline-block; margin-top: 12px; padding: 4px 12px; border-radius: 999px; font-size: .8rem;
  border: 1px solid rgba(120,200,255,.5); color: #eaf2ff; background: rgba(255,255,255,.05);}
.orbit-system {position: absolute; right: 56px; top: 50%; width: 220px; height: 220px; margin-top: -110px; z-index: 2;
  animation: floaty 7s ease-in-out infinite;}
.orbit-system::before {content: ""; position: absolute; inset: 0; border-radius: 50%; border: 1px dashed rgba(120,200,255,.35);}
.earth {position: absolute; left: 50%; top: 50%; width: 130px; height: 130px; margin: -65px 0 0 -65px;
  object-fit: cover; clip-path: circle(41%); filter: drop-shadow(0 0 22px rgba(80,170,255,.85)); animation: pulse 8s ease-in-out infinite;}
.orbit {position: absolute; inset: 0; animation: spin 30s linear infinite;}
.moon {position: absolute; left: 50%; top: -30px; width: 60px; height: 60px; margin-left: -30px; object-fit: cover;
  clip-path: circle(31%); filter: drop-shadow(0 0 10px rgba(255,255,255,.5));}

/* cards */
.mission {position: relative; padding: 22px 26px; border-radius: 16px; margin: 12px 0 16px; border: 1px solid rgba(120,200,255,.25);
  background: linear-gradient(90deg, rgba(2,4,13,.92) 0%, rgba(2,4,13,.55) 100%), url(__MOONCLOSE__) right center/cover;
  animation: rise .8s ease-out both;}
.mission .label {font-size: .85rem; opacity: .8;}
.mission .big {font-size: 1.7rem; font-weight: 600; margin: 2px 0 6px;}
div[data-baseweb="select"] div, [data-testid="stDateInput"] div, [data-testid="stDateInput"] input,
[data-testid="stChatInput"] textarea {background-color: rgba(15,27,68,.92) !important; color: #eaf2ff !important;
  border-color: rgba(120,200,255,.35) !important;}
div[data-baseweb="select"] svg, [data-testid="stDateInput"] svg {fill: #eaf2ff !important;}
[data-testid="stMetric"], [data-testid="stChatMessage"] {background: rgba(255,255,255,.06);
  border: 1px solid rgba(120,200,255,.25); border-radius: 14px; padding: 14px 18px;
  animation: rise .8s ease-out both; transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease;}
[data-testid="stMetric"]:hover {transform: translateY(-4px); border-color: rgba(214,255,63,.6);
  box-shadow: 0 10px 28px rgba(80,170,255,.25);}
[data-testid="stPlotlyChart"] {animation: rise 1s ease-out both;}
.note {padding: 14px 18px; border-radius: 12px; margin: 8px 0 16px; background: rgba(255,255,255,.07);
  border: 1px solid rgba(120,200,255,.35); animation: rise .7s ease-out both;}
.note.warn {border-color: rgba(214,255,63,.6);}
.note, .note * {color: #eaf2ff !important;}
button[data-baseweb="tab"] {transition: transform .2s ease;}
button[data-baseweb="tab"]:hover {transform: translateY(-2px);}
@media (max-width: 800px) {.orbit-system {display: none;} .hero-text .title {font-size: 2.2rem;}}
@media (prefers-reduced-motion: reduce) {* {animation: none !important;}}
</style>
"""
CSS = (
    CSS.replace("__NEBULA__", img_uri("nebula.jpg", 1600))
    .replace("__LANDER__", img_uri("lander.jpg", 1280))
    .replace("__MOONCLOSE__", img_uri("moon_close.jpg", 800))
)
st.markdown(
    CSS + '<div class="nebula"></div><div class="sunglow"></div>'
    '<div class="shoot s1"></div><div class="shoot s2"></div><div class="shoot s3"></div>',
    unsafe_allow_html=True,
)

HERO = """
<div class="hero"><div class="hero-bg"></div>
<div class="hero-text"><div class="title">LunaPilot</div>
<div class="tag">Land where the Sun never sets.</div>
<span class="chip">NASA Space Apps Challenge 2026</span></div>
<div class="orbit-system"><img class="earth" src="__EARTH__"><div class="orbit"><img class="moon" src="__MOON__"></div></div>
</div>
"""
st.markdown(HERO.replace("__EARTH__", img_uri("earth.jpg", 400)).replace("__MOON__", img_uri("moon.jpg", 300)),
            unsafe_allow_html=True)


def note(text, kind="info"):
    st.markdown(f'<div class="note {kind}">{text}</div>', unsafe_allow_html=True)


sites = ["Site A (demo)", "Site B (demo)", "Site C (demo)"]

# FAKE data, only to test the layout
times = pd.date_range("2029-03-01", periods=240, freq="3h")
sun = 1.5 * np.sin(np.linspace(0, 8 * np.pi, len(times)))
earth = 5 * np.sin(np.linspace(0, 4 * np.pi, len(times)) + 1)


def make_chart(values, title, color):
    fig = go.Figure(go.Scatter(x=times, y=values, mode="lines", line=dict(color=color, width=3)))
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,.5)")
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=title, font=dict(color="#eaf2ff", size=18)),
        yaxis_title="Elevation (degrees)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#eaf2ff"),
    )
    fig.update_xaxes(gridcolor="rgba(120,200,255,.15)", color="#eaf2ff")
    fig.update_yaxes(gridcolor="rgba(120,200,255,.15)", color="#eaf2ff")
    return fig


tab1, tab2, tab3, tab4 = st.tabs(["Explorer", "Compare", "Copilot", "About and credits"])

with tab1:
    note("Layout demo with FAKE data. Real numbers will come from the engine.", "warn")
    site = st.selectbox("Choose a landing site", sites)
    col1, col2 = st.columns(2)
    start = col1.date_input("Start date")
    end = col2.date_input("End date")
    if end < start:
        note("End date is before the start date. Please fix the dates.", "warn")
        days = 0
    else:
        days = (end - start).days + 1
    st.markdown(
        f'<div class="mission"><div class="label">Selected site</div><div class="big">{site}</div>'
        f'<div class="label">Window: {start} to {end} ({days} days)</div></div>',
        unsafe_allow_html=True,
    )
    left, right = st.columns(2)
    left.plotly_chart(make_chart(sun, "Sun elevation", "#d6ff3f"), width="stretch", theme=None)
    right.plotly_chart(make_chart(earth, "Earth elevation", "#3fe0ff"), width="stretch", theme=None)

    sunlit = float((sun > 0).mean())
    earth_visible = float((earth > 0).mean())
    power_score = sunlit * 100
    comms_score = earth_visible * 100
    overall = 0.5 * power_score + 0.5 * comms_score

    st.subheader("Score")
    c1, c2, c3 = st.columns(3)
    c1.metric("Power score", f"{power_score:.1f}")
    c2.metric("Comms score", f"{comms_score:.1f}")
    c3.metric("Overall", f"{overall:.1f}")
    st.caption(
        "Power = sunlit fraction x 100. Comms = Earth visible fraction x 100. "
        "Overall = 0.5 x power + 0.5 x comms."
    )
    data = pd.DataFrame({"time": times, "sun_elevation_deg": sun, "earth_elevation_deg": earth})
    st.download_button("Download chart data (CSV, demo)", data.to_csv(index=False), "lunapilot_demo.csv", "text/csv")
    note("Limitation: flat horizon, no terrain shadows.")

with tab2:
    note("Demo table with FAKE numbers. The real comparison will use the engine.", "warn")
    demo = pd.DataFrame(
        {
            "Site": sites,
            "Power score (demo)": [49.6, 61.2, 44.8],
            "Comms score (demo)": [50.4, 38.9, 57.3],
        }
    )
    demo["Overall (demo)"] = 0.5 * demo["Power score (demo)"] + 0.5 * demo["Comms score (demo)"]
    st.dataframe(demo, width="stretch", hide_index=True)

with tab3:
    note("Demo mode. The real copilot will call our tools and use only numbers computed by our code.", "warn")
    st.caption("Example questions: Which site has the longest sunlight? Which site has the best Earth link? "
               "Compare two sites. What is the longest dark period? How is the score calculated?")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    prompt = st.chat_input("Ask about a site or a date range")
    if prompt:
        reply = (
            "**Answer:** Demo mode, no engine connected yet.\n\n"
            "**Numbers:** none (the copilot will only show numbers returned by our tools).\n\n"
            "**Caveat:** flat horizon, no terrain shadows."
        )
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

with tab4:
    st.subheader("About LunaPilot")
    st.write("LunaPilot helps compare Moon south pole landing sites and dates, "
             "showing Sun and Earth elevation, power potential and communication windows.")
    st.subheader("Use of AI")
    st.write("AI tools (Claude) helped write parts of the interface code. Numbers and checks are done by our own code and team.")
    st.subheader("Image credits (Pixabay)")
    st.write("Earth and Sun: wikiimages. Moon: jwvein and bellergy. Nebula: timrael. Lunar landing: cristianis. "
             "Links and licenses are listed in docs/credits.md.")
    note("Limitation: flat horizon, no terrain shadows.")