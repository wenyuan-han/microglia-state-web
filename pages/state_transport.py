import pandas as pd
import plotly.express as px
import streamlit as st

from core.loaders import (
    load_transport_pair_metrics,
    load_transport_model_metrics,
    load_transport_gain_decomposition,
    load_transport_statistics,
)
from core.ui import page_header

page_header(
    "Frozen DAG-v2 generative audit",
    "State Transport",
    "展示 STEP34B 的 matched distribution-level transport：Frozen no-graph Base、DAG-v1、证据校准 DAG-v2 与 degree-matched Rewired-v2。SEA-AD 为横断面数据，因此这里表示分布输运而非同一细胞的纵向轨迹。",
)

model_df = load_transport_model_metrics()
pair_df = load_transport_pair_metrics()
gain_df = load_transport_gain_decomposition()
stats_df = load_transport_statistics()

if model_df.empty and pair_df.empty:
    st.info("尚未找到 STEP34B web cache。请在本地运行 `python webapp/scripts/build_web_data.py` 后重新部署。")
    st.stop()

# Prefer the already aggregated STEP34B table.
if not model_df.empty and {"model", "metric"}.issubset(model_df.columns):
    value_col = "mean" if "mean" in model_df.columns else next(
        (c for c in model_df.columns if pd.api.types.is_numeric_dtype(model_df[c])), None
    )
    metrics = model_df["metric"].dropna().astype(str).unique().tolist()
    preferred = [
        "mean_mse_generated_target",
        "mean_pcc_generated_target",
        "shift_cosine",
        "program_mse_generated_target",
        "program_shift_cosine",
    ]
    ordered = [m for m in preferred if m in metrics] + [m for m in metrics if m not in preferred]
    metric = st.selectbox("Transport metric", ordered)
    sub = model_df[model_df["metric"].astype(str) == metric].copy()
    if value_col:
        fig = px.bar(sub, x="model", y=value_col, text_auto=".4f", title=f"Held-out mean: {metric}")
        fig.update_layout(height=420, xaxis_title="Model", yaxis_title=metric)
        st.plotly_chart(fig, use_container_width=True)

        cols = st.columns(min(4, max(1, len(sub))))
        for col, (_, row) in zip(cols, sub.head(len(cols)).iterrows()):
            col.metric(str(row["model"]), f"{float(row[value_col]):.4f}")
else:
    st.markdown("### Pair-level transport metrics")

st.markdown("### Gain decomposition")
if gain_df.empty:
    st.caption("34B_gain_decomposition.csv 未进入 cache。")
else:
    # STEP34B defines positive gain as improvement; keep the original columns visible.
    numeric_cols = [c for c in gain_df.columns if pd.api.types.is_numeric_dtype(gain_df[c])]
    if "metric" in gain_df.columns and numeric_cols:
        melt_cols = [c for c in numeric_cols if c not in {"n_pairs"}]
        if melt_cols:
            long = gain_df.melt(id_vars=["metric"], value_vars=melt_cols, var_name="gain_type", value_name="gain")
            fig = px.bar(long, x="metric", y="gain", color="gain_type", barmode="group")
            fig.update_layout(height=440, xaxis_title="", yaxis_title="Positive = improvement")
            st.plotly_chart(fig, use_container_width=True)
    with st.expander("Show gain decomposition table"):
        st.dataframe(gain_df, use_container_width=True, hide_index=True)

st.markdown("### Matched uncertainty / significance")
if stats_df.empty:
    st.caption("34B_matched_statistics.csv 未进入 cache。")
else:
    display_cols = [
        c for c in [
            "comparison", "metric", "mean_effect", "median_effect",
            "pair_bootstrap_ci_low", "pair_bootstrap_ci_high",
            "dyadic_bootstrap_ci_low", "dyadic_bootstrap_ci_high",
            "p_value", "permutation_p", "n_pairs",
        ] if c in stats_df.columns
    ]
    st.dataframe(stats_df[display_cols] if display_cols else stats_df, use_container_width=True, hide_index=True)

with st.expander("Pair-level audit data"):
    if pair_df.empty:
        st.caption("34B_pair_metrics.csv 未进入 cache。")
    else:
        model_options = pair_df["model"].dropna().astype(str).unique().tolist() if "model" in pair_df.columns else []
        if model_options:
            chosen = st.multiselect("Models", model_options, default=model_options[:3])
            view = pair_df[pair_df["model"].astype(str).isin(chosen)] if chosen else pair_df
        else:
            view = pair_df
        st.dataframe(view.head(2000), use_container_width=True, hide_index=True)

st.caption("Interpretation: graph-structured residual capacity and exact topology are reported separately; this page does not treat cross-sectional donor pairs as observed longitudinal cell trajectories.")
