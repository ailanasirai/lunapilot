import base64
import io
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.geometry import analyze_site, load_sites  # noqa: E402

st.set_page_config(page_title="LunaPilot", page_icon="🌙", layout="wide")

ASSETS = Path(__file__).parent / "assets"
MIN_D, MAX_D = date(1900, 1, 1), date(2050, 1, 1)  # kernel coverage (from David)
LIMITATION = "Limitation: flat horizon, no terrain shadows. Scores can read 0% or 100% because terrain is ignored."


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

.nebula {position: fixed; inset: -5%; z-index: 0; pointer-events: none; opacity: .22; mix-blend-mode: screen;
  filter: blur(7px) saturate(.85);
  background: url(__NEBULA__) 0% 0% / 140% auto; animation: drift 140s ease-in-out infinite alternate;}
.sunglow {position: fixed; left: -220px; top: -220px; width: 520px; height: 520px; z-index: 0; pointer-events: none;
  mix-blend-mode: screen; border-radius: 50%; filter: blur(18px);
  background: radial-gradient(circle, rgba(255,190,90,.65) 0%, rgba(255,130,50,.28) 38%, rgba(255,90,30,0) 70%);
  animation: breathe 9s ease-in-out infinite;}

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


# ---------- engine wrappers ----------
@st.cache_resource
def get_sites():
    return load_sites()


@st.cache_data(show_spinner=False)
def run(site_id, start, end, step):
    return analyze_site(site_id, start, end, step)


def scores(m, w_power):
    power = m["sunlit_fraction"] * 100
    comms = m["earth_visible_fraction"] * 100
    return power, comms, w_power * power + (1 - w_power) * comms


def site_rows(sites, start, end, step, w):
    rows = []
    for s in sites:
        m = run(s["id"], str(start), str(end), step)["metrics"]
        p, c, o = scores(m, w)
        rows.append({
            "Site": s["name"],
            "Power score": p,
            "Comms score": c,
            "Overall": o,
            "Both visible %": m["both_fraction"] * 100,
            "Longest dark (h)": m["longest_dark_hours"],
        })
    return pd.DataFrame(rows)


def make_chart(times, values, title, color):
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


def md_table(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(f"{v:.1f}" if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(lines)


def copilot_answer(q, df, window, w):
    """Tool-based answers. Every number comes from the engine results in df."""
    ql = q.lower()
    caveat = "Flat horizon, no terrain shadows. Scores are shares of time above the horizon."
    named = [n for n in df["Site"] if n.lower() in ql]
    sub = df[df["Site"].isin(named)] if named else df

    def reply(answer, table=None):
        out = f"**Answer:** {answer}\n\n"
        out += f"**Numbers ({window}):**\n\n{md_table(table)}\n\n" if table is not None else "**Numbers:** none needed.\n\n"
        return out + f"**Caveat:** {caveat}"

    if any(k in ql for k in ("formula", "calculat", "score work", "how is the score")):
        return reply(
            f"Power score = share of time the Sun is above the horizon x 100. Comms score = share of time Earth "
            f"is above the horizon x 100. Overall = {w:.2f} x power + {1 - w:.2f} x comms."
        )
    if any(k in ql for k in ("dark", "night", "shadow")):
        parts = "; ".join(f"{r['Site']}: {r['Longest dark (h)']:.0f} hours" for _, r in sub.iterrows())
        return reply(f"Longest continuous period without sunlight: {parts}.", sub[["Site", "Longest dark (h)"]])
    if "compare" in ql:
        return reply("Side by side comparison for the selected window.", sub)
    if any(k in ql for k in ("earth", "comm", "link", "signal")):
        b = df.loc[df["Comms score"].idxmax()]
        return reply(f"{b['Site']} has the best Earth link, with a comms score of {b['Comms score']:.1f}.",
                     df[["Site", "Comms score"]])
    if any(k in ql for k in ("sun", "power", "light", "energy", "solar")):
        b = df.loc[df["Power score"].idxmax()]
        return reply(f"{b['Site']} has the most sunlight, with a power score of {b['Power score']:.1f}.",
                     df[["Site", "Power score"]])
    return reply("I need a bit more detail. Ask about sunlight (power), Earth link (comms), the longest dark "
                 "period, comparing sites, or how the score is calculated.")


# ---------- load sites ----------
sites = get_sites()
site_ids = [s["id"] for s in sites]
by_id = {s["id"]: s for s in sites}

tab1, tab2, tab3, tab4 = st.tabs(["Explorer", "Compare", "Copilot", "About and credits"])
df_all = None
window = ""
w = 0.5

with tab1:
    site_id = st.selectbox("Choose a landing site", site_ids, format_func=lambda i: by_id[i]["name"])
    c1, c2, c3 = st.columns(3)
    start = c1.date_input("Start date", value=date(2029, 7, 1), min_value=MIN_D, max_value=MAX_D)
    end = c2.date_input("End date", value=date(2029, 7, 31), min_value=MIN_D, max_value=MAX_D)
    step = c3.selectbox("Time step (minutes)", [30, 60, 120], index=1)
    w = st.slider("Weight on power (the rest goes to comms)", 0, 100, 50) / 100

    ok = end >= start and (end - start).days <= 366
    if end < start:
        note("End date is before the start date. Please fix the dates.", "warn")
    elif not ok:
        note("Please choose a window of at most 366 days.", "warn")

    if ok:
        window = f"{start} to {end}"
        try:
            with st.spinner("Computing Sun and Earth positions (the first run downloads about 18 MB of NASA kernels)..."):
                res = run(site_id, str(start), str(end), step)
                df_all = site_rows(sites, start, end, step, w)
        except Exception as e:  # keep the app alive, show a clear message
            res = None
            note(f"The engine could not run: {e}", "warn")

        if res is not None:
            s = by_id[site_id]
            st.markdown(
                f'<div class="mission"><div class="label">Selected site</div><div class="big">{s["name"]}</div>'
                f'<div class="label">Latitude {s["latitude"]}, longitude {s["longitude"]} | Window: {window}</div></div>',
                unsafe_allow_html=True,
            )
            times = pd.to_datetime(res["time"])
            sun = res["sun_elevation_deg"]
            earth = res["earth_elevation_deg"]
            left, right = st.columns(2)
            left.plotly_chart(make_chart(times, sun, "Sun elevation", "#d6ff3f"), width="stretch", theme=None)
            right.plotly_chart(make_chart(times, earth, "Earth elevation", "#3fe0ff"), width="stretch", theme=None)
            st.caption(
                f"Sun elevation ranged from {min(sun):.2f} to {max(sun):.2f} degrees. "
                f"Earth elevation ranged from {min(earth):.2f} to {max(earth):.2f} degrees."
            )

            m = res["metrics"]
            p, c, o = scores(m, w)
            st.subheader("Score")
            a1, a2, a3 = st.columns(3)
            a1.metric("Power score", f"{p:.1f}")
            a2.metric("Comms score", f"{c:.1f}")
            a3.metric("Overall", f"{o:.1f}")
            b1, b2, b3, b4 = st.columns(4)
            b1.metric("Sunlit time", f"{m['sunlit_fraction'] * 100:.1f}%")
            b2.metric("Earth visible", f"{m['earth_visible_fraction'] * 100:.1f}%")
            b3.metric("Both visible", f"{m['both_fraction'] * 100:.1f}%")
            b4.metric("Longest dark", f"{m['longest_dark_hours']:.0f} h")
            st.caption(
                "Power = sunlit fraction x 100. Comms = Earth visible fraction x 100. "
                f"Overall = {w:.2f} x power + {1 - w:.2f} x comms."
            )
            data = pd.DataFrame({"time": times, "sun_elevation_deg": sun, "earth_elevation_deg": earth})
            st.download_button("Download chart data (CSV)", data.to_csv(index=False),
                               f"lunapilot_{site_id}_{start}_{end}.csv", "text/csv")
    note(LIMITATION)

with tab2:
    if df_all is None:
        note("Choose a valid window in the Explorer tab first.", "warn")
    else:
        picked = st.multiselect("Sites to compare", list(df_all["Site"]), default=list(df_all["Site"]))
        view = df_all[df_all["Site"].isin(picked)]
        st.caption(f"Window: {window}, step {step} minutes")
        st.dataframe(view.round(1), width="stretch", hide_index=True)
        fig = go.Figure()
        fig.add_bar(x=view["Site"], y=view["Power score"], name="Power score", marker_color="#d6ff3f")
        fig.add_bar(x=view["Site"], y=view["Comms score"], name="Comms score", marker_color="#3fe0ff")
        fig.update_layout(barmode="group", template="plotly_dark", yaxis_range=[0, 100],
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#eaf2ff"))
        st.plotly_chart(fig, width="stretch", theme=None)
    note(LIMITATION)

with tab3:
    note("Tool mode: every answer is built from numbers our engine computed for the window selected in the Explorer tab. "
         "The language model layer comes next.", "warn")
    st.caption("Try: Which site has the longest sunlight? Which site has the best Earth link? Compare two sites. "
               "What is the longest dark period at Nobile Rim 2? How is the score calculated?")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    prompt = st.chat_input("Ask about a site or a date range")
    if prompt:
        if df_all is None:
            reply = "**Answer:** I need a valid date window first. Please set it in the Explorer tab."
        else:
            reply = copilot_answer(prompt, df_all, window, w)
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

with tab4:
    st.subheader("About LunaPilot")
    st.write("LunaPilot helps compare Moon south pole landing sites and dates, "
             "showing Sun and Earth elevation, power potential and communication windows.")
    st.subheader("How it works")
    st.write("For each time step the engine takes the Sun and Earth positions from NASA JPL ephemerides, "
             "converts them to the Moon body frame, and computes the elevation above a flat local horizon "
             "at the chosen site. Scores are shares of time the Sun or Earth is above the horizon.")
    st.subheader("Data sources")
    st.write("Ephemerides and Moon orientation kernels: NASA JPL / NAIF (downloaded at first run). "
             "Computation: Skyfield. Region names: NASA Artemis III candidate region announcement. "
             "Coordinates are approximate region centres taken from the papers below.")
    for s in sites:
        st.write(f"{s['name']}: {s['source']}")
    st.subheader("Use of AI")
    st.write("AI tools (Claude) helped write parts of the code. Numbers are computed by our own engine and checked by the team.")
    st.subheader("Image credits (Pixabay)")
    st.write("Earth and Sun: wikiimages. Moon: jwvein and bellergy. Nebula: timrael. Lunar landing: cristianis. "
             "Links and licenses are listed in docs/credits.md.")
    note(LIMITATION)