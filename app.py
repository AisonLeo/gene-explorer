from pathlib import Path
import streamlit as st
import pandas as pd
import json
import urllib.parse

# =====================
# Streamlit 設定
# =====================
st.set_page_config(page_title="Gene Explorer - Enrichr-KG", layout="wide")

# =====================
# 讀取資料
# =====================
DATA_PATH = Path("data/578T_Tax660_vs_578T_Parental.xlsx")
@st.cache_data
def load_data():
    df = pd.read_excel(DATA_PATH)
    return df[["Symbol", "log2FoldChange", "padj"]].dropna()

df = load_data()

# =====================
# 使用者輸入
# =====================
st.title("log2FoldChange Gene Explorer")

gene_input = st.text_input("請輸入 Gene Symbol（作為 Description）")

fc_threshold = st.slider(
    "log2FoldChange 閾值",
    float(df["log2FoldChange"].min()),
    float(df["log2FoldChange"].max()),
    1.0,
    0.1
)

use_padj = st.checkbox("只顯示 padj < 0.05", True)

direction = st.radio("調控方向", ["Up-regulated", "Down-regulated"])

# =====================
# 篩選基因
# =====================
if direction == "Up-regulated":
    result = df[df["log2FoldChange"] >= fc_threshold]
else:
    result = df[df["log2FoldChange"] <= -fc_threshold]

if use_padj:
    result = result[result["padj"] < 0.05]

st.write(f"符合條件的 gene 數量：{len(result)}")
st.dataframe(result, use_container_width=True)

# 前50基因
genes_preview = result["Symbol"].dropna().astype(str).str.strip().str.upper().unique()[:50]
if len(genes_preview) > 0:
    st.subheader("前50基因預覽")
    st.text_area("Gene List Preview", "\n".join(genes_preview), height=200)

# =====================
# Library 多選
# =====================
library_list = [
    "KEGG_2021_Human",
    "GO_Biological_Process_2021",
    "GO_Molecular_Function_2021",
    "GO_Cellular_Component_2021",
    "Reactome_2022"
]

selected_libraries = st.multiselect("選擇分析庫（可多選）", library_list, default=["KEGG_2021_Human"])

# =====================
# 生成一鍵打開 HTML
# =====================
if st.button("🚀 一鍵打開 Enrichr-KG"):

    if len(genes_preview) == 0:
        st.warning("篩選後沒有基因")
        st.stop()

    if len(selected_libraries) == 0:
        st.warning("請至少選一個 library")
        st.stop()

    # 準備基因 & description
    genes_js = json.dumps(list(genes_preview))
    description_js = json.dumps(gene_input)
    libraries_js = json.dumps(selected_libraries)

    # 產生一個 HTML 按鈕，點擊後 JS 將自動填入 KG
    html_code = f"""
    <button onclick="
        const geneBox = document.querySelector('#geneListInput');
        const descBox = document.querySelector('#descriptionInput');
        if (geneBox) geneBox.value = {genes_js}.join('\\n');
        if (descBox) descBox.value = {description_js};
        alert('前50基因與 description 已填好，請點 Analyze 開始分析!');
    ">點此打開 Enrichr-KG 並自動填資料</button>
    <script>
        // 自動跳轉到 Enrichr-KG 網頁
        window.open('https://maayanlab.cloud/enrichr-kg', '_blank');
    </script>
    """

    st.components.v1.html(html_code, height=100)








# =====================
# KMplot 連結
# =====================
st.divider()

st.markdown(
    "[👉 點此進入 KMplot（Breast Cancer prognosis）]"
    "(https://kmplot.com/analysis/index.php?p=service&cancer=breast)"

)
























