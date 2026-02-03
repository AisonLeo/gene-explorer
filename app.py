from io import BytesIO
from pathlib import Path
import streamlit as st
import pandas as pd
import json
import urllib.parse
import requests

# =====================
# Streamlit 設定
# =====================
st.set_page_config(
    page_title="Gene Explorer - Enrichr-KG",
    layout="wide"
)

# =====================
# 資料路徑
# =====================
DATA_PATH = Path("data/578T_Tax660_vs_578T_Parental.xlsx")

# =====================
# 讀取基因資料
# =====================
@st.cache_data
def load_data():
    df = pd.read_excel(DATA_PATH)
    return df[["Symbol", "log2FoldChange", "padj"]].dropna()

df = load_data()

# =====================
# ⭐ 取得全部 Enrichr Library
# =====================
@st.cache_data
def load_enrichr_libraries():

    url = "https://maayanlab.cloud/Enrichr/datasetStatistics"
    r = requests.get(url)
    r.raise_for_status()

    data = r.json()
    libraries = sorted([lib["libraryName"] for lib in data["statistics"]])

    return libraries

library_list = load_enrichr_libraries()

# =====================
# 標題
# =====================
st.title("log2FoldChange Gene Explorer")

# =====================
# Gene 查詢
# =====================
gene = st.text_input("請輸入 Gene Symbol（會當作 Description）")

if gene:
    if gene in df["Symbol"].values:
        gene_fc = df.loc[df["Symbol"] == gene, "log2FoldChange"].values[0]
        st.success(f"{gene} 的 log2FoldChange = {gene_fc:.3f}")
    else:
        st.error("找不到此 Gene")
        st.stop()

# =====================
# 篩選條件
# =====================
st.subheader("基因篩選條件")

fc_threshold = st.slider(
    "log2FoldChange 閾值",
    float(df["log2FoldChange"].min()),
    float(df["log2FoldChange"].max()),
    1.0,
    0.1
)

use_padj = st.checkbox("只顯示 padj < 0.05", True)

direction = st.radio(
    "調控方向",
    ["Up-regulated", "Down-regulated"]
)

# 篩選
if direction == "Up-regulated":
    result = df[df["log2FoldChange"] >= fc_threshold]
else:
    result = df[df["log2FoldChange"] <= -fc_threshold]

if use_padj:
    result = result[result["padj"] < 0.05]

st.write(f"符合條件的 gene 數量：{len(result)}")
st.dataframe(result, use_container_width=True)

# =====================
# 下載 Excel
# =====================
buffer = BytesIO()
result.to_excel(buffer, index=False, engine="openpyxl")
buffer.seek(0)

st.download_button(
    "下載篩選後基因清單",
    buffer,
    file_name="filtered_genes.xlsx"
)

# =====================
# Library 選單（全部）
# =====================
selected_library = st.selectbox(
    "選擇分析庫",
    library_list
)

# =====================
# ⭐ 建立 Enrichr-KG URL
# =====================
def build_enrichr_kg_url(genes, description, library):

    gene_text = "\n".join(genes)

    q_json = {
        "gene_list": gene_text,
        "description": description,
        "libraries": [{"name": library, "limit": 5}],
        "term_limit": 5,
        "min_lib": 1,
        "gene_degree": 3,
        "search": True
    }

    encoded = urllib.parse.quote(json.dumps(q_json))

    return f"https://maayanlab.cloud/enrichr-kg?q={encoded}"

# =====================
# ⭐ 一鍵打開 Enrichr-KG
# =====================
if st.button("👉 一鍵打開 Enrichr-KG"):

    genes = (
        result["Symbol"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .unique()
    )[:50]

    if len(genes) == 0:
        st.warning("篩選後沒有基因")
    else:

        kg_url = build_enrichr_kg_url(
            genes,
            gene,   # Description = 使用者輸入
            selected_library
        )

        st.markdown(
            f'<a href="{kg_url}" target="_blank">🚀 點此打開 Enrichr-KG</a>',
            unsafe_allow_html=True
        )




# =====================
# KMplot 連結
# =====================
st.divider()

st.markdown(
    "[👉 點此進入 KMplot（Breast Cancer prognosis）]"
    "(https://kmplot.com/analysis/index.php?p=service&cancer=breast)"

)















