from pathlib import Path
import sys
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(
    page_title="Microglia Transition Explorer | Research Workspace",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core.ui import inject_global_css, init_session_state

inject_global_css()
init_session_state()

# Existing file paths are retained so bookmarked page URLs remain unchanged.
pages = {
    "Discover": [
        st.Page("pages/overview.py", title="Overview", icon=":material/dashboard:", default=True),
    ],
    "Explore": [
        st.Page("pages/microglia_atlas.py", title="Microglia Atlas", icon=":material/bubble_chart:"),
        st.Page("pages/dag_explorer.py", title="Mechanistic DAG", icon=":material/account_tree:"),
    ],
    "Simulate": [
        st.Page("pages/data_simulation.py", title="Data & Simulation", icon=":material/biotech:"),
        st.Page("pages/state_transport.py", title="State Transport", icon=":material/route:"),
        st.Page("pages/virtual_intervention.py", title="Virtual Intervention", icon=":material/tune:"),
    ],
    "Evaluate": [
        st.Page("pages/external_evidence.py", title="External Evidence", icon=":material/science:"),
    ],
}

navigation = st.navigation(pages, position="sidebar")
navigation.run()
