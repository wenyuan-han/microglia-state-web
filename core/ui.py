import streamlit as st


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
        .block-container {padding-top: 1.8rem; padding-bottom: 3rem;}
        [data-testid="stMetricValue"] {font-size: 1.55rem;}
        .micro-card {
            border: 1px solid rgba(128,128,128,.22);
            border-radius: 14px;
            padding: 16px 18px;
            margin-bottom: 12px;
        }
        .micro-muted {opacity: .72;}
        .micro-kicker {
            font-size: .78rem;
            letter-spacing: .08em;
            text-transform: uppercase;
            opacity: .65;
            font-weight: 650;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(kicker: str, title: str, description: str):
    st.markdown(f'<div class="micro-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.title(title)
    st.caption(description)


def missing_cache_notice():
    st.warning(
        "Web cache 尚未生成。请先在项目根目录运行："
        "`python webapp/scripts/build_web_data.py`"
    )
