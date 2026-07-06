"""
IngreLens AI — Shared UI: Sage & Stone palette + real logo.
"""
import streamlit as st
import base64
import hashlib
import re
from pathlib import Path

from backend.db import database as db

# ── Cinematic near-black + chartreuse/jade tokens (matches reference artifact) ──
SAGE = {
    "darkest":  "#0b120f",   # Void background anchor — near-black (artifact bg-void)
    "dark":     "#101a15",   # Sidebar/hero/footer gradient mid — near-black stage
    "mid":      "#2fb586",   # Primary interactive + Vegan verdict — jade green
    "accent":   "#c8ff5b",   # Buttons, highlights, glow — chartreuse lime
    "teal":     "#6fae95",   # Muted secondary accent — soft jade-gray
    "light":    "#d9f7c2",   # Light chartreuse tint — badge borders, shimmer text
    "pale":     "rgba(200,255,91,0.16)",  # Subtle glass borders / chip fills
    "cream":    "#0b120f",   # Page background — near-black
    "offwhite": "#16211b",   # Card surfaces — dark panel
    "stone":    "#9fb6aa",   # Secondary text — muted sage-gray
    "charcoal": "#eaf2ed",   # Body text — near-white
}

BRAND_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html,body,[class*="css"]{{font-family:'Inter',sans-serif!important}}
#MainMenu,footer,.stDeployButton{{display:none!important}}
/* Native Streamlit header reserves height at the very top of the viewport
   even fully transparent — collapse it so the custom nav below sits flush
   at the top with no gap above it. */
header[data-testid="stHeader"]{{background:transparent;height:0;min-height:0}}
header[data-testid="stHeader"] *{{display:none!important}}
.main .block-container{{padding:1.75rem 2.25rem 3.5rem;max-width:1240px}}

/* ── ANIMATIONS ── */
@keyframes ilFadeUp{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes ilGlow{{0%,100%{{opacity:0.55}}50%{{opacity:0.9}}}}

/* ── NATIVE SIDEBAR — replaced by top navigation, fully hidden ── */
[data-testid="stSidebar"]{{display:none!important}}
[data-testid="collapsedControl"]{{display:none!important}}
.main .block-container{{padding-top:0.5rem}}
/* Newer Streamlit builds rename the block container's testid — target it
   directly so no top padding survives regardless of which class the
   installed version uses. */
[data-testid="stMainBlockContainer"]{{padding-top:0!important}}

/* ── TOP NAVIGATION ── */
.st-key-il_topnav{{
  position:sticky;top:0;z-index:998;margin:-0.5rem -0.25rem 1rem;
  padding:10px 18px;background:rgba(11,18,15,0.82);
  backdrop-filter:blur(14px) saturate(160%);-webkit-backdrop-filter:blur(14px) saturate(160%);
  border-bottom:1px solid rgba(232,255,214,0.08);
}}
.st-key-il_topnav [data-testid="stHorizontalBlock"]{{align-items:center}}
.il-topnav-brand{{display:flex;align-items:center;gap:12px;white-space:nowrap;padding-left:6px;cursor:pointer}}
/* Brand/logo doubles as the Home link. The real st.button is kept in the
   DOM (so a click can mark Home as "entered" and land on Quick Actions
   directly) but visually collapsed — clicks are forwarded to it from the
   visible logo via JS (below), since Streamlit's own fit-content sizing
   on the button kept winning over any inset:0 overlay attempt. */
.st-key-il_topnav_brand_link{{position:relative}}
.st-key-il_topnav_brand_link button{{
  position:absolute;top:0;left:0;opacity:0;pointer-events:none;
}}
.il-topnav-word{{font-weight:800;font-size:1.02rem;letter-spacing:-0.01em;color:{SAGE['charcoal']}}}
.il-topnav-word b{{color:{SAGE['mid']}}}

.st-key-il_topnav_links [data-testid="stPageLink"]{{
  border-radius:10px!important;padding:6px 3px!important;
  transition:background .22s ease, transform .22s ease!important;
}}
.st-key-il_topnav_links [data-testid="stPageLink"]:hover{{
  background:rgba(232,255,214,0.06)!important;transform:translateY(-1px)!important;
}}
.st-key-il_topnav_links [data-testid="stPageLink"][aria-current="page"]{{
  background:rgba(47,181,134,0.14)!important;
  box-shadow:inset 0 -2px 0 {SAGE['mid']}!important;
}}
.st-key-il_topnav_links [data-testid="stPageLink"] p{{
  font-size:1rem!important;font-weight:700!important;color:{SAGE['stone']}!important;
  white-space:nowrap!important;
}}
.st-key-il_topnav_links [data-testid="stPageLink"][aria-current="page"] p{{color:{SAGE['charcoal']}!important}}
/* Profile dropdown trigger — same transparent pill look as the page-link items beside it */
.st-key-il_topnav_links [data-testid="stPopoverButton"]{{
  border-radius:10px!important;padding:6px 3px!important;background:transparent!important;
  border:none!important;box-shadow:none!important;font-size:0.9rem!important;font-weight:700!important;
  color:{SAGE['stone']}!important;transition:background .22s ease, transform .22s ease!important;
}}
.st-key-il_topnav_links [data-testid="stPopoverButton"]:hover{{
  background:rgba(232,255,214,0.06)!important;transform:translateY(-1px)!important;
}}

/* Mobile hamburger toggle — hidden on desktop, shown under the breakpoint */
.st-key-il_topnav_toggle{{display:none}}
.st-key-il_topnav_toggle .stButton>button{{
  background:transparent!important;border:1px solid rgba(232,255,214,0.16)!important;
  color:{SAGE['charcoal']}!important;box-shadow:none!important;font-size:1.1rem!important;
  padding:0.3rem 0.7rem!important;
}}
.st-key-il_mobile_nav_panel{{
  margin:-0.5rem -0.25rem 1rem;padding:6px 10px 10px;
  background:rgba(11,18,15,0.92);border-bottom:1px solid rgba(232,255,214,0.08);
}}
.st-key-il_mobile_nav_panel [data-testid="stPageLink"] p{{font-size:0.86rem!important;color:{SAGE['stone']}!important}}
.st-key-il_mobile_nav_panel [data-testid="stPageLink"][aria-current="page"] p{{color:{SAGE['mid']}!important;font-weight:700!important}}

@media (max-width:900px){{
  .st-key-il_topnav_links{{display:none!important}}
  .st-key-il_topnav_toggle{{display:block!important}}
}}
@media (min-width:901px){{
  .st-key-il_mobile_nav_panel{{display:none!important}}
}}

.il-daily-target{{
  display:inline-flex;align-items:center;gap:8px;font-size:1rem;font-weight:600;
  color:{SAGE['stone']};background:rgba(255,255,255,0.06);border:1px solid {SAGE['pale']};
  border-radius:99px;padding:8px 18px;box-shadow:0 2px 10px rgba(0,0,0,0.2);
  transition:border-color .25s ease,box-shadow .25s ease;
}}
.il-daily-target b{{font-size:1.15rem;color:{SAGE['mid']}}}
/* Non-blocking visual warning once remaining calories hit 0 — logging more
   food is still allowed, this is purely informational. */
.il-daily-target-warn{{
  border-color:#e5584a!important;box-shadow:0 2px 12px rgba(229,88,74,0.35)!important;
}}
.il-daily-target-warn b{{color:#ff9686!important}}
/* Logged-in status strip, directly under the main nav — Daily Target on
   the left, Remaining Calories pushed to the far right of the same row */
.st-key-il_status_panel{{
  display:flex!important;flex-direction:row!important;
  justify-content:flex-start;align-items:center;gap:16px;
  margin:-0.5rem -0.25rem 1rem;padding:8px 18px;
}}
/* Streamlit gives each element-container width:100% by default, which (in
   this flex row) splits the two pills into two equal-width halves instead
   of letting them hug their own content — override to shrink-to-fit, then
   push the second pill (Remaining) flush to the right with auto margin. */
.st-key-il_status_panel .stElementContainer{{width:auto!important;flex:0 0 auto!important}}
.st-key-il_status_panel .stElementContainer:last-child{{margin-left:auto}}

/* ── PREMIUM LOGIN / ACCOUNT (inline in the main nav row, far right) ── */
.st-key-il_login_btn{{display:flex;justify-content:flex-end}}
.st-key-il_login_btn [data-testid="stPopoverButton"],
.st-key-il_login_btn .stButton>button{{
  background:linear-gradient(180deg,{SAGE['mid']} 0%,#1c5c45 100%)!important;
  color:{SAGE['charcoal']}!important;border:1px solid rgba(232,255,214,0.16)!important;
  border-radius:99px!important;font-weight:700!important;font-size:0.95rem!important;
  padding:0.5rem 1.1rem!important;width:auto!important;max-width:160px;
  overflow:hidden;text-overflow:ellipsis;
  box-shadow:0 6px 20px rgba(0,0,0,0.35),inset 0 1px 0 rgba(255,255,255,0.16)!important;
  transition:box-shadow .22s ease,transform .22s ease!important;
}}
.st-key-il_login_btn [data-testid="stPopoverButton"]:hover,
.st-key-il_login_btn .stButton>button:hover{{
  box-shadow:0 10px 26px rgba(47,181,134,0.4),inset 0 1px 0 rgba(255,255,255,0.2)!important;
  transform:translateY(-2px) scale(1.03)!important;
}}

/* ── HERO ── */
.il-hero{{
  background:linear-gradient(135deg,{SAGE['darkest']} 0%,{SAGE['dark']} 50%,{SAGE['mid']} 100%);
  border-radius:24px;padding:2.6rem 2.7rem;color:white;margin-bottom:2rem;
  position:relative;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.4);
  animation:ilFadeUp .5s cubic-bezier(.2,.9,.3,1);
}}
.il-hero::before{{
  content:'';position:absolute;top:-60px;right:-60px;
  width:240px;height:240px;background:rgba(255,255,255,0.05);border-radius:50%;
  filter:blur(2px);
}}
.il-hero::after{{
  content:'';position:absolute;inset:0;border-radius:24px;
  border:1px solid rgba(255,255,255,0.08);pointer-events:none;
}}
.il-hero h1{{font-size:2.05rem;font-weight:800;margin:0 0 0.3rem;color:white;letter-spacing:-0.015em}}
.il-hero p{{font-size:1.02rem;opacity:0.9;margin:0;color:white;line-height:1.5}}
.il-tagline{{font-size:0.65rem;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;opacity:0.65;margin-bottom:3px}}

/* ── LOGO — hero brand treatment (header/sidebar/footer) ── */
.il-logo-wrap{{position:relative;display:inline-block;animation:ilFadeUp .6s cubic-bezier(.2,.9,.3,1)}}
.il-logo-glow{{
  position:absolute;inset:-16px;border-radius:50%;
  background:radial-gradient(closest-side,rgba(200,255,91,0.28),transparent 72%);
  filter:blur(8px);animation:ilGlow 3.2s ease-in-out infinite;z-index:0;
}}
.il-logo-glass{{
  position:relative;z-index:1;background:transparent;border:none;
  padding:2px;animation:ilFloatYSubtle 5s ease-in-out infinite;
}}
.il-logo-glass img{{display:block;filter:
  brightness(1.2) saturate(1.4)
  drop-shadow(0.6px 0 0 rgba(255,255,255,0.85)) drop-shadow(-0.6px 0 0 rgba(255,255,255,0.85))
  drop-shadow(0 0.6px 0 rgba(255,255,255,0.85)) drop-shadow(0 -0.6px 0 rgba(255,255,255,0.85))
  drop-shadow(0 0 8px rgba(47,181,134,0.55))
}}

/* ── MEGA HERO (Home only) — premium animated landing ── */
@keyframes ilBgDrift{{
  0%{{background-position:0% 50%}}
  50%{{background-position:100% 50%}}
  100%{{background-position:0% 50%}}
}}
@keyframes ilFloatY{{
  0%,100%{{transform:translateY(0)}}
  50%{{transform:translateY(-14px)}}
}}
@keyframes ilFloatYSubtle{{
  0%,100%{{transform:translateY(0)}}
  50%{{transform:translateY(-4px)}}
}}
@keyframes ilShapeDrift{{
  0%,100%{{transform:translate(0,0) scale(1)}}
  50%{{transform:translate(20px,-30px) scale(1.08)}}
}}
@keyframes ilTaglineGlow{{
  0%,100%{{filter:drop-shadow(0 0 14px rgba(200,255,91,0.35))}}
  50%{{filter:drop-shadow(0 0 26px rgba(200,255,91,0.6))}}
}}
@keyframes ilFadeSlideUp{{
  from{{opacity:0;transform:translateY(22px)}}
  to{{opacity:1;transform:translateY(0)}}
}}

/* ── CINEMATIC SCAN SCENE (Home hero) — stickman + magnifying glass scanning
   a barcode, sweeping scan-beam, rising data motes, AI-decode chips ── */
@keyframes ilScanActorEnter{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes ilScanArmApproach{{from{{transform:rotate(-16deg) translate(0,-10px)}}to{{transform:rotate(0deg) translate(0,0)}}}}
@keyframes ilScanSweep{{
  0%{{opacity:0;transform:translateY(-34px)}}
  12%{{opacity:1}}
  85%{{opacity:1}}
  100%{{opacity:0;transform:translateY(34px)}}
}}
@keyframes ilScanMoteRise{{
  0%{{opacity:0;transform:translateY(0) scale(.4)}}
  18%{{opacity:1;transform:translateY(-8px) scale(1)}}
  100%{{opacity:0;transform:translateY(-90px) scale(.7)}}
}}
@keyframes ilScanChipIn{{
  from{{opacity:0;transform:translateY(16px) scale(.85)}}
  60%{{opacity:1}}
  to{{opacity:1;transform:translateY(0) scale(1)}}
}}
@keyframes ilScanIdleFloat{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-6px)}}}}

.il-scan-scene{{position:relative;width:100%;max-width:340px;margin:0 auto 1.2rem;overflow:visible}}
.il-scan-scene svg{{display:block;width:100%;height:auto}}
.il-scan-actor{{animation:ilScanActorEnter .7s cubic-bezier(.2,.8,.2,1) both}}
.il-scan-arm{{transform-origin:270px 170px;animation:ilScanArmApproach 1s .6s cubic-bezier(.3,.7,.3,1) both}}
.il-scan-beam{{
  stroke:{SAGE['accent']};stroke-width:3;opacity:0;
  filter:drop-shadow(0 0 6px {SAGE['accent']}) drop-shadow(0 0 14px rgba(53,208,224,0.5));
  animation:ilScanSweep 1.4s 1.55s cubic-bezier(.4,0,.2,1) both;
}}
.il-scan-mote{{fill:{SAGE['accent']};opacity:0;animation:ilScanMoteRise 2.2s ease-out both}}
.il-scan-mote:nth-of-type(1){{animation-delay:2.45s}}
.il-scan-mote:nth-of-type(2){{animation-delay:2.6s}}
.il-scan-mote:nth-of-type(3){{animation-delay:2.7s}}
.il-scan-mote:nth-of-type(4){{animation-delay:2.85s}}
.il-scan-mote:nth-of-type(5){{animation-delay:2.95s}}
.il-scan-mote:nth-of-type(6){{animation-delay:3.1s}}
.il-scan-chip{{
  opacity:0;
  animation:ilScanChipIn .9s cubic-bezier(.2,.8,.2,1) var(--d,0s) both,
    ilScanIdleFloat 4.2s ease-in-out calc(var(--d,0s) + 1.2s) infinite;
}}
.il-scan-chip rect{{fill:{SAGE['darkest']};stroke:{SAGE['accent']};stroke-width:1.6;filter:drop-shadow(0 3px 10px rgba(0,0,0,0.4))}}
.il-scan-chip text{{fill:{SAGE['light']};font-family:'Inter',sans-serif;font-size:11px;font-weight:700;letter-spacing:.02em}}
@media (max-width:640px){{.il-scan-scene{{max-width:260px}}}}

.il-mega-hero{{
  position:relative;overflow:hidden;border-radius:28px;margin-bottom:2.2rem;
  padding:4.2rem 2rem 3.6rem;text-align:center;isolation:isolate;
  background:radial-gradient(ellipse 60% 50% at 50% 45%,rgba(47,181,134,0.10),transparent 70%),{SAGE['darkest']};
  box-shadow:0 20px 60px rgba(0,0,0,0.55);
}}
.il-mega-hero::after{{
  content:'';position:absolute;inset:0;border-radius:28px;z-index:0;
  border:1px solid rgba(232,255,214,0.07);pointer-events:none;
}}
.il-mega-shape{{position:absolute;border-radius:50%;filter:blur(46px);z-index:0;opacity:0.5;animation:ilShapeDrift 12s ease-in-out infinite}}
.il-mega-shape.s1{{width:260px;height:260px;background:rgba(47,181,134,0.30);top:-60px;left:-40px;animation-duration:14s}}
.il-mega-shape.s2{{width:220px;height:220px;background:rgba(200,255,91,0.16);bottom:-50px;right:-30px;animation-duration:17s;animation-delay:1s}}
.il-mega-shape.s3{{width:180px;height:180px;background:rgba(232,255,214,0.08);top:40%;right:15%;animation-duration:11s;animation-delay:2s}}

.il-mega-content{{position:relative;z-index:1;max-width:760px;margin:0 auto}}

.il-mega-badge{{
  display:inline-block;font-family:ui-monospace,'SF Mono',Menlo,Consolas,monospace;
  font-size:0.78rem;font-weight:600;color:{SAGE['accent']};
  letter-spacing:0.16em;text-transform:uppercase;margin-bottom:1.2rem;
  animation:ilFadeSlideUp .6s cubic-bezier(.2,.9,.3,1) both;
}}

.il-mega-logo-wrap{{
  position:relative;display:inline-block;margin-bottom:1.2rem;
  animation:ilFadeSlideUp .7s cubic-bezier(.2,.9,.3,1) .08s both;
}}
.il-mega-logo-glow{{
  position:absolute;inset:-26px;border-radius:50%;z-index:0;
  background:radial-gradient(closest-side,rgba(200,255,91,0.30),transparent 72%);
  filter:blur(12px);animation:ilGlow 3.4s ease-in-out infinite;
}}
.il-mega-logo-glass{{
  position:relative;z-index:1;background:transparent;border:none;padding:6px;
  animation:ilFloatY 5s ease-in-out infinite;
}}
.il-mega-logo-glass img{{display:block;width:120px;filter:
  brightness(1.2) saturate(1.4)
  drop-shadow(0.8px 0 0 rgba(255,255,255,0.85)) drop-shadow(-0.8px 0 0 rgba(255,255,255,0.85))
  drop-shadow(0 0.8px 0 rgba(255,255,255,0.85)) drop-shadow(0 -0.8px 0 rgba(255,255,255,0.85))
  drop-shadow(0 0 10px rgba(47,181,134,0.55))
}}

.il-mega-title{{
  font-size:clamp(2.4rem,6vw,4rem);font-weight:800;letter-spacing:-0.02em;line-height:1.05;
  margin:0 0 0.7rem;color:{SAGE['charcoal']};
  animation:ilFadeSlideUp .7s cubic-bezier(.2,.9,.3,1) .16s both;
}}
.il-mega-title span{{color:{SAGE['mid']}}}
.il-mega-tagline{{
  font-size:clamp(1.15rem,2.6vw,1.6rem);font-weight:700;letter-spacing:-0.01em;line-height:1.3;
  margin:0 0 1.1rem;color:{SAGE['stone']};
  animation:ilFadeSlideUp .8s cubic-bezier(.2,.9,.3,1) .24s both;
}}
.il-mega-tagline span{{
  color:{SAGE['accent']};font-weight:800;
  filter:drop-shadow(0 0 14px rgba(200,255,91,0.35));
  animation:ilTaglineGlow 3.5s ease-in-out infinite;
}}
.il-mega-subtitle{{
  font-size:1.02rem;color:{SAGE['teal']};line-height:1.65;max-width:560px;margin:0 auto;
  animation:ilFadeSlideUp .8s cubic-bezier(.2,.9,.3,1) .32s both;
}}
@media (max-width:640px){{
  .il-mega-hero{{padding:3rem 1.2rem 2.6rem;border-radius:22px}}
  .il-mega-logo-glass img{{width:88px}}
  .il-mega-subtitle{{font-size:0.92rem}}
}}

/* ── VERDICT ── */
.verdict-vegan{{background:linear-gradient(135deg,rgba(23,201,168,0.16),rgba(23,201,168,0.06));border-left:5px solid {SAGE['mid']};border-radius:18px;padding:1.5rem 1.9rem;margin:0.8rem 0;box-shadow:0 6px 24px rgba(23,201,168,0.14)}}
.verdict-notvegan{{background:linear-gradient(135deg,rgba(229,88,74,0.16),rgba(229,88,74,0.06));border-left:5px solid #e5584a;border-radius:18px;padding:1.5rem 1.9rem;margin:0.8rem 0;box-shadow:0 6px 24px rgba(229,88,74,0.14)}}
.verdict-uncertain{{background:linear-gradient(135deg,rgba(224,171,58,0.16),rgba(224,171,58,0.06));border-left:5px solid #e0ab3a;border-radius:18px;padding:1.5rem 1.9rem;margin:0.8rem 0}}
.verdict-unknown{{background:{SAGE['pale']};border-left:5px solid {SAGE['teal']};border-radius:18px;padding:1.5rem 1.9rem;margin:0.8rem 0}}
.verdict-icon{{font-size:2rem;margin-bottom:3px}}
.verdict-title{{font-size:1.4rem;font-weight:700;margin:0 0 0.3rem;color:{SAGE['charcoal']}}}
.verdict-sub{{font-size:0.9rem;color:{SAGE['stone']};margin:0;line-height:1.5}}
.conf-bar-bg{{background:rgba(255,255,255,0.08);border-radius:99px;height:7px;margin-top:6px}}
.conf-bar{{height:7px;border-radius:99px}}

/* ── INGREDIENT CARDS ── */
.ing-card{{background:{SAGE['offwhite']};border-radius:14px;padding:11px 13px;margin:4px 0;border:1px solid {SAGE['pale']};display:flex;align-items:flex-start;gap:9px;box-shadow:0 1px 6px rgba(0,0,0,0.16);transition:box-shadow .22s ease,transform .22s ease}}
.ing-card:hover{{box-shadow:0 4px 16px rgba(0,0,0,0.28);transform:translateY(-1px)}}
.ing-icon{{font-size:1rem;flex-shrink:0;margin-top:1px}}
.ing-name{{font-weight:600;font-size:0.85rem;color:{SAGE['charcoal']}}}
.ing-reason{{font-size:0.76rem;color:{SAGE['stone']};margin-top:1px;line-height:1.4}}
.ing-alt{{font-size:0.7rem;color:{SAGE['mid']};font-weight:500;margin-top:3px}}
.ing-card-nv{{border-left:3px solid #e5584a;background:rgba(229,88,74,0.09)}}
.ing-card-unc{{border-left:3px solid #e0ab3a;background:rgba(224,171,58,0.09)}}
.ing-card-vegan{{border-left:3px solid {SAGE['mid']};background:rgba(23,201,168,0.09)}}

/* ── METRICS ── */
.metric-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:1rem 0}}
.metric-card{{background:{SAGE['offwhite']};border:1px solid {SAGE['pale']};border-radius:16px;padding:1.1rem;text-align:center;box-shadow:0 2px 10px rgba(0,0,0,0.18);transition:box-shadow .22s ease,transform .22s ease}}
.metric-card:hover{{box-shadow:0 6px 18px rgba(0,0,0,0.3);transform:translateY(-1px)}}
.metric-icon{{font-size:1.3rem;margin-bottom:3px}}
.metric-num{{font-size:1.5rem;font-weight:700;color:{SAGE['charcoal']};line-height:1}}
.metric-lbl{{font-size:0.65rem;color:{SAGE['stone']};text-transform:uppercase;letter-spacing:0.06em;margin-top:3px}}

/* ── st.metric widgets (BMI / Daily Calories / Daily Protein / Daily Target) ── */
div[data-testid="stMetric"]{{
  background:{SAGE['offwhite']};border-radius:18px;padding:1.35rem 1rem;
  border:1px solid {SAGE['pale']};box-shadow:0 3px 14px rgba(0,0,0,0.16);
  transition:box-shadow .22s ease,transform .22s ease;overflow:hidden;
}}
div[data-testid="stMetric"]:hover{{box-shadow:0 8px 22px rgba(0,0,0,0.26);transform:translateY(-2px)}}
div[data-testid="stMetricLabel"]{{font-size:0.78rem!important;color:{SAGE['stone']}!important}}
div[data-testid="stMetricValue"]{{
  font-size:clamp(1.05rem,2.1vw,2rem)!important;font-weight:800!important;
  color:{SAGE['charcoal']}!important;white-space:normal!important;
  overflow-wrap:break-word;line-height:1.25!important;
}}

/* ── Daily Consumption dialog — tighter tiles, no clipping/overflow ── */
div[role="dialog"] div[data-testid="stMetric"]{{
  padding:0.85rem 0.6rem!important;min-height:92px;display:flex;flex-direction:column;
  justify-content:center;
}}
div[role="dialog"] div[data-testid="stMetricLabel"]{{font-size:0.7rem!important}}
div[role="dialog"] div[data-testid="stMetricValue"]{{
  font-size:clamp(0.82rem,1.6vw,1.15rem)!important;line-height:1.2!important;
}}
div[role="dialog"] div[data-testid="stMetricDelta"]{{font-size:0.68rem!important}}

/* ── HEALTH ── */
.health-wrap{{background:{SAGE['offwhite']};border-radius:16px;padding:1.2rem 1.4rem;border:1px solid {SAGE['pale']};box-shadow:0 2px 10px rgba(0,0,0,0.18)}}
.health-num{{font-size:2.2rem;font-weight:800;line-height:1}}
.health-lbl{{font-size:0.65rem;color:{SAGE['stone']};text-transform:uppercase;letter-spacing:0.06em}}
.health-bar-bg{{background:{SAGE['pale']};border-radius:99px;height:9px;margin-top:7px}}
.health-bar{{height:9px;border-radius:99px}}

/* ── PILLS ── */
.pill{{display:inline-flex;align-items:center;gap:3px;border-radius:99px;padding:3px 11px;font-size:0.76rem;margin:2px;font-weight:500}}
.pill-red{{background:rgba(229,88,74,0.16);color:#ff9686;border:1px solid rgba(229,88,74,0.4)}}
.pill-orange{{background:rgba(224,171,58,0.16);color:#f2c766;border:1px solid rgba(224,171,58,0.4)}}
.pill-green{{background:rgba(23,201,168,0.16);color:#6fe8cf;border:1px solid rgba(23,201,168,0.4)}}
.pill-blue{{background:rgba(53,150,224,0.16);color:#8ec6f2;border:1px solid rgba(53,150,224,0.4)}}
.pill-sage{{background:{SAGE['pale']};color:{SAGE['charcoal']};border:1px solid {SAGE['light']}}}

/* ── SECTION HEADERS ── */
.shdr{{font-size:0.65rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{SAGE['stone']};margin:1.2rem 0 0.6rem}}

/* ── BUTTONS — premium dark-green glossy finish (no neon lime) ── */
.stButton>button{{
  background:linear-gradient(180deg,{SAGE['mid']} 0%,#1c5c45 100%)!important;
  color:{SAGE['charcoal']}!important;border:1px solid rgba(232,255,214,0.14)!important;
  border-radius:14px!important;font-weight:700!important;font-size:0.88rem!important;
  box-shadow:0 4px 14px rgba(0,0,0,0.35),inset 0 1px 0 rgba(255,255,255,0.16)!important;
  transition:box-shadow .2s ease,transform .2s ease!important;
}}
.stButton>button:hover{{
  box-shadow:0 8px 22px rgba(47,181,134,0.35),inset 0 1px 0 rgba(255,255,255,0.22)!important;
  transform:translateY(-2px) scale(1.015)!important;
}}
.stButton>button:active{{transform:translateY(0) scale(0.99)!important}}

/* ── HERO CTA — premium dark-green pill, same finish as other buttons ── */
.st-key-get_started_cta .stButton>button{{
  background:linear-gradient(180deg,#37c793 0%,#1a5540 100%)!important;
  color:{SAGE['charcoal']}!important;border:1px solid rgba(232,255,214,0.18)!important;
  border-radius:99px!important;font-weight:700!important;font-size:0.98rem!important;
  padding:0.85rem 1rem!important;
  box-shadow:0 6px 20px rgba(0,0,0,0.4),inset 0 1px 0 rgba(255,255,255,0.2)!important;
}}
.st-key-get_started_cta .stButton>button:hover{{
  box-shadow:0 10px 28px rgba(47,181,134,0.4),inset 0 1px 0 rgba(255,255,255,0.24)!important;
  transform:translateY(-2px) scale(1.02)!important;
}}

/* ── AGENT BADGES ── */
.agent-badge{{display:inline-flex;align-items:center;gap:4px;background:{SAGE['pale']};color:{SAGE['charcoal']};border:1px solid {SAGE['light']};border-radius:8px;padding:3px 9px;font-size:0.72rem;font-weight:500;margin:2px}}

/* ── HISTORY ── */
.h-dot{{width:9px;height:9px;border-radius:50%;flex-shrink:0}}
.history-row{{display:flex;align-items:center;gap:9px;padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.1)}}

/* ── MISC ── */
.stTabs [data-baseweb="tab"]{{font-size:0.86rem!important;font-weight:500!important}}
.stTabs [data-baseweb="tab"][aria-selected="true"]{{color:{SAGE['mid']}!important}}
[data-testid="stChatMessage"]{{border-radius:16px!important}}

/* ── DEMO CARDS ── */
.demo-card{{background:rgba(16,29,46,0.65);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);border-radius:18px;padding:16px;border:1px solid {SAGE['pale']};cursor:pointer;transition:box-shadow .22s ease,transform .22s ease;box-shadow:0 2px 10px rgba(0,0,0,0.22)}}
.demo-card:hover{{box-shadow:0 10px 30px rgba(23,201,168,0.22);transform:translateY(-3px) scale(1.015)}}

/* ── FEATURE CARDS ── */
.feat-card{{background:rgba(16,29,46,0.65);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);border-radius:18px;padding:18px;border:1px solid {SAGE['pale']};box-shadow:0 2px 10px rgba(0,0,0,0.18);transition:box-shadow .2s ease,transform .2s ease}}
.feat-card:hover{{box-shadow:0 8px 22px rgba(0,0,0,0.3);transform:translateY(-2px)}}

/* ── STAT CARDS ── */
.stat-card{{background:rgba(16,29,46,0.65);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);border:1px solid {SAGE['pale']};border-radius:18px;padding:16px;text-align:center;transition:box-shadow .2s ease,transform .2s ease}}
.stat-card:hover{{box-shadow:0 8px 22px rgba(0,0,0,0.3);transform:translateY(-2px)}}

/* ── QUICK ACTION CARDS (Home) — modern app-launcher tiles: big illustration,
   whole tile clickable, small secondary pill label pinned to the bottom ── */
[class*="st-key-qa_"]{{
  position:relative;border-radius:20px;background:rgba(16,29,46,0.65);
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  border:1px solid {SAGE['pale']};box-shadow:0 4px 18px rgba(0,0,0,0.24);
  transition:box-shadow .25s ease,transform .25s ease;overflow:hidden;
  padding:1.2rem 1rem 1rem;display:flex;flex-direction:column;
  align-items:center;min-height:230px;cursor:pointer;
}}
[class*="st-key-qa_"]:hover{{box-shadow:0 16px 38px rgba(47,181,134,0.28);transform:translateY(-5px) scale(1.02)}}
[class*="st-key-qa_"] .stElementContainer:has(svg){{
  flex:1 1 auto;min-height:0;display:flex;align-items:center;justify-content:center;
}}
[class*="st-key-qa_"] .stElementContainer:has(svg) [data-testid="stMarkdownContainer"],
[class*="st-key-qa_"] .stElementContainer:has(svg) .stMarkdown{{
  width:100%;height:100%;display:flex;align-items:center;justify-content:center;
}}
[class*="st-key-qa_"] svg{{width:100%;height:100%;max-height:100%}}
.il-qa-pill{{
  margin-top:auto;padding:0.5rem 1.3rem;border-radius:99px;
  border:1px solid rgba(232,255,214,0.25);background:rgba(255,255,255,0.04);
  color:{SAGE['stone']};font-weight:700;font-size:0.86rem;text-align:center;
  white-space:nowrap;transition:border-color .25s ease,color .25s ease,background .25s ease;
}}
[class*="st-key-qa_"]:hover .il-qa-pill{{
  border-color:{SAGE['mid']};color:{SAGE['charcoal']};background:rgba(47,181,134,0.12);
}}
/* Real button stretched invisibly over the whole tile — click anywhere triggers it */
/* The button's own wrapper is position:relative by default, which would
   trap the absolutely-positioned button inside its own (zero-height) box
   instead of the full card — force it static so the button escapes upward. */
[class*="st-key-qa_"] [class*="st-key-btn_"]{{position:static!important}}
[class*="st-key-qa_"] .stButton{{position:absolute;inset:0;z-index:3}}
[class*="st-key-qa_"] .stButton>button{{
  width:100%;height:100%;background:transparent!important;border:none!important;
  box-shadow:none!important;color:transparent!important;cursor:pointer;
}}
@media (max-width:640px){{
  [class*="st-key-qa_"]{{min-height:170px;padding:0.9rem 0.7rem}}
}}

/* ── FOOTER ── */
.ingrelens-footer{{
  background:linear-gradient(135deg,{SAGE['darkest']},{SAGE['dark']});
  color:white;text-align:center;padding:1.6rem 1.2rem;border-radius:20px;
  margin-top:2rem;font-size:0.82rem;opacity:0.96;
  box-shadow:0 10px 32px rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.06);
}}
.ingrelens-footer a{{color:{SAGE['light']};text-decoration:none}}

/* ── RESPONSIVE ── */
@media (max-width:768px){{
  .main .block-container{{padding:1.1rem 1rem 2.5rem}}
  .il-hero{{padding:1.7rem 1.5rem;border-radius:18px}}
  .il-hero h1{{font-size:1.5rem}}
}}

</style>
"""

def inject_css():
    st.markdown(BRAND_CSS, unsafe_allow_html=True)

def get_logo_b64(variant="brand"):
    """Load logo as base64. variant: header|sidebar|brand|icon|square"""
    paths = {
        "header":  "logo_header.png",   # 300px — for page hero headers
        "sidebar": "logo_sidebar.png",  # 160px — for sidebar branding
        "brand":   "logo_header.png",   # alias → header size
        "icon":    "logo_icon.png",     # 64px — for chat avatars
        "square":  "logo_square.png",   # 120px — for page_icon / small uses
    }
    p = Path(__file__).parent / "assets" / paths.get(variant, "logo_header.png")
    if p.exists():
        return base64.b64encode(p.read_bytes()).decode()
    # Fallback chain
    for fallback in ["logo_header.png", "logo_square.png", "logo_icon.png"]:
        fp = Path(__file__).parent / "assets" / fallback
        if fp.exists():
            return base64.b64encode(fp.read_bytes()).decode()
    return ""


BRAND_TAGLINE = "SCAN, ANALYSE & EAT SMARTER"

def _render_login_popover():
    with st.popover("👤  Login", use_container_width=True):
        tab_in, tab_up = st.tabs(["Sign In", "Sign Up"])
        with tab_in:
            email = st.text_input("Email", key="login_email")
            pw = st.text_input("Password", type="password", key="login_pw")
            if st.button("Sign In", key="btn_signin", type="primary", use_container_width=True):
                user = db.authenticate(email, pw)
                if user:
                    do_login(user)
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
        with tab_up:
            name = st.text_input("Name", key="signup_name")
            email2 = st.text_input("Email", key="signup_email")
            pw2 = st.text_input("Password", type="password", key="signup_pw")
            if st.button("Sign Up", key="btn_signup", type="primary", use_container_width=True):
                if not (name and email2 and pw2):
                    st.error("All fields are required.")
                else:
                    uid = db.create_account(name, email2, pw2)
                    if uid:
                        do_login(db.get_user_by_email(email2))
                        st.rerun()
                    else:
                        st.error("That email is already registered.")


def render_status_panel():
    """Compact status strip directly under the main nav — Daily Target +
    Remaining Calories, shown only when logged in. Uses the exact same
    _get_daily_target()/db.get_daily_consumption() values Food Logs uses,
    so the two stay in sync automatically (same source of truth, not a
    separate computation)."""
    if not st.session_state.get("auth_user"):
        return
    user_id = st.session_state.get("user_id", "")
    targets = _get_daily_target(user_id)
    daily = db.get_daily_consumption(user_id)
    remaining = max(targets["daily_calories"] - daily["calories"], 0)
    warn_class = " il-daily-target-warn" if remaining <= 0 else ""
    with st.container(key="il_status_panel"):
        # Two separate st.markdown calls so each pill is its own flex child —
        # a single call would wrap both in one element and space-between
        # would have nothing to distribute.
        st.markdown(
            f'<div class="il-daily-target">🎯 Daily Target&nbsp; <b>{targets["daily_calories"]} kcal</b></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="il-daily-target{warn_class}">🔥 Remaining&nbsp; <b>{remaining:.0f} kcal</b></div>',
            unsafe_allow_html=True,
        )


def render_nav_auth_control():
    """Inline auth control that sits in the main nav row (far right, after
    About) — no separate status bar above the nav, so there's no reserved
    empty space when logged out.
    Logged out: only the Login popover (Sign In / Sign Up) shows — no
    Profile menu anywhere in the nav for anonymous users.
    Logged in: a same-sized popover button reading "Hi, [name]" (the
    username appears once, on the button itself — nothing repeats it
    inside), whose dropdown merges what used to be two separate menus:
    Profile, Food Logs, History, and Logout."""
    auth = st.session_state.get("auth_user")

    with st.container(key="il_login_btn"):
        if not auth:
            _render_login_popover()
            return

        display_name = auth["name"] or auth["email"]
        with st.popover(f"Hi, {display_name}", use_container_width=True):
            for target, label, icon in _PROFILE_DROPDOWN:
                st.page_link(target, label=label, icon=icon)
            if st.button("Logout", key="btn_logout_header", type="primary", use_container_width=True):
                do_logout()
                st.switch_page("app.py")


def render_scan_scene() -> str:
    """Stickman-with-magnifying-glass scanning a food label — cinematic entrance
    visual for the Home hero. Pure inline SVG + CSS keyframes (no JS/Lottie
    dependency), staged to play once on hero load: figure enters → glass arm
    swings up → scan-beam sweeps the barcode → data motes rise → AI result
    chips pop in → whole scene settles into a slow idle float."""
    return f'''<div class="il-scan-scene"><svg viewBox="0 0 460 420">
  <g class="il-scan-actor">
    <rect x="40" y="120" width="150" height="220" rx="10" fill="{SAGE['offwhite']}" stroke="{SAGE['pale']}" stroke-width="2"/>
    <path d="M115 120 C105 100 125 88 130 70 C142 92 140 115 115 120 Z" fill="{SAGE['mid']}" opacity="0.9"/>
    <g fill="{SAGE['stone']}" opacity="0.5">
      <rect x="58" y="150" width="70" height="7" rx="2"/>
      <rect x="58" y="165" width="54" height="5" rx="2"/>
      <rect x="58" y="176" width="60" height="5" rx="2"/>
      <rect x="58" y="187" width="46" height="5" rx="2"/>
      <rect x="58" y="198" width="58" height="5" rx="2"/>
    </g>
    <g fill="{SAGE['stone']}" opacity="0.7">
      <rect x="58" y="270" width="4" height="46"/><rect x="66" y="270" width="2" height="46"/>
      <rect x="72" y="270" width="7" height="46"/><rect x="83" y="270" width="2" height="46"/>
      <rect x="89" y="270" width="4" height="46"/><rect x="97" y="270" width="3" height="46"/>
      <rect x="105" y="270" width="7" height="46"/><rect x="116" y="270" width="2" height="46"/>
      <rect x="122" y="270" width="4" height="46"/><rect x="130" y="270" width="2" height="46"/>
      <rect x="136" y="270" width="7" height="46"/><rect x="147" y="270" width="3" height="46"/>
      <rect x="155" y="270" width="2" height="46"/>
    </g>
    <line class="il-scan-beam" x1="50" y1="270" x2="180" y2="270"/>
    <circle class="il-scan-mote" cx="68" cy="266" r="3.2"/>
    <circle class="il-scan-mote" cx="90" cy="266" r="2.6"/>
    <circle class="il-scan-mote" cx="112" cy="266" r="3.6"/>
    <circle class="il-scan-mote" cx="130" cy="266" r="2.8"/>
    <circle class="il-scan-mote" cx="146" cy="266" r="3.2"/>
    <circle class="il-scan-mote" cx="100" cy="266" r="2.4"/>
    <circle cx="270" cy="120" r="22" fill="none" stroke="{SAGE['stone']}" stroke-width="6"/>
    <g stroke="{SAGE['stone']}" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round">
      <line x1="270" y1="142" x2="270" y2="235"/>
      <line x1="270" y1="235" x2="242" y2="315"/>
      <line x1="270" y1="235" x2="300" y2="315"/>
      <line x1="270" y1="170" x2="236" y2="210"/>
    </g>
    <g class="il-scan-arm">
      <line x1="270" y1="170" x2="128" y2="230" stroke="{SAGE['stone']}" stroke-width="6" fill="none" stroke-linecap="round"/>
      <line x1="128" y1="230" x2="112" y2="246" stroke="{SAGE['accent']}" stroke-width="6" stroke-linecap="round"/>
      <circle cx="90" cy="268" r="26" fill="none" stroke="{SAGE['accent']}" stroke-width="6"/>
    </g>
    <g transform="translate(250,40)"><g class="il-scan-chip" style="--d:3.4s">
      <rect width="112" height="32" rx="16"/><text x="56" y="20" text-anchor="middle">VEGETARIAN</text>
    </g></g>
    <g transform="translate(300,110)"><g class="il-scan-chip" style="--d:3.65s">
      <rect width="76" height="32" rx="16"/><text x="38" y="20" text-anchor="middle">95% AI</text>
    </g></g>
    <g transform="translate(250,180)"><g class="il-scan-chip" style="--d:3.9s">
      <rect width="126" height="32" rx="16"/><text x="63" y="20" text-anchor="middle">LOW SODIUM</text>
    </g></g>
  </g>
</svg></div>'''


def render_home_hero():
    """Premium animated hero — Home page only. Same logo/palette, no new
    functionality; purely a visual entrance point for the app."""
    b64 = get_logo_b64("header")
    logo_img = (
        f'<div class="il-mega-logo-wrap"><div class="il-mega-logo-glow"></div>'
        f'<div class="il-mega-logo-glass"><img src="data:image/png;base64,{b64}" '
        f'alt="IngreLens AI"></div></div>'
        if b64 else '<div style="font-size:4rem">🏠</div>'
    )
    st.markdown(
        f'''<div class="il-mega-hero" id="il-hero-anchor">
  <div class="il-mega-shape s1"></div>
  <div class="il-mega-shape s2"></div>
  <div class="il-mega-shape s3"></div>
  <div class="il-mega-content">
    <div class="il-mega-badge">AI Ingredient Intelligence</div>
    {render_scan_scene()}
    {logo_img}
    <div class="il-mega-title">IngreLens <span>AI</span></div>
    <div class="il-mega-tagline">Scan. <span>Analyze.</span> &amp; Eat Smarter.</div>
    <div class="il-mega-subtitle">Smart ingredient intelligence, simplified. Scan with our Deep AI
      Analyzer, decode the data, and eat with confidence.</div>
  </div>
</div>''',
        unsafe_allow_html=True,
    )


def render_page_header(page_icon: str, page_title: str, page_subtitle: str = "", mega: bool = False):
    """
    Shared global header used on every page.
    Shows: larger logo + IngreLens AI branding + page title + subtitle.
    Call this at the top of every page instead of duplicating hero HTML.
    mega=True (Home only) swaps in the full premium animated hero.
    Login/Account control itself is rendered inline by render_top_nav().
    """
    render_floating_assistant()
    if mega:
        render_home_hero()
        return
    b64 = get_logo_b64("header")
    logo_img = (
        f'<div class="il-logo-wrap" style="margin-bottom:10px"><div class="il-logo-glow"></div>'
        f'<div class="il-logo-glass"><img src="data:image/png;base64,{b64}" '
        f'style="width:140px" alt="IngreLens AI"></div></div>'
        if b64 else
        f'<div style="font-size:3rem">{page_icon}</div>'
    )
    subtitle_html = (
        f'<p style="font-size:0.95rem;opacity:0.88;margin:4px 0 0;color:white">'
        f'{page_subtitle}</p>'
        if page_subtitle else ""
    )
    st.markdown(
        f'''<div class="il-hero" style="padding:1.8rem 2.2rem">
  <div style="display:flex;align-items:center;gap:22px;flex-wrap:wrap">
    <div style="flex-shrink:0;text-align:center">
      {logo_img}
      <div style="font-size:0.58rem;font-weight:700;letter-spacing:0.14em;
                  text-transform:uppercase;opacity:0.7;color:white;margin-top:4px">
        IngreLens AI
      </div>
      <div style="font-size:0.52rem;font-weight:600;letter-spacing:0.1em;
                  text-transform:uppercase;opacity:0.55;color:white">
        SCAN, ANALYSE &amp; EAT SMARTER
      </div>
    </div>
    <div style="flex:1;min-width:200px">
      <div style="font-size:1.55rem;font-weight:800;color:white;
                  letter-spacing:-0.01em;margin-bottom:3px">
        {(page_icon + ' ') if page_icon else ''}{page_title}
      </div>
      {subtitle_html}
    </div>
  </div>
</div>''',
        unsafe_allow_html=True,
    )


def render_logo_hero():
    """Full logo for hero section."""
    b64 = get_logo_b64("header")
    if b64:
        st.markdown(
            f'<img src="data:image/png;base64,{b64}" '
            f'style="max-width:320px;width:100%;margin-bottom:1rem;border-radius:16px" '
            f'alt="IngreLens AI logo">',
            unsafe_allow_html=True,
        )

def render_logo_sidebar():
    """Sidebar logo — uses pre-optimized 160px version for fast load."""
    b64 = get_logo_b64("sidebar")
    if b64:
        st.markdown(
            f'<div style="text-align:center;padding:14px 8px 6px">'
            f'<div class="il-logo-wrap"><div class="il-logo-glow"></div>'
            f'<div class="il-logo-glass">'
            f'<img src="data:image/png;base64,{b64}" style="width:130px;max-width:80vw" alt="IngreLens AI">'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="text-align:center;padding:0.8rem 0 0.4rem"><img src="data:image/png;base64,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" style="width:130px;border-radius:12px;box-shadow:0 4px 18px rgba(0,0,0,0.35)"></div>',
            unsafe_allow_html=True,
        )

def render_sidebar():
    with st.sidebar:
        # ── Logo ──────────────────────────────────────────────────────────────
        render_logo_sidebar()
        st.markdown(
            '<div style="text-align:center;font-size:1.05rem;font-weight:700;'
            'margin:6px 0 2px;letter-spacing:-0.01em;color:white">IngreLens AI</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="text-align:center;font-size:0.58rem;opacity:0.65;'
            'letter-spacing:0.12em;text-transform:uppercase;margin-bottom:10px;color:white">'
            'SCAN, ANALYSE &amp; EAT SMARTER</div>',
            unsafe_allow_html=True,
        )

        # ── Navigation (native sidebar nav disabled via showSidebarNavigation
        # so the logo can sit above it instead of below Streamlit's own "app"
        # header) ────────────────────────────────────────────────────────────
        st.page_link("app.py", label="IngreLens AI", icon="🏠")
        st.page_link("pages/1_📷_Scanner.py", label="Scanner", icon="📷")
        st.page_link("pages/2_🔍_Analyzer.py", label="Analyzer", icon="🔍")
        st.page_link("pages/3_🔢_Barcode_Lookup.py", label="Barcode Lookup", icon="🔢")
        st.page_link("pages/4_⚖️_Comparison.py", label="Comparison", icon="⚖️")
        st.page_link("pages/5_👤_Preferences.py", label="Preferences", icon="👤")
        st.page_link("pages/6_📚_History.py", label="History", icon="📚")
        st.page_link("pages/7_ℹ️_About.py", label="About IngreLens App", icon="ℹ️")


_NAV_CENTER = [
    ("pages/1_📷_Scanner.py", "Scanner", "📷"),
    ("pages/2_🔍_Analyzer.py", "Search Product", "🔍"),
    ("pages/3_🔢_Barcode_Lookup.py", "Barcode Lookup", "🔢"),
    ("pages/4_⚖️_Comparison.py", "Compare Products", "⚖️"),
]
_NAV_RIGHT = [
    ("pages/7_ℹ️_About.py", "About", "ℹ️"),
]
# Grouped under the "Profile" dropdown in the main nav — same routes/pages,
# just tucked behind one menu instead of three separate top-level pills.
_PROFILE_DROPDOWN = [
    ("pages/5_👤_Preferences.py", "Profile", "👤"),
    ("pages/8_🍽️_Food_Logs.py", "Food Logs", "🍽️"),
    ("pages/6_📚_History.py", "History", "📚"),
]


def render_top_nav():
    """Responsive top navigation bar — replaces the left sidebar.
    Uses the same st.page_link widgets as before (routing/logic untouched),
    just laid out horizontally. Collapses into a hamburger toggle under 900px.
    Login/Account sits inline at the far right of this same row (after
    About) — there's no separate status bar above the nav, so no empty
    space is reserved when logged out. Profile/Food Logs/History only
    exist as a dropdown (popover) inside the authenticated account
    control — logged out, there's no Profile menu at all, just Login."""
    import streamlit.components.v1 as components
    if "show_mobile_nav" not in st.session_state:
        st.session_state.show_mobile_nav = False

    b64 = get_logo_b64("sidebar")
    logo_html = (
        f'<div class="il-topnav-brand"><div class="il-logo-wrap" style="display:inline-block;vertical-align:middle">'
        f'<div class="il-logo-glow" style="inset:-10px"></div>'
        f'<div class="il-logo-glass"><img src="data:image/png;base64,{b64}" '
        f'style="width:38px;vertical-align:middle" alt="IngreLens AI"></div></div>'
        f'<span class="il-topnav-word">IngreLens <b>AI</b></span></div>'
        if b64 else '<span class="il-topnav-word">IngreLens <b>AI</b></span>'
    )

    with st.container(key="il_topnav"):
        col_logo, col_links, col_auth, col_toggle = st.columns([1.5, 8.0, 2.2, 0.3])
        with col_logo:
            with st.container(key="il_topnav_brand_link"):
                st.markdown(logo_html, unsafe_allow_html=True)
                # A real st.button (not a page_link) so clicking the logo can
                # also mark the Home dashboard as already "entered" — landing
                # straight on Quick Actions instead of the pre-Get-Started
                # hero gate. It's visually collapsed; clicks on the visible
                # logo are forwarded to it via JS, since Streamlit's own
                # fit-content sizing on the button kept winning over any
                # CSS-only inset:0 overlay attempt.
                if st.button("IngreLens AI", key="il_brand_home_btn"):
                    st.session_state["entered_app"] = True
                    st.session_state["_scroll_to_quick_actions"] = True
                    st.switch_page("app.py")
                components.html(
                    """<script>(function(){
                        const doc = window.parent.document;
                        const brand = doc.querySelector('.il-topnav-brand');
                        const btn = doc.querySelector(
                            '.st-key-il_topnav_brand_link button');
                        if (brand && btn) {
                            brand.onclick = function(){ btn.click(); };
                        }
                    })();</script>""",
                    height=0,
                )
        with col_links:
            with st.container(key="il_topnav_links"):
                # Unequal ratios so longer labels (e.g. "Search Product") don't clip.
                # No icons here (desktop pills) — every pixel goes to the label text.
                # Profile/Food Logs/History only ever appear grouped inside the
                # authenticated account control — logged out, there's no Profile
                # menu in the nav at all, just Login.
                _nav_ratios = [1.0, 1.55, 1.55, 1.7, 0.9]
                sub_cols = st.columns(_nav_ratios, gap="small")
                for i, (target, label, icon) in enumerate(_NAV_CENTER):
                    with sub_cols[i]:
                        st.page_link(target, label=label)
                with sub_cols[len(_NAV_CENTER)]:
                    for target, label, icon in _NAV_RIGHT:
                        st.page_link(target, label=label)
        with col_auth:
            render_nav_auth_control()
        with col_toggle:
            with st.container(key="il_topnav_toggle"):
                if st.button("☰", key="mobile_nav_toggle_btn"):
                    st.session_state.show_mobile_nav = not st.session_state.show_mobile_nav

    if st.session_state.show_mobile_nav:
        with st.container(key="il_mobile_nav_panel"):
            mobile_items = _NAV_CENTER + _NAV_RIGHT
            if st.session_state.get("auth_user"):
                mobile_items = _NAV_CENTER + _PROFILE_DROPDOWN + _NAV_RIGHT
            for target, label, icon in mobile_items:
                st.page_link(target, label=label, icon=icon)

    render_status_panel()


def _ensure_db_ready():
    """Create ingrelens.db and its tables if missing.

    Not cached: db.init_db() is itself idempotent (CREATE TABLE IF NOT
    EXISTS + seed-if-missing), and skipping that check via cache_resource
    meant a db file deleted/reset after the first run stayed table-less
    (and demo login broken) for the rest of the process's life.
    """
    db.init_db()
    return True

def init_state():
    _ensure_db_ready()
    for k, v in {
        "history": [], "chat_messages": [], "current_result": None,
        "user_prefs": {"diet": "None", "allergens": [], "health_goals": []},
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Local persistent identity — survives restarts and browser sessions so
    # preferences/history don't need reconfiguring, even before signing in.
    if "user_id" not in st.session_state:
        _activate_user(db.get_or_create_local_user())

    # Restore an authenticated session across a hard browser refresh/reopen —
    # st.session_state itself is wiped on those, so the logged-in user's id
    # is mirrored into the URL's query params (do_login/every page load) and
    # read back here via the same existing do_login() flow, never a new
    # auth path. Only ever restores an id that came from a real login.
    if not st.session_state.get("auth_user"):
        restore_uid = st.query_params.get("uid")
        if restore_uid:
            restored_user = db.get_user_by_id(restore_uid)
            if restored_user:
                do_login(restored_user)
    if st.session_state.get("auth_user"):
        st.query_params["uid"] = st.session_state.auth_user["user_id"]


# Transient per-page working state — cleared whenever the user actually
# navigates to a different page (not on same-page reruns), so every page
# always opens clean. History/preferences/auth are never touched.
_CLEARABLE_PAGE_KEYS = [
    # Scanner
    "ocr_extracted", "ocr_result", "ocr_result_name", "ocr_prod_name_saved",
    "ocr_image_hash", "barcode_result", "barcode_prod", "cam_detected_bc",
    "scan_mode_radio",
    # Barcode Lookup / Paste Ingredients
    "selected_barcode", "paste_result", "paste_result_name", "paste_raw", "paste_name_input",
    "paste_product", "_paste_demo_meta",
    # Analyzer / Search
    "ar", "ap", "analyzer_pending_query", "analyzer_products",
    "analyzer_suggestions", "analyzer_query", "analyzer_suggest_pick",
    # Comparison
    "cmp_result", "cmp_a", "cmp_b", "cmp_trigger",
]


def enter_page(page_key: str):
    """Call once near the top of every page, right after render_sidebar()."""
    if st.session_state.get("_current_page") != page_key:
        for k in _CLEARABLE_PAGE_KEYS:
            st.session_state.pop(k, None)
        st.session_state["_current_page"] = page_key


def _activate_user(user_id: str):
    """Point session state at user_id's saved preferences/history — used on
    first load, and again on login/logout to make History user-specific."""
    st.session_state.user_id = user_id
    saved_prefs = db.get_user_preferences(user_id)
    if saved_prefs:
        st.session_state.user_prefs = {
            "diet": saved_prefs.get("diet_type") or "None",
            "allergens": saved_prefs.get("allergies") or [],
            "health_goals": st.session_state.get("user_prefs", {}).get("health_goals", []),
        }
    else:
        st.session_state.user_prefs = {"diet": "None", "allergens": [], "health_goals": []}
    st.session_state.history = _load_history_from_db(user_id)


def do_login(user: dict):
    st.session_state.auth_user = {
        "user_id": user["user_id"], "name": user.get("name") or "", "email": user.get("email") or "",
    }
    _activate_user(user["user_id"])


def do_logout():
    st.session_state.pop("auth_user", None)
    st.query_params.pop("uid", None)
    _activate_user(db.get_or_create_local_user())


def _load_history_from_db(user_id: str) -> list:
    try:
        rows = db.get_scan_history(user_id)
    except Exception:
        return []
    entries = []
    for row in rows:
        entries.append(_scan_row_to_history_entry(row))
    return entries


def _scan_row_to_history_entry(row: dict) -> dict:
    from datetime import datetime
    ai_response = None
    cached = db.get_cached_product(barcode=row.get("barcode"), image_hash=row.get("image_hash"))
    if cached:
        ai_response = cached.get("ai_response")
    result = db.deserialize_result(ai_response)

    try:
        dt = datetime.fromisoformat(row["timestamp"])
    except Exception:
        dt = None

    verdict = row.get("classification") or "Uncertain"
    ingredients = row.get("full_ingredients") or ""
    confidence_raw = row.get("confidence")
    confidence_pct = int(confidence_raw * 100) if isinstance(confidence_raw, (int, float)) else 0

    return {
        "product":     row.get("product_name"),
        "verdict":     verdict,
        "snippet":     ingredients[:70] + "…" if len(ingredients) > 70 else ingredients,
        "ingredients": ingredients,
        "time":        dt.strftime("%H:%M") if dt else "",
        "date":        dt.strftime("%d %b") if dt else "",
        "result":      result,
        "confidence":  int(result.vegan_confidence * 100) if result else confidence_pct,
        "health_score": result.health_score if result else 0,
        "allergens":   result.allergens_detected if result else [],
        "diet_category": getattr(result, "diet_category", verdict) if result else verdict,
    }

def add_history(name, verdict, ingredients, result=None, barcode=None, image_hash=None):
    from datetime import datetime
    entry = {
        "product":     name,
        "verdict":     verdict,
        "snippet":     ingredients[:70] + "…" if len(ingredients) > 70 else ingredients,
        "ingredients": ingredients,
        "time":        datetime.now().strftime("%H:%M"),
        "date":        datetime.now().strftime("%d %b"),
        "result":      result,
        # Extra fields for History page display
        "confidence":  int(result.vegan_confidence * 100) if result else 0,
        "health_score": result.health_score if result else 0,
        "allergens":   result.allergens_detected if result else [],
        "diet_category": getattr(result, "diet_category", verdict) if result else verdict,
    }

    # Persist every successful scan to SQLite regardless of the in-session
    # duplicate check below, so scan/analysis history & analytics stay complete.
    user_id = st.session_state.get("user_id") or db.get_or_create_local_user()
    db.record_scan_and_analysis(user_id, name, ingredients, result, barcode=barcode, image_hash=image_hash)

    # Avoid exact duplicate consecutive entries in the on-screen list
    existing = st.session_state.history
    if existing and existing[0]["product"] == name and existing[0]["snippet"] == entry["snippet"]:
        return  # skip duplicate
    st.session_state.history.insert(0, entry)
    if len(st.session_state.history) > 100:
        st.session_state.history = st.session_state.history[:100]


def log_activity(action: str, page: str = ""):
    """Fire-and-forget usage analytics; never raises into the calling page."""
    user_id = st.session_state.get("user_id") or db.get_or_create_local_user()
    db.log_activity(user_id, action, page)


def hash_image_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def cached_analyze(svc, ingredients_text: str, product_name: str, barcode: str = None, image_hash: str = None):
    """
    Cache-first wrapper around IngredientAnalysisService.analyze().
    Checks product_cache by barcode/image_hash before re-running
    classification; falls back to a normal analyze() call on a miss or
    any cache error, so behavior/output is identical either way.
    """
    if barcode or image_hash:
        cached = db.get_cached_product(barcode=barcode, image_hash=image_hash)
        if cached and cached.get("ai_response"):
            restored = db.deserialize_result(cached["ai_response"])
            if restored is not None:
                return restored
    return svc.analyze(ingredients_text, product_name)


def cached_ocr_extract(ocr, uploaded_file):
    """
    Cache-first wrapper around OCRService.extract_text(). Hashes the image
    bytes and skips the (comparatively expensive) OCR pass entirely if this
    exact image was already processed. Returns (extracted_text, image_hash).
    """
    try:
        data = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
        image_hash = hash_image_bytes(data)
    except Exception:
        return ocr.extract_text(uploaded_file), None

    cached = db.get_cached_product(image_hash=image_hash)
    if cached and cached.get("ingredients"):
        return cached["ingredients"], image_hash

    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    extracted = ocr.extract_text(uploaded_file)
    return extracted, image_hash

# ── Verdict helpers ────────────────────────────────────────────────────────────
def verdict_css(v):
    return {"Vegan":"verdict-vegan","Not Vegan":"verdict-notvegan","Uncertain":"verdict-uncertain"}.get(v,"verdict-unknown")

def verdict_emoji(v):
    return {"Vegan":"✅","Not Vegan":"❌","Uncertain":"⚠️"}.get(v,"❓")

def verdict_color(v):
    return {"Vegan": SAGE["mid"], "Not Vegan": "#e5584a", "Uncertain": "#e0ab3a"}.get(v, SAGE["stone"])

# ── UI renderers ───────────────────────────────────────────────────────────────
def render_verdict_card(result):
    v   = result.overall_vegan
    css = verdict_css(v)
    emj = verdict_emoji(v)
    col = verdict_color(v)
    conf = int(result.vegan_confidence * 100)
    st.markdown(
        f'<div class="{css}">'
        f'<div class="verdict-icon">{emj}</div>'
        f'<div class="verdict-title" style="color:{col}">{v.upper()}</div>'
        f'<div class="verdict-sub">{result.reasoning}</div>'
        f'<div style="margin-top:0.7rem">'
        f'<div style="font-size:0.74rem;color:#a9bdd2;font-weight:500">Confidence: {conf}%</div>'
        f'<div class="conf-bar-bg"><div class="conf-bar" style="width:{conf}%;background:{col}"></div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

def render_metrics(result):
    v   = result.overall_vegan
    col = verdict_color(v)
    nv  = len(result.non_vegan_ingredients)
    al  = len(result.allergens_detected)
    hs  = result.health_score
    tot = len(result.ingredient_results)
    hc  = SAGE["mid"] if hs >= 70 else "#e0ab3a" if hs >= 45 else "#e5584a"
    st.markdown(
        f'<div class="metric-row">'
        f'<div class="metric-card"><div class="metric-icon">{verdict_emoji(v)}</div>'
        f'<div class="metric-num" style="font-size:0.95rem;color:{col}">{v}</div>'
        f'<div class="metric-lbl">Vegan Status</div></div>'
        f'<div class="metric-card"><div class="metric-icon">🧪</div>'
        f'<div class="metric-num">{tot}</div><div class="metric-lbl">Ingredients</div></div>'
        f'<div class="metric-card"><div class="metric-icon">⚠️</div>'
        f'<div class="metric-num" style="color:{"#e5584a" if al > 0 else SAGE["mid"]}">{al}</div>'
        f'<div class="metric-lbl">Allergens</div></div>'
        f'<div class="metric-card"><div class="metric-icon">🏥</div>'
        f'<div class="metric-num" style="color:{hc}">{hs}</div>'
        f'<div class="metric-lbl">Health Score</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def render_health_score(score):
    c = SAGE["mid"] if score >= 70 else "#e0ab3a" if score >= 45 else "#e5584a"
    l = "Excellent" if score >= 85 else "Good" if score >= 70 else "Moderate" if score >= 50 else "Poor"
    st.markdown(
        f'<div class="health-wrap">'
        f'<div class="health-lbl">Health Score</div>'
        f'<div class="health-num" style="color:{c}">{score}'
        f'<span style="font-size:0.9rem;color:{SAGE["stone"]}">/100</span></div>'
        f'<div style="font-size:0.78rem;color:{c};font-weight:600">{l}</div>'
        f'<div class="health-bar-bg"><div class="health-bar" style="width:{score}%;background:{c}"></div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def render_nutriscore(ns):
    if not ns:
        return
    ns = ns.upper()
    if ns not in "ABCDE":
        return
    bg  = {"A": "#1a6b4a", "B": "#5a9a30", "C": "#c8a020", "D": "#c87820", "E": "#e5584a"}
    tc  = {"A": "white",   "B": "white",   "C": "#4a3800", "D": "white",   "E": "white"}
    cols = st.columns(5)
    for i, L in enumerate(["A", "B", "C", "D", "E"]):
        active = "transform:scale(1.2);box-shadow:0 3px 10px rgba(0,0,0,0.2);" if L == ns else "opacity:0.2;"
        with cols[i]:
            st.markdown(
                f'<div style="width:34px;height:42px;background:{bg[L]};border-radius:6px;'
                f'display:flex;align-items:center;justify-content:center;'
                f'font-size:1rem;font-weight:700;color:{tc[L]};{active}">{L}</div>',
                unsafe_allow_html=True,
            )

def render_nutrition_pie(nutriments: dict, key_suffix: str = "", large: bool = False):
    """Responsive pie of the 6 tracked macros — st.columns already stacks
    this beside the classification card on desktop and below it on mobile."""
    # Validated categorical palette (dataviz skill, palette.md slots 1-6) —
    # fixed hue order, never reassigned by rank, passes CVD/lightness/chroma checks.
    fields = [
        ("Energy (kcal)", "energy", "#2a78d6"),
        ("Protein", "protein", "#1baf7a"),
        ("Sugars", "sugars", "#eda100"),
        ("Fiber", "fiber", "#008300"),
        ("Salt", "salt", "#4a3aa7"),
        ("Fat", "fat", "#e34948"),
    ]
    labels, values, colors = [], [], []
    for lbl, key, color in fields:
        v = nutriments.get(key)
        if v:
            labels.append(lbl)
            values.append(float(v))
            colors.append(color)
    if len(values) < 2:
        return
    try:
        import plotly.express as px
        fig = px.pie(names=labels, values=values, hole=0.45,
                     color=labels, color_discrete_sequence=colors)
        fig.update_traces(textposition="inside", textinfo="percent+label", showlegend=True,
                           textfont_size=15 if large else 11)
        fig.update_layout(height=420 if large else 230, margin=dict(t=10, b=0, l=0, r=0),
                           paper_bgcolor="rgba(0,0,0,0)",
                           legend=dict(font=dict(size=13 if large else 10)))
        chart_key = f"nutrition_pie_{key_suffix}_{'_'.join(labels)}"[:150]
        st.plotly_chart(fig, use_container_width=True, key=chart_key)
    except ImportError:
        st.caption("Install plotly for the nutrition chart: `pip install plotly`")


def render_ingredient_cards(results, status_filter=None):
    icons  = {"non-vegan": "❌", "uncertain": "⚠️", "vegan": "✅", "usually vegan": "✅", "usually non-vegan": "❌"}
    css_map = {"non-vegan": "ing-card-nv", "uncertain": "ing-card-unc", "vegan": "ing-card-vegan", "usually vegan": "ing-card-vegan"}
    for r in results:
        if status_filter and r.vegan_status not in status_filter:
            continue
        icon = icons.get(r.vegan_status, "❓")
        css  = css_map.get(r.vegan_status, "")
        alt  = f'<div class="ing-alt">🌱 Alt: {r.alternatives}</div>' if r.alternatives else ""
        st.markdown(
            f'<div class="ing-card {css}">'
            f'<div class="ing-icon">{icon}</div>'
            f'<div><div class="ing-name">{r.name}</div>'
            f'<div class="ing-reason">{r.reason}</div>{alt}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

def render_allergen_pills(allergens):
    if not allergens:
        return
    icons = {"dairy":"🥛","eggs":"🥚","gluten":"🌾","soy":"🫘","peanuts":"🥜",
             "tree nuts":"🌰","fish":"🐟","shellfish":"🦐","sesame":"🌿","wheat":"🌾"}
    st.markdown(
        " ".join(f'<span class="pill pill-red">{icons.get(a,"⚠️")} {a.title()}</span>' for a in allergens),
        unsafe_allow_html=True,
    )

@st.cache_resource(show_spinner=False)
def _get_coordinator_agent():
    """The same Coordinator Agent the MCP server exposes (backend/services/
    coordinator_agent.py) — the floating chat and the MCP tool both route
    through this one decision point rather than each having their own copy
    of the routing logic."""
    from backend.services.product_service import ProductFetchService
    from backend.services.ocr_service import OCRService
    from backend.services.analysis_service import IngredientAnalysisService
    from backend.services.llm_service import IngredientAnalystAgent
    from backend.services.coordinator_agent import CoordinatorAgent
    analysis_svc = IngredientAnalysisService()
    return CoordinatorAgent(
        product_service=ProductFetchService(),
        ocr_service=OCRService(),
        analysis_service=analysis_svc,
        analyst_agent=IngredientAnalystAgent(analysis_svc),
    )


# Keyword → canned answer for questions about using the app itself (as opposed
# to ingredient/nutrition questions, which go to the LLM agent below).
_APP_HELP_FAQ = [
    (("bmi", "body mass"),
     "Your **BMI** is calculated automatically on the Preferences page once you enter "
     "Gender, Age, Height and Weight — it also shows your Daily Calorie and Daily Protein "
     "targets under 'Your Profile'."),
    (("daily target", "daily calor", "calorie target"),
     "Your **Daily Calorie Target** shows in the header on every page once your profile "
     "(gender/age/height/weight) is saved in Preferences (👤)."),
    (("check button", "consumption", "how many calories", "remaining calor", "calories left"),
     "After analyzing a product, click the **Check** button below the results to log it and "
     "see calories/protein/fat/sugar consumed today vs. your daily allowance, with a comparison chart."),
    (("history", "past scan", "previous scan"),
     "Your **History** page (📚) lists every past scan with charts and a JSON export — it's "
     "specific to your signed-in account."),
    (("preference", "allerg", "diet type", "vegan setting", "dietary alert"),
     "Set diet type, allergies and your body profile under **Preferences** (👤) — they're saved "
     "automatically and used to flag conflicts (e.g. a vegan scanning dairy) right after each scan."),
    (("sign up", "sign in", "log in", "login", "account", "register"),
     "Click **🔐 Login** at the top-right of any page to sign in or create an account. "
     "Demo login: test123@gmail.com / test123."),
    (("compare", "comparison"),
     "Use the **Comparison** page (⚖️) to analyze two products side-by-side, including a "
     "nutrition breakdown for each."),
    (("scan", "barcode", "upload", "ocr", "label"),
     "Use the **Scanner** page (📷) to scan a barcode with your camera, upload a label photo "
     "for OCR, or paste ingredients directly."),
]


def _match_app_faq(question: str):
    q = question.lower()
    for keywords, answer in _APP_HELP_FAQ:
        if any(k in q for k in keywords):
            return answer
    return None


def ask_assistant(question: str) -> str:
    """Local app-usage FAQ first (fast, deterministic, no product data
    involved), otherwise routed through the Coordinator Agent — same
    decision point the MCP server's tool uses."""
    faq = _match_app_faq(question)
    if faq:
        return faq
    try:
        result = _get_coordinator_agent().handle(question=question)
        return result.message
    except Exception as e:
        return f"Sorry, I couldn't process that right now ({e})."


def render_floating_assistant():
    """Global floating chat FAB (bottom-right) — replaces the AI Assistant nav
    page. Answers both ingredient questions (via the existing LLM agent) and
    app-usage questions (via a small local FAQ), without touching either."""
    if "ai_widget_open" not in st.session_state:
        st.session_state.ai_widget_open = False
    if "ai_widget_messages" not in st.session_state:
        st.session_state.ai_widget_messages = []

    st.markdown(
        """
        <style>
        .st-key-ai_fab_btn {
            position: fixed !important; bottom: 24px; right: 24px; z-index: 10000;
            width: 58px !important; height: 58px !important;
        }
        .st-key-ai_fab_btn .stButton>button {
            width: 58px; height: 58px; border-radius: 50% !important;
            font-size: 2rem !important; padding: 0 !important;
            box-shadow: 0 6px 22px rgba(23,201,168,0.4) !important;
            transition: transform .22s ease !important;
        }
        .st-key-ai_fab_btn .stButton>button:hover { transform: scale(1.08) translateY(-2px) !important; }
        .st-key-ai_panel {
            position: fixed; bottom: 92px; right: 24px; z-index: 9999;
            width: 350px; max-width: 88vw; max-height: 60vh; overflow-y: auto;
            background: var(--background-color, #101d2e); border-radius: 16px;
            box-shadow: 0 14px 44px rgba(0,0,0,0.45); border: 1px solid rgba(102,214,235,0.18);
            padding: 12px 14px 6px; animation: ilSlideUp .28s cubic-bezier(.2,.9,.3,1);
        }
        @keyframes ilSlideUp {
            from { opacity: 0; transform: translateY(18px) scale(0.97); }
            to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        @media (max-width: 640px) {
            .st-key-ai_panel { right: 12px; bottom: 84px; width: 82vw; }
            .st-key-ai_fab_btn { right: 14px; bottom: 14px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="ai_fab_btn"):
        if st.button("✕" if st.session_state.ai_widget_open else "💬", key="ai_fab_toggle_btn"):
            st.session_state.ai_widget_open = not st.session_state.ai_widget_open
            st.rerun()

    if not st.session_state.ai_widget_open:
        return

    with st.container(key="ai_panel"):
        st.markdown(
            f'<div style="font-weight:700;font-size:0.92rem;color:{SAGE["charcoal"]};'
            f'margin-bottom:6px">🤖 IngreLens Assistant</div>',
            unsafe_allow_html=True,
        )
        if not st.session_state.ai_widget_messages:
            st.caption("Ask about ingredients, allergens, or how to use the app (BMI, History, Check, Preferences…).")
        for msg in st.session_state.ai_widget_messages[-8:]:
            with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
                st.markdown(msg["content"])

        q = st.chat_input("Ask a question…", key="ai_widget_input")
        if q:
            st.session_state.ai_widget_messages.append({"role": "user", "content": q})
            with st.spinner("Thinking…"):
                ans = ask_assistant(q)
            st.session_state.ai_widget_messages.append({"role": "assistant", "content": ans})
            st.rerun()


def render_agent_row():
    """Names here match backend/services/coordinator_agent.py and README.md
    exactly — one Coordinator that routes to whichever of the 5 specialists
    a given request actually needs (see CoordinatorAgent.handle)."""
    st.markdown(
        f'<div style="margin:0.5rem 0 1rem">'
        f'<span class="agent-badge">🧭 Coordinator Agent</span>'
        f'<span class="agent-badge">📦 Product Fetch Agent</span>'
        f'<span class="agent-badge">👁️ OCR Agent</span>'
        f'<span class="agent-badge">🏷️ Classification Agent</span>'
        f'<span class="agent-badge">📊 Nutrition Agent</span>'
        f'<span class="agent-badge">🤖 AI Analyst Agent</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

DEFAULT_DAILY_TARGET = 2000  # kcal — used whenever no BMI-based target is set


def _get_daily_target(user_id: str) -> dict:
    """User-specific calorie/protein target from their BMI profile if set,
    else a flat sensible default so Food Log features always work."""
    profile = db.get_user_preferences(user_id) or {}
    targets = db.compute_bmi_and_targets(
        profile.get("gender"), profile.get("age"), profile.get("height_cm"), profile.get("weight_kg")
    )
    if targets:
        return targets
    return {"daily_calories": DEFAULT_DAILY_TARGET, "daily_protein": round(DEFAULT_DAILY_TARGET * 0.15 / 4)}


def _parse_quantity(product: dict):
    """Best-effort unit-mode detection from a product's quantity/serving
    string ('400g' -> weight, '1.5L' -> weight (liquid, normalized to ml),
    '6 pieces' -> count). Falls back to the standard 100g/100ml reference
    basis nutriments are already stored in."""
    qty_str = str((product or {}).get("quantity") or (product or {}).get("serving_size") or "").lower()
    count_units = [("slice", "slices"), ("piece", "pieces"), ("pcs", "pieces"),
                   ("bar", "bars"), ("cookie", "cookies"), ("biscuit", "biscuits"), ("item", "items")]
    for kw, label in count_units:
        if kw in qty_str:
            m = re.search(r"(\d+(?:\.\d+)?)", qty_str)
            return "count", (float(m.group(1)) if m else 1.0), label
    # Liters -> normalize to ml (1L = 1000ml) so the same per-100ml basis applies
    m = re.search(r"(\d+(?:\.\d+)?)\s*l(?:iters?|itres?)?\b", qty_str)
    if m and "ml" not in qty_str:
        return "weight", float(m.group(1)) * 1000, "ml"
    m = re.search(r"(\d+(?:\.\d+)?)\s*ml\b", qty_str)
    if m:
        return "weight", float(m.group(1)), "ml"
    m = re.search(r"(\d+(?:\.\d+)?)\s*g\b", qty_str)
    if m:
        return "weight", float(m.group(1)), "g"
    return "weight", 100.0, "g"


@st.dialog("How much did you consume?")
def _show_portion_dialog(name: str, nm: dict, product: dict, btn_key: str):
    mode, total_units, unit_label = _parse_quantity(product)
    user_id = st.session_state.get("user_id")

    if mode == "weight":
        # Let the user pick g / ml / L explicitly rather than trusting
        # auto-detection alone — L is normalized to ml (1L = 1000ml) since
        # nutriments are stored on a per-100g/100ml basis either way.
        unit_options = ["g", "ml", "L"]
        default_idx = unit_options.index(unit_label) if unit_label in unit_options else 0
        uc1, uc2 = st.columns([2, 1])
        with uc2:
            chosen_unit = st.selectbox("Unit", unit_options, index=default_idx,
                                        key=f"portion_unit_{btn_key}", label_visibility="collapsed")
        with uc1:
            st.caption(f"Nutrition values are per 100{unit_label}. Enter how much you actually consumed.")
        if chosen_unit == "L":
            default_amt, max_amt, step_amt = 0.1, 5.0, 0.1
        else:
            default_amt = min(float(total_units), 100.0) if chosen_unit == unit_label else 100.0
            max_amt, step_amt = 2000.0, 5.0
        consumed = st.number_input(
            f"Amount consumed ({chosen_unit})", min_value=0.0, max_value=max_amt,
            value=default_amt, step=step_amt, key=f"portion_amt_{btn_key}_{chosen_unit}",
        )
        # Normalize to the same 100g/100ml basis nutriments are stored in
        consumed_normalized = consumed * 1000 if chosen_unit == "L" else consumed
        ratio = consumed_normalized / 100.0
        unit_label = chosen_unit  # for display + what gets logged
    else:
        st.caption(f"This package is about {total_units:g} {unit_label}.")
        consumed = st.number_input(
            f"How many {unit_label} did you eat?", min_value=0.0, max_value=total_units * 10,
            value=1.0, step=1.0, key=f"portion_amt_{btn_key}",
        )
        ratio = (consumed / total_units) if total_units else 0.0

    ratio = max(0.0, ratio)
    calories = (nm.get("energy") or 0) * ratio
    protein  = (nm.get("protein") or 0) * ratio
    fat      = (nm.get("fat") or 0) * ratio
    sugar    = (nm.get("sugars") or 0) * ratio

    targets = _get_daily_target(user_id)
    daily_before = db.get_daily_consumption(user_id)
    total_after = daily_before["calories"] + calories
    remaining_after = max(targets["daily_calories"] - total_after, 0)
    pct_of_day = min(100, round(total_after / targets["daily_calories"] * 100)) if targets["daily_calories"] else 0

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("This portion", f"{calories:.0f} kcal")
    c2.metric("Protein", f"{protein:.1f}g")
    c3.metric("Fat", f"{fat:.1f}g")
    st.caption(
        f"If logged: **{total_after:.0f} / {targets['daily_calories']} kcal** today "
        f"({pct_of_day}% of target) · **{remaining_after:.0f} kcal** would remain"
    )

    try:
        import plotly.express as px
        fig = px.pie(
            names=["Consumed (incl. this)", "Remaining"],
            values=[pct_of_day, max(100 - pct_of_day, 0)],
            hole=0.5, color=["Consumed (incl. this)", "Remaining"],
            color_discrete_map={"Consumed (incl. this)": "#e34948", "Remaining": "#1baf7a"},
        )
        fig.update_traces(textinfo="percent+label")
        fig.update_layout(height=220, margin=dict(t=10, b=0, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, key=f"portion_pie_{btn_key}")
    except ImportError:
        pass

    st.markdown("**Meal**")
    meal_type = st.radio(
        "Meal", ["Breakfast", "Lunch", "Snack", "Dinner"], index=None,
        key=f"portion_meal_{btn_key}", horizontal=True, label_visibility="collapsed",
    )
    if meal_type is None:
        st.caption("⬆️ Select a meal before adding to your Food Log.")

    if st.button("➕ Add to Food Log", key=f"add_food_log_{btn_key}", type="primary",
                 use_container_width=True, disabled=meal_type is None):
        db.log_consumption(
            user_id, name, calories=calories, protein=protein, fat=fat, sugar=sugar,
            quantity=consumed, unit=unit_label, meal_type=meal_type,
        )
        log_activity("Food Log Add", "Analysis")
        st.session_state.pop(f"_consumption_open_{btn_key}", None)  # don't reopen this dialog on return
        st.session_state["_scroll_to_quick_actions"] = True
        st.toast("✅ Added to your food logs", icon="✅")
        st.switch_page("app.py")

    # Streamlit dialogs have no "on close" callback, so the native X button
    # can't clear our own "is this open" flag — an explicit Cancel gives
    # users a reliable way to dismiss it without it popping back up the next
    # time they interact with anything else on the page.
    if st.button("Cancel", key=f"cancel_portion_{btn_key}", use_container_width=True):
        st.session_state.pop(f"_consumption_open_{btn_key}", None)
        st.rerun()


def render_consumption_checker(result, product=None, key_suffix=""):
    """'Check' button below scan results. Gates on login first (no BMI/portion
    screens are shown to a logged-out user), then opens a portion-size modal
    that computes proportional nutrition for what was actually eaten — not
    the whole package — before offering to add it to the Food Log."""
    nm = (product or {}).get("nutriments", {}) or {}
    if not any(nm.values()):
        return
    name = getattr(result, "product_name", "Product")
    btn_key = f"check_consumption_{key_suffix}_{name}"[:150]
    open_key = f"_consumption_open_{btn_key}"

    if st.button("✅ Check Daily Consumption", key=btn_key,
                 help="See how this fits into today's intake before logging it"):
        st.session_state[open_key] = True

    if not st.session_state.get(open_key):
        return

    if not st.session_state.get("auth_user"):
        st.warning("🔒 Please log in to continue tracking your daily consumption")
        with st.form(key=f"inline_login_{btn_key}"):
            email = st.text_input("Email", key=f"il_email_{btn_key}")
            pw = st.text_input("Password", type="password", key=f"il_pw_{btn_key}")
            submitted = st.form_submit_button("Sign In")
        if submitted:
            user = db.authenticate(email, pw)
            if user:
                do_login(user)
                st.rerun()
            else:
                st.error("Invalid email or password.")
        return

    _show_portion_dialog(name, nm, product or {}, btn_key)


def render_dietary_alerts(result):
    """Cross-check this analysis against the signed-in user's saved diet/allergies."""
    prefs = st.session_state.get("user_prefs", {})
    # diet_modes (new multi-select) takes precedence; fall back to the old
    # single "diet" string so sessions saved before the multi-select change
    # still trigger the same conflict checks.
    diet_modes = prefs.get("diet_modes") or ([prefs["diet"]] if prefs.get("diet") and prefs.get("diet") != "None" else [])
    user_allergens = [a.lower() for a in prefs.get("allergens", [])]
    detected_allergens = [a.lower() for a in (result.allergens_detected or [])]
    diet_category = getattr(result, "diet_category", result.overall_vegan)

    conflicts = []
    for diet in diet_modes:
        if diet == "Vegan" and diet_category != "Vegan":
            conflicts.append(f"You follow a **Vegan** diet, but this product is classified **{diet_category}**.")
        elif diet == "Vegetarian" and diet_category == "Non-Vegetarian":
            conflicts.append(f"You follow a **Vegetarian** diet, but this product is **{diet_category}**.")
        elif diet == "Dairy-Free" and any("dairy" in a or "milk" in a for a in detected_allergens):
            conflicts.append("You've set **Dairy-Free**, but dairy was detected in this product.")
        elif diet == "Nut-Free" and any("nut" in a for a in detected_allergens):
            conflicts.append("You've set **Nut-Free**, but nuts were detected in this product.")

    for ua in user_allergens:
        for da in detected_allergens:
            if ua == da or ua in da or da in ua or (ua == "tree nuts" and "nut" in da):
                conflicts.append(f"Contains **{da.title()}** — matches your saved **{ua.title()}** allergy.")
                break

    conflicts = list(dict.fromkeys(conflicts))
    if conflicts:
        items = "".join(f'<div style="font-size:0.86rem;color:#ff9686;margin:3px 0">• {c}</div>' for c in conflicts)
        st.markdown(
            f'<div style="background:rgba(229,88,74,0.14);border-left:5px solid #e5584a;border-radius:12px;'
            f'padding:1rem 1.2rem;margin-bottom:1rem">'
            f'<div style="font-weight:700;color:#ff9686;margin-bottom:6px">🚨 Dietary Conflict Alert</div>'
            f'{items}</div>',
            unsafe_allow_html=True,
        )


def _scroll_to_anchor(anchor_id: str):
    """Smooth-scrolls the real page (not the sandboxed iframe) to a given
    element id. st.markdown's HTML doesn't execute <script> tags (React's
    dangerouslySetInnerHTML leaves them inert), so this uses
    components.v1.html — its iframe DOES run scripts — and reaches back out
    to the parent document, which is where the actual page content lives."""
    import streamlit.components.v1 as components
    components.html(
        f"""<script>
        (function() {{
            const doc = window.parent.document;
            const el = doc.getElementById('{anchor_id}');
            if (el) {{ el.scrollIntoView({{behavior:'smooth', block:'start'}}); }}
        }})();
        </script>""",
        height=0,
    )


def scroll_sequence(steps: list):
    """Chained smooth-scrolls, e.g. [("hero-id", 400), ("cta-id", 2500)]
    scrolls to hero after 400ms, then to the CTA 2.5s after that — giving the
    hero a moment of focus before moving on. Delays are cumulative."""
    import streamlit.components.v1 as components
    js_steps = []
    cumulative = 0
    for anchor_id, delay_ms in steps:
        cumulative += delay_ms
        js_steps.append(
            f"""setTimeout(function() {{
                const el = doc.getElementById('{anchor_id}');
                if (el) {{ el.scrollIntoView({{behavior:'smooth', block:'start'}}); }}
            }}, {cumulative});"""
        )
    components.html(
        f"<script>(function(){{const doc = window.parent.document;{''.join(js_steps)}}})();</script>",
        height=0,
    )


def full_analysis_display(result, product=None, key_suffix="main"):
    # Smooth-scroll to the results the first time THIS analysis renders (not
    # on every later rerun within the same page, e.g. clicking Check Daily
    # Consumption below) — gated on a per-(page, product) flag.
    name_id = getattr(result, "product_name", "") or (product or {}).get("name", "")
    anchor_id = f"il-analysis-{key_suffix}".replace(" ", "_")
    scroll_flag = f"_scrolled_{key_suffix}_{name_id}"
    st.markdown(f'<div id="{anchor_id}"></div>', unsafe_allow_html=True)
    if not st.session_state.get(scroll_flag):
        st.session_state[scroll_flag] = True
        _scroll_to_anchor(anchor_id)

    render_dietary_alerts(result)

    nm = (product or {}).get("nutriments", {}) or {}
    has_nutrition = any(nm.values())

    if has_nutrition:
        # Classification card + Nutrition Pie Chart — 50/50 on desktop,
        # stacked on mobile (st.columns' default responsive behavior).
        cls_col, chart_col = st.columns([1, 1])
        with cls_col:
            render_verdict_card(result)
        with chart_col:
            render_nutrition_pie(nm, key_suffix=key_suffix, large=True)

        st.markdown('<div class="shdr">Nutrition / 100g</div>', unsafe_allow_html=True)
        def fmt(v, u="g"):
            return f"{float(v):.1f} {u}" if v is not None else "—"
        nut_fields = [
            ("🔥 Energy","energy","kcal"), ("🫀 Fat","fat","g"),
            ("🍬 Sugars","sugars","g"),    ("💪 Protein","protein","g"),
            ("🧂 Salt","salt","g"),         ("🌾 Fiber","fiber","g"),
        ]
        nut_cols = st.columns(len(nut_fields))
        for col, (lbl, key, unit) in zip(nut_cols, nut_fields):
            with col:
                st.caption(lbl)
                st.markdown(f"**{fmt(nm.get(key), unit)}**")
    else:
        render_verdict_card(result)

    render_agent_row()
    render_metrics(result)

    left, right = st.columns([3, 2])

    with left:
        nv  = [r for r in result.ingredient_results if "non-vegan" in r.vegan_status]
        unc = [r for r in result.ingredient_results if r.vegan_status == "uncertain"]
        ok  = [r for r in result.ingredient_results if r.vegan_status in ("vegan", "usually vegan")]

        if nv:
            st.markdown('<div class="shdr">❌ Non-Vegan Ingredients</div>', unsafe_allow_html=True)
            render_ingredient_cards(result.ingredient_results, {"non-vegan", "usually non-vegan"})

        if unc:
            st.markdown('<div class="shdr">⚠️ Uncertain — Verify with Manufacturer</div>', unsafe_allow_html=True)
            render_ingredient_cards(result.ingredient_results, {"uncertain"})

        if ok:
            st.markdown(f'<div class="shdr">✅ Vegan Ingredients ({len(ok)})</div>', unsafe_allow_html=True)
            render_ingredient_cards(ok[:10], None)
            if len(ok) > 10:
                with st.expander(f"Show {len(ok) - 10} more"):
                    render_ingredient_cards(ok[10:], None)

        if result.allergens_detected:
            st.markdown('<div class="shdr">⚠️ Allergens</div>', unsafe_allow_html=True)
            render_allergen_pills(result.allergens_detected)

        for f in result.health_flags:
            st.warning(f"⚠️ {f}")

        for rec in result.recommendations:
            st.info(f"💡 {rec}")

    with right:
        render_health_score(result.health_score)

        if product:
            if product.get("nutriscore"):
                st.markdown('<div class="shdr">Nutri-Score</div>', unsafe_allow_html=True)
                render_nutriscore(product["nutriscore"])

            if product.get("allergens"):
                st.markdown('<div class="shdr">Package Allergen Warnings</div>', unsafe_allow_html=True)
                render_allergen_pills(product["allergens"])

            render_consumption_checker(result, product, key_suffix=key_suffix)

        if result.ultra_processed_markers:
            st.markdown('<div class="shdr">🏭 Ultra-Processed</div>', unsafe_allow_html=True)
            st.markdown(" ".join(f'<span class="pill pill-orange">{m}</span>' for m in result.ultra_processed_markers), unsafe_allow_html=True)

        if result.preservatives:
            st.markdown('<div class="shdr">🧪 Preservatives</div>', unsafe_allow_html=True)
            st.markdown(" ".join(f'<span class="pill pill-blue">{p}</span>' for p in result.preservatives), unsafe_allow_html=True)
