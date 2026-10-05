import streamlit as st

from core.loaders import load_cells, load_donors, load_dag_v2, load_manifest
from core.plotting import stage_state_box
from core.ui import page_header, missing_cache_notice


page_header(
    "Microglia state-transition platform",
    "Microglia Transition Explorer",
    "SEA-AD 小胶质细胞状态、机制图、分布输运和虚拟干预的交互式研究入口。",
)

cells = load_cells()
donors = load_donors()
dag = load_dag_v2()
manifest = load_manifest()

if cells.empty:
    missing_cache_notice()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Web cells", f"{len(cells):,}")
c2.metric("Donors", f"{donors['donor'].nunique():,}" if "donor" in donors.columns else f"{len(donors):,}")
c3.metric("Selected Programs", "5")
c4.metric("Frozen DAG-v2 edges", f"{len(dag):,}")

st.markdown("### Research workflow")
st.markdown(
    """
    **SEA-AD → Microglia Programs → Continuous state → Evidence-audited hierarchical graph → Frozen DAG-v2 → Distribution transport → Mechanism-transmission intervention → External concordance**
    """
)

left, right = st.columns([1.25, 1])

with left:
    if not donors.empty and {"disease_stage", "continuous_state"}.issubset(donors.columns):
        st.plotly_chart(stage_state_box(donors), use_container_width=True)
    elif not cells.empty and {"disease_stage", "continuous_state"}.issubset(cells.columns):
        st.plotly_chart(stage_state_box(cells), use_container_width=True)
    else:
        st.info("Continuous-state summary 尚未进入 web cache。")

with right:
    st.markdown("### Frozen biological focus")
    st.markdown(
        """
        - **P1 / P4 / P6 / P7 / P10**：当前选定的 microglial molecular Programs  
        - **NLRP3 / TFEB / TREM2-SYK / APOE-LXR**：DAG-v2 机制层节点  
        - 当前网页中的“trajectory”均指**病理关联状态空间中的模型路径**，不是单细胞纵向追踪。
        """
    )

    if manifest:
        st.markdown("### Cache build")
        st.code(
            "\n".join(
                [
                    f"built_at: {manifest.get('built_at', 'unknown')}",
                    f"source_h5ad: {manifest.get('source_h5ad', 'unknown')}",
                    f"sampled_cells: {manifest.get('sampled_cells', 'unknown')}",
                ]
            )
        )

st.markdown("### What to explore next")
a, b, c = st.columns(3)
with a:
    st.info("**Microglia Atlas**\n\n按 disease stage / region / donor 浏览 UMAP 与 Program 活性。")
with b:
    st.info("**Mechanistic DAG**\n\n切换 DAG-v1/v2，并逐边查看 STEP31–33 证据状态。")
with c:
    st.info("**Virtual Intervention**\n\n后续接入 STEP35A 后，可调机制节点干预强度并查看 ΔProgram。")
