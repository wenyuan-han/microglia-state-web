"""User-uploaded h5ad preview and bounded exploratory simulations."""
from pathlib import Path
import shutil
import tempfile

import pandas as pd
import plotly.express as px
import streamlit as st

from core.ui import page_header
from core.user_simulator import inspect_h5ad, lookup_gene, run_simulation


MAX_UPLOAD_MB = 150
KEY_DATA = "upload_sim_input"
KEY_RESULT = "upload_sim_result"


def clear_loaded():
    info = st.session_state.pop(KEY_DATA, None)
    st.session_state.pop(KEY_RESULT, None)
    if info and info.get("tempdir"):
        shutil.rmtree(info["tempdir"], ignore_errors=True)


page_header(
    "Interactive research workspace",
    "Data & Simulation",
    "上传自己的 .h5ad，浏览元数据、执行小样本探索性模拟并导出新的 AnnData。原始文件不会被修改。",
)
st.warning(
    "当前运行的是模型无关的探索性模拟，不是 CausFlow、DAG-Agent 的训练权重推理，"
    "也不能据此认定基因扰动具有真实生物学效应。"
)

st.markdown("### 1. 上传与检查数据")
uploaded = st.file_uploader("选择 AnnData 文件", type=["h5ad"], key="upload_sim_file")
if uploaded is not None:
    size_mb = uploaded.size / (1024 * 1024)
    st.caption(f"文件：{uploaded.name} · {size_mb:.1f} MB · 上传后仅供当前会话使用")
    if size_mb > MAX_UPLOAD_MB:
        st.error(
            f"此在线版为保护 Streamlit Cloud 内存，限制文件不超过 {MAX_UPLOAD_MB} MB。"
            "对于大型 SEA-AD 数据，请在本地运行，或先导出细胞/HVG 子集。"
        )
    if st.button("读取文件并检查结构", type="primary", disabled=size_mb > MAX_UPLOAD_MB):
        clear_loaded()
        tempdir = tempfile.mkdtemp(prefix="microglia_user_")
        path = Path(tempdir) / "uploaded.h5ad"
        try:
            uploaded.seek(0)
            with path.open("wb") as dest:
                while True:
                    chunk = uploaded.read(1024 * 1024)
                    if not chunk:
                        break
                    dest.write(chunk)
            meta = inspect_h5ad(str(path))
            st.session_state[KEY_DATA] = {
                "path": str(path), "tempdir": tempdir,
                "filename": uploaded.name, "bytes": uploaded.size,
                "meta": meta,
            }
            st.success("文件已读取，下面可以配置模拟。")
        except Exception as exc:
            shutil.rmtree(tempdir, ignore_errors=True)
            st.error(f"无法读取该 h5ad：{exc}")

loaded = st.session_state.get(KEY_DATA)
if not loaded:
    st.info("上传 .h5ad 后点击“读取文件并检查结构”。")
    st.stop()

if uploaded is None or (uploaded.name, uploaded.size) != (loaded["filename"], loaded["bytes"]):
    st.info("当前上传区与上次加载的文件不同。请重新点击“读取文件并检查结构”。")
    st.stop()

meta = loaded["meta"]
a, b, c, d = st.columns(4)
a.metric("Cells", f"{meta['n_obs']:,}")
b.metric("Genes", f"{meta['n_vars']:,}")
c.metric("HVG annotation", "Yes" if meta["has_hvg"] else "No")
d.metric("UMAP annotation", "Yes" if meta["has_umap"] else "No")

with st.expander("查看 obs 列、分组变量和 layers", expanded=False):
    st.write("**obs columns**", meta["obs_columns"])
    st.write("**layers**", meta["layers"] or "无")
    st.write("**可用的离散分组变量**", list(meta["categorical_columns"]))
    st.write("**var_names 示例**", meta.get("var_name_examples", []))
    st.write("**可匹配基因符号 / ID 的 var 列**", meta.get("gene_annotation_columns", []) or "未发现")
    st.write("**adata.raw 可用**", "Yes" if meta.get("has_raw") else "No")
    st.caption("本版仅处理 adata.X，不读取 layers、raw 或 obsm 中的表达矩阵。")

if not meta["unique_genes"]:
    st.error("var_names 存在重复基因名，请在本地先运行 adata.var_names_make_unique() 再上传。")
    st.stop()

st.markdown("### 2. 选择模拟方式")
mode_text = st.radio(
    "模型 / 算法",
    ["疾病阶段均值迁移（探索性）", "单基因表达编辑（数值模拟）"],
    horizontal=True,
)
mode = "stage_mean_shift" if mode_text.startswith("疾病") else "single_gene_edit"
input_kind_text = st.radio(
    "adata.X 的表达格式",
    ["已做 log1p 归一化（非负）", "原始 counts（非负整数）"],
    horizontal=True,
    help="选择 counts 时使用完整基因矩阵计算每个细胞的 library size，做 1e4 CPM-like normalization + log1p。",
)
input_kind = "counts" if input_kind_text.startswith("原始") else "log1p"
st.caption("不支持直接输入 z-score/scale 后的负值矩阵。若原始计数放在 layers['UMIs']，请先在本地生成相应的 X 版本。")

cat_cols = meta["categorical_columns"]
stage_col = None
source_stage = None
target_stage = None
focus_gene = None

if mode == "stage_mean_shift":
    if not cat_cols:
        st.error("未找到 2–25 个类别的 obs 分组列，因此无法构建同文件的 source / target 参考。")
        st.stop()
    common_names = ["disease_stage", "Overall AD neuropathological Change", "AD stage", "stage"]
    preferred = next((x for x in common_names if x in cat_cols), next(iter(cat_cols)))
    stage_col = st.selectbox("Disease stage 所在 obs 列", list(cat_cols), index=list(cat_cols).index(preferred))
    counts = cat_cols[stage_col]
    options = list(counts)
    x, y = st.columns(2)
    with x:
        source_stage = st.selectbox("Source（源细胞状态）", options, format_func=lambda s: f"{s} ({counts[s]:,})")
    with y:
        target_options = [s for s in options if s != source_stage]
        target_stage = st.selectbox("Target（参考目标状态）", target_options,
                                     format_func=lambda s: f"{s} ({counts[s]:,})")
    strength = st.slider("迁移程度 α", min_value=0.0, max_value=1.5, value=1.0, step=0.1)
    st.caption("公式：X_sim = max(0, X_source + α × (mean_target − mean_source))；按基因在 log1p 空间计算。")
else:
    st.info("这里仅编辑一个基因自身的数值，不会推算上下游通路或其他基因的响应。")
    if cat_cols:
        stage_choice = st.selectbox("仅模拟某个细胞群（可选）", ["全体细胞"] + list(cat_cols))
        if stage_choice != "全体细胞":
            stage_col = stage_choice
            counts = cat_cols[stage_col]
            source_stage = st.selectbox("选择细胞群", list(counts),
                                        format_func=lambda s: f"{s} ({counts[s]:,})")
    focus_gene = st.text_input(
        "要编辑的基因符号或 ID（支持 var_names 和 var 注释列）",
        value="TREM2", help="例如 TREM2、APOE 或 ENSG...；编辑前可先点“检查基因”。"
    )
    if st.button("检查基因是否在当前表达矩阵中"):
        try:
            found = lookup_gene(loaded["path"], focus_gene)
            st.success(
                f"找到：{found['gene_query']} → {found['var_name']} "
                f"（通过 {found['matched_column']}，第 {found['var_index'] + 1} 列）"
            )
        except ValueError as exc:
            st.warning(str(exc))
    strength = st.slider("该基因表达乘数", min_value=0.0, max_value=3.0, value=0.5, step=0.1)
    st.caption("0 = 表达置零；1 = 保持原状；2 = 将该基因的线性尺度表达乘以 2，然后重新 log1p。")

filter_cols = [c for c in cat_cols if c != stage_col]
filter_col = st.selectbox("限制一个亚组（如 Brain Region，可选）", ["不限制"] + filter_cols)
filter_value = None
if filter_col == "不限制":
    filter_col = None
else:
    filter_value = st.selectbox("亚组值", list(cat_cols[filter_col]),
                                format_func=lambda s: f"{s} ({cat_cols[filter_col][s]:,})")

with st.expander("计算规模与可重复性", expanded=False):
    max_cells = st.slider("每组最多采样多少细胞", 100, 1200, 800, 100)
    max_genes = st.slider("最多使用多少基因", 100, 2000, 1000, 100)
    seed = st.number_input("Random seed", min_value=0, max_value=999999, value=42, step=1)
    st.caption("优先使用 var.highly_variable；否则从最多 240 个采样细胞中按方差挑选基因。")

if st.button("运行模拟", type="primary"):
    if mode == "single_gene_edit" and not (focus_gene or "").strip():
        st.error("请填写基因名。")
    else:
        try:
            with st.spinner("从 h5ad 分块读取所需细胞并计算模拟结果…"):
                output_path = str(Path(loaded["tempdir"]) / "simulation_result.h5ad")
                result = run_simulation(
                    loaded["path"], output_path,
                    mode=mode, input_kind=input_kind, stage_col=stage_col,
                    source_stage=source_stage, target_stage=target_stage,
                    filter_col=filter_col, filter_value=filter_value,
                    strength=float(strength), focus_gene=(focus_gene or "").strip() or None,
                    max_cells=int(max_cells), max_genes=int(max_genes), seed=int(seed),
                )
            st.session_state[KEY_RESULT] = result
            st.success("模拟完成。可以在下方查看和下载结果。")
        except Exception as exc:
            st.session_state.pop(KEY_RESULT, None)
            st.error(f"模拟失败：{exc}")

result = st.session_state.get(KEY_RESULT)
if result:
    st.markdown("### 3. 模拟结果")
    st.caption(result.description)
    if result.gene_resolution:
        st.info("基因定位：" + result.gene_resolution)
    a, b, c = st.columns(3)
    a.metric("Source cells", f"{result.n_source:,}")
    b.metric("Target reference", f"{result.n_target:,}" if result.n_target else "无")
    c.metric("Genes in output", f"{result.n_genes:,}")

    left, right = st.columns([1.1, 1])
    with left:
        st.markdown("**表达空间 PCA（来源 / 编辑后 / 参考目标）**")
        fig = px.scatter(
            result.embedding, x="PC1", y="PC2", color="Group",
            opacity=0.66, color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig.update_traces(marker={"size": 5})
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=15, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("PCA 仅用于观察本次抽样的几何变化；不使用原始 UMAP 坐标作为预测坐标。")
    with right:
        st.markdown("**变化最大的基因**")
        chart = result.gene_summary.head(15).sort_values("abs_change")
        fig = px.bar(chart, x="simulated_minus_source", y="gene", orientation="h",
                     labels={"simulated_minus_source": "Mean change (log1p)", "gene": "Gene"})
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=15, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(result.gene_summary.head(200), use_container_width=True, hide_index=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "下载模拟结果 .h5ad",
            data=Path(result.output_path).read_bytes(),
            file_name="microglia_simulated.h5ad", mime="application/octet-stream",
        )
    with col_b:
        st.download_button(
            "下载基因变化 CSV",
            data=result.gene_summary.to_csv(index=False).encode("utf-8-sig"),
            file_name="simulation_gene_summary.csv", mime="text/csv",
        )
    st.info(
        "输出文件 X 为模拟后的非负 log1p 表达矩阵，layers['original_log1p'] 保留采样前数据；"
        "obs 保留源细胞标签并附加模拟信息。该文件不可作为真实干预、纵向轨迹或早筛有效性的证据。"
    )

st.divider()
st.markdown("**后续可接入的真正模型推理**：加载冻结的预处理参数、DAG 拓扑、CausFlow 模型权重和推理函数，"
            "再将此页面升级为条件状态生成与机制干预预测；这些模型资源尚未连接。")
if st.button("清空当前上传文件和结果"):
    clear_loaded()
    st.rerun()
