from __future__ import annotations

import math
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


PROGRAMS = ["P1", "P4", "P6", "P7", "P10"]


def umap_figure(df: pd.DataFrame, color_col: str):
    hover = [
        c
        for c in [
            "donor",
            "disease_stage",
            "brain_region",
            "continuous_state",
            "P1",
            "P4",
            "P6",
            "P7",
            "P10",
        ]
        if c in df.columns
    ]

    numeric = color_col in df.columns and pd.api.types.is_numeric_dtype(df[color_col])

    kwargs = {}
    if numeric:
        kwargs["color_continuous_scale"] = "Viridis"

    fig = px.scatter(
        df,
        x="umap1",
        y="umap2",
        color=color_col if color_col in df.columns else None,
        hover_data=hover,
        opacity=0.72,
        render_mode="webgl",
        **kwargs,
    )
    fig.update_traces(marker={"size": 4})
    fig.update_layout(
        height=630,
        margin=dict(l=10, r=10, t=20, b=10),
        legend_title_text=color_col,
    )
    fig.update_xaxes(title="UMAP 1", showgrid=False, zeroline=False)
    fig.update_yaxes(title="UMAP 2", showgrid=False, zeroline=False)
    return fig


def program_bar(values: Dict[str, float], title="Program profile"):
    data = pd.DataFrame(
        {
            "Program": PROGRAMS,
            "Activity": [float(values.get(p, np.nan)) for p in PROGRAMS],
        }
    )
    fig = px.bar(data, x="Program", y="Activity", title=title)
    fig.update_layout(height=330, margin=dict(l=10, r=10, t=48, b=10))
    return fig


def stage_state_box(df: pd.DataFrame):
    if "continuous_state" not in df.columns or "disease_stage" not in df.columns:
        return go.Figure()

    preferred = ["Not AD", "not_ad", "Low", "low", "Intermediate", "intermediate", "High", "high"]
    existing = list(dict.fromkeys(df["disease_stage"].dropna().astype(str).tolist()))
    order = [x for x in preferred if x in existing] + [x for x in existing if x not in preferred]

    fig = px.box(
        df,
        x="disease_stage",
        y="continuous_state",
        points="outliers",
        category_orders={"disease_stage": order},
    )
    fig.update_layout(
        height=380,
        xaxis_title="Pathology-associated disease stage",
        yaxis_title="Continuous molecular state",
        margin=dict(l=10, r=10, t=20, b=10),
    )
    return fig


def _node_layers(edges: pd.DataFrame):
    nodes = sorted(set(edges["source"].astype(str)) | set(edges["target"].astype(str)))

    genes = {"INPP5D", "MS4A6A", "RABEP1"}
    programs = {x for x in nodes if x.startswith("P") and x[1:].isdigit()}

    mechanisms = [x for x in nodes if x not in genes and x not in programs]
    gene_nodes = [x for x in nodes if x in genes]
    program_nodes = [x for x in nodes if x in programs]

    return gene_nodes, mechanisms, program_nodes


def dag_figure(edges: pd.DataFrame, selected_edge: Tuple[str, str] | None = None):
    if edges.empty:
        return go.Figure()

    gene_nodes, mechanism_nodes, program_nodes = _node_layers(edges)

    pos = {}

    def spread(nodes, x):
        if not nodes:
            return
        ys = np.linspace(1, -1, len(nodes)) if len(nodes) > 1 else np.array([0.0])
        for n, y in zip(sorted(nodes), ys):
            pos[n] = (x, float(y))

    spread(gene_nodes, 0.0)
    spread(mechanism_nodes, 1.0)
    spread(program_nodes, 2.0)

    edge_x, edge_y = [], []
    selected_x, selected_y = [], []

    for _, row in edges.iterrows():
        s, t = str(row["source"]), str(row["target"])
        if s not in pos or t not in pos:
            continue

        target_arrays = (selected_x, selected_y) if selected_edge == (s, t) else (edge_x, edge_y)
        xs, ys = target_arrays

        x0, y0 = pos[s]
        x1, y1 = pos[t]

        xs.extend([x0, x1, None])
        ys.extend([y0, y1, None])

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=1.7, color="rgba(130,130,130,.65)"),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    if selected_x:
        fig.add_trace(
            go.Scatter(
                x=selected_x,
                y=selected_y,
                mode="lines",
                line=dict(width=4),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    node_order = gene_nodes + mechanism_nodes + program_nodes
    fig.add_trace(
        go.Scatter(
            x=[pos[n][0] for n in node_order],
            y=[pos[n][1] for n in node_order],
            text=node_order,
            customdata=node_order,
            mode="markers+text",
            textposition="middle right",
            marker=dict(size=22),
            hovertemplate="%{text}<extra></extra>",
            showlegend=False,
        )
    )

    fig.update_layout(
        height=600,
        margin=dict(l=10, r=40, t=10, b=10),
        xaxis=dict(visible=False, range=[-0.2, 2.45]),
        yaxis=dict(visible=False, range=[-1.25, 1.25]),
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
