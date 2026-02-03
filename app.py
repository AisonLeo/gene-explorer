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
    return sorted([lib["libraryName"] for lib in data["statistics"]])

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
# ⭐ 多 Library 選擇
# =====================
selected_libraries = st.multiselect(
    "選擇分析庫（可多選）",
    library_list,
    default=["KEGG_2021_Human"]
)

st.markdown("💡 多選方式：點選下拉選單中的項目，列表中會累加，點叉號可取消")

# =====================
# ⭐ 建立 Enrichr-KG URL
# =====================
def build_enrichr_kg_url(genes, description, libraries):

    gene_text = "\n".join(genes)

    lib_json = [{"name": lib, "limit": 5} for lib in libraries]

    q_json = {
        "gene_list": gene_text,
        "description": description,
        "libraries": lib_json,
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

    # 前50筆基因
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

    elif len(selected_libraries) == 0:
        st.warning("請至少選一個 library")

    else:
        kg_url = build_enrichr_kg_url(
            genes,
            gene,   # Description 使用者輸入的 gene symbol
            selected_libraries
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

















