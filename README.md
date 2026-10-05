# Microglia Transition Explorer

第一阶段科研型 Web MVP，用于把现有 SEA-AD / DAG-Agent / CausFlow 结果做成交互式页面。

## 当前可用页面

- Overview
- Microglia Atlas
- Mechanistic DAG Explorer

另外三页已经搭好框架：

- State Transport
- Virtual Intervention
- External Evidence

当 STEP34/35 输出存在时，`build_web_data.py` 会自动尝试转换部分结果。

## 1. 放置目录

建议解压到：

```text
D:\PycharmProjects\DAG-Agent\webapp
```

最终应为：

```text
DAG-Agent/
└── webapp/
    ├── app.py
    ├── pages/
    ├── core/
    ├── scripts/
    └── data_cache/
```

## 2. 安装

```powershell
conda activate causflow
pip install -r D:\PycharmProjects\DAG-Agent\webapp\requirements.txt
```

## 3. 构建缓存

```powershell
D:\anaconda3\envs\causflow\python.exe D:\PycharmProjects\DAG-Agent\webapp\scripts\build_web_data.py
```

默认自动寻找：

- `Glial_transition\data\outputs\SEAAD_Microglia_State.h5ad`
- `data\SEAAD\processed\nmf\NMF_K12_W.npy`
- STEP33 DAG-v1 / DAG-v2 / evidence tables
- STEP34B pair metrics
- STEP35A specificity summary（存在时）
- STEP32B-D specificity tables（存在时）

不会修改原始科研文件。

## 4. 启动

```powershell
cd D:\PycharmProjects\DAG-Agent\webapp
streamlit run app.py
```

打开：

```text
http://localhost:8501
```

## 设计原则

- 网页优先读取 Parquet/CSV cache，而不是每次加载 20+ 万细胞 h5ad。
- 第一版不实时调用 GPU。
- DAG-v2 只读取 frozen STEP33 输出，不在网页内重新选边。
- “trajectory” 表述应理解为 pathology-associated model-implied state path，而非纵向细胞追踪。

## Final DAG-v2 web-data workflow

The Streamlit app never trains CFM or runs large SEA-AD analyses online. Build the web cache locally from the completed scientific outputs:

```powershell
cd D:\PycharmProjects\DAG-Agent
python webapp\scripts\build_web_data.py
python webapp\scripts\verify_web_cache.py
cd webapp
streamlit run app.py
```

Final page sources:

- Mechanistic DAG: STEP33 frozen DAG-v2 primary/core + DAG-v1 audit
- State Transport: STEP34B
- Virtual Intervention: STEP35A v2
- External Evidence: STEP32A-D + STEP35B

The generated web-ready files live under `webapp/data_cache/` and should be committed to the web repository when deploying on Streamlit Community Cloud. Do not commit the large source h5ad or model checkpoints to the web repository.
