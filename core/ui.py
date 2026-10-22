"""Shared presentation primitives for the Microglia Transition Explorer.

Visual-only module. It does not change model outputs or data processing.
"""
from __future__ import annotations

from html import escape
import streamlit as st


ACCENT = "#4966E9"
TEAL = "#078C91"
INK = "#17243E"


def init_session_state():
    defaults = {
        "selected_donor": "All",
        "selected_stage": "All",
        "selected_region": "All",
        "selected_program": "P1",
        "selected_dag_version": "DAG-v2",
        "selected_mechanism": "NLRP3",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def inject_global_css():
    st.markdown(
        """
        <style>
        :root {
          --micro-accent: #4966E9;
          --micro-teal: #078C91;
          --micro-ink: #17243E;
          --micro-muted: #66758D;
          --micro-border: #E4EAF4;
        }
        .stApp {
          background: radial-gradient(circle at 92% 0%, #EFF4FF 0, transparent 31%),
                      #F7F9FD;
        }
        .block-container {
          max-width: 1440px;
          padding-top: 2.1rem;
          padding-bottom: 4.5rem;
        }
        [data-testid="stSidebar"] {
          background: linear-gradient(180deg, #15233F 0%, #101B31 100%);
          border-right: 1px solid #253753;
        }
        [data-testid="stSidebar"] * {color: #EAF0FC;}
        [data-testid="stSidebar"] [data-testid="stSidebarNav"] {padding-top: .8rem;}
        [data-testid="stSidebar"] a[aria-current="page"],
        [data-testid="stSidebar"] [aria-selected="true"] {
          background: rgba(129,151,252,.20) !important;
          border-radius: 9px;
        }
        .micro-brand {padding: .25rem .4rem 1.25rem;}
        .micro-brand-mark {
          display:inline-block; width: 10px; height: 10px; border-radius: 3px;
          background: linear-gradient(135deg,#77D8D4,#8EA0FF);
          margin-right: 8px;
        }
        .micro-brand-title {
          font-size: 1.03rem; font-weight: 780; letter-spacing: .025em;
          color: #F4F7FF !important;
        }
        .micro-brand-subtitle {font-size: .76rem; color: #AFC0E3 !important; margin-top: .32rem;}
        .micro-hero {
          border: 1px solid #DBE4F5;
          background: linear-gradient(118deg,#FFFFFF 0%,#F4F7FF 68%,#ECF9F9 100%);
          border-radius: 20px;
          padding: clamp(1.2rem,2.6vw,2.1rem) clamp(1.2rem,3vw,2.6rem);
          box-shadow: 0 7px 28px rgba(26,45,93,.045);
          margin-bottom: 1.25rem;
        }
        .micro-kicker {
          display: inline-block; color: #4966E9;
          font-size: .73rem; font-weight: 790; letter-spacing: .125em;
          text-transform: uppercase; margin-bottom: .65rem;
        }
        .micro-hero h1 {
          font-size: clamp(1.9rem,3.3vw,2.7rem);
          line-height: 1.19; margin: 0 0 .55rem;
          letter-spacing: -.038em; font-weight: 780;
          color: #17243E;
        }
        .micro-hero p {margin:0; max-width: 780px; color:#60718D; font-size:.965rem; line-height:1.65;}
        .micro-section {
          display: flex; align-items: baseline; gap: .7rem;
          margin: 1.55rem 0 .75rem;
        }
        .micro-section-num {
          color:#7385D9; font-size:.75rem; font-weight:800;
          background:#EAF0FF; padding:.23rem .5rem;
          border-radius: 6px;
        }
        .micro-section-title {font-size: 1.15rem; font-weight: 760; letter-spacing: -.015em; color:#17243E;}
        .micro-section-desc {color:#76849B;font-size:.82rem;margin: -.35rem 0 1rem;}
        .micro-note {
          padding:.78rem 1rem; border:1px solid #DFE6F2;
          border-left:3px solid #078C91; background: #F8FBFD;
          color:#52637E; border-radius: 9px; font-size: .865rem;
          line-height:1.55; margin:.75rem 0;
        }
        .micro-note strong {color:#213859;}
        .micro-workflow {font-size:.86rem;color:#50607B;padding:1rem 1.15rem;
          border-radius:12px;border:1px solid #E4EAF4;background:#FFF;line-height:1.9;}
        .micro-workflow strong{color:#263D65}
        .micro-step {color:#4966E9;font-weight:750;}
        .micro-tile {
          border:1px solid #E4EAF4; border-radius:14px;
          background:#fff; padding:1.12rem 1.15rem;
          box-shadow: 0 4px 18px rgba(23,36,62,.027);
          min-height:144px; margin-bottom:.4rem;
        }
        .micro-tile-label {font-size:.72rem;font-weight:800;letter-spacing:.08em;color:#078C91;margin-bottom:.48rem}
        .micro-tile-title {font-size:1.03rem;font-weight:760;color:#17243E;margin-bottom:.42rem}
        .micro-tile-desc {font-size:.84rem;color:#6E7C95;line-height:1.55}
        .micro-footer {font-size:.75rem;color:#8995A8;border-top:1px solid #E4EAF4;
          padding-top:.9rem;margin-top:2.2rem;}
        [data-testid="stMetric"] {
          border: 1px solid var(--micro-border); border-radius: 13px;
          background: #FFFFFF;
          padding: 1rem 1.12rem;
          box-shadow: 0 3px 14px rgba(23,36,62,.024);
        }
        [data-testid="stMetricLabel"] {color:#71819A; font-weight:610;}
        [data-testid="stMetricValue"] {font-size:1.63rem; color:#17243E;font-weight:760;}
        [data-testid="stVerticalBlockBorderWrapper"] {
          border-radius: 13px;
          border-color: #E3E9F4;
          background: #FFFFFF;
        }
        div[data-testid="stFileUploader"] {border-radius:12px;}
        div[data-testid="stFileUploaderDropzone"] {
          background: #F8FAFF; border:1.5px dashed #C6D3EE;
          border-radius:12px;
        }
        div.stButton > button[kind="primary"],
        div.stDownloadButton > button[kind="primary"] {
          border-radius:10px; font-weight:700;
          box-shadow: 0 5px 13px rgba(73,102,233,.17);
        }
        div.stButton > button, div.stDownloadButton > button {border-radius:10px;}
        [data-testid="stDataFrame"] {border-radius:12px;overflow:hidden;}
        [data-testid="stAlert"] {border-radius:11px;}
        h2,h3 {letter-spacing:-.02em;}
        @media(max-width:760px) {
          .block-container {padding-top:1.1rem;padding-left:1rem;padding-right:1rem;}
          .micro-hero {padding: 1.2rem; border-radius:14px;}
          .micro-section {margin-top:1.15rem;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.sidebar:
        st.markdown(
            '<div class="micro-brand">'
            '<div class="micro-brand-title"><span class="micro-brand-mark"></span> MICROGLIA LAB</div>'
            '<div class="micro-brand-subtitle">State · Mechanism · Simulation</div>'
            '</div>',
            unsafe_allow_html=True,
        )


def page_header(kicker: str, title: str, description: str):
    st.markdown(
        '<div class="micro-hero">'
        f'<span class="micro-kicker">{escape(kicker)}</span>'
        f'<h1>{escape(title)}</h1>'
        f'<p>{escape(description)}</p>'
        '</div>',
        unsafe_allow_html=True,
    )


def section_header(number: str, title: str, description: str = ""):
    st.markdown(
        '<div class="micro-section">'
        f'<span class="micro-section-num">{escape(number)}</span>'
        f'<span class="micro-section-title">{escape(title)}</span>'
        '</div>'
        + (f'<div class="micro-section-desc">{escape(description)}</div>' if description else ''),
        unsafe_allow_html=True,
    )


def note(text: str):
    st.markdown(f'<div class="micro-note">{escape(text)}</div>', unsafe_allow_html=True)


def tile(kicker: str, title: str, description: str):
    st.markdown(
        '<div class="micro-tile">'
        f'<div class="micro-tile-label">{escape(kicker)}</div>'
        f'<div class="micro-tile-title">{escape(title)}</div>'
        f'<div class="micro-tile-desc">{escape(description)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def footer():
    st.markdown(
        '<div class="micro-footer">Research use only · Exploratory analysis does not establish causal effects or clinical validity.</div>',
        unsafe_allow_html=True,
    )


def apply_figure_style(fig, *, height=None):
    fig.update_layout(
        font=dict(family="Inter, Segoe UI, Arial", color="#344563", size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=["#4966E9", "#078C91", "#E69C42", "#8778D0", "#63A7D7"],
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#17243E", font_color="#FFFFFF"),
    )
    if height is not None:
        fig.update_layout(height=height)
    fig.update_xaxes(gridcolor="#EDF1F7", zerolinecolor="#E0E7F2", linecolor="#DAE3F0")
    fig.update_yaxes(gridcolor="#EDF1F7", zerolinecolor="#E0E7F2", linecolor="#DAE3F0")
    return fig


def missing_cache_notice():
    st.info("Visualization data is not available. Generate the web cache locally with `python webapp/scripts/build_web_data.py`.")
