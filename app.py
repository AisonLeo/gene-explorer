from io import BytesIO
from pathlib import Path
import streamlit as st
import pandas as pd
import requests

# =====================
# Streamlit 頁面設定
# =====================
st.set_page_config(
    page_title="Gene Explorer",
    layout="wide"
)

# =====================
# 資料路徑設定（部署關鍵）
# =====================
DATA_PATH = Path("data/578T_Tax660_vs_578T_Parental.xlsx")

# =====================
# 讀取資料
# =====================
@st.cache_data
def load_data():
    if not DATA_PATH.exists():
        st.error(f"找不到資料檔案：{DATA_PATH}")
        st.stop()

    df = pd.read_excel(DATA_PATH)
    return df[["Symbol", "log2FoldChange", "padj"]].dropna()

df = load_data()

# =====================
# 標題
# =====================
st.title("log2FoldChange Gene Explorer")

# =====================
# 第一階段：Gene 查詢
# =====================
gene = st.text_input("請輸入 Gene Symbol（例如 ESR1）")

if gene:
    if gene in df["Symbol"].values:
        gene_fc = df.loc[df["Symbol"] == gene, "log2FoldChange"].values[0]
        st.success(f"{gene} 的 log2FoldChange = {gene_fc:.3f}")
    else:
        st.error("找不到此 Gene")
        st.stop()

# =====================
# 第二階段：篩選條件
# =====================
st.subheader("基因篩選條件")

fc_threshold = st.slider(
    "log2FoldChange 閾值",
    min_value=float(df["log2FoldChange"].min()),
    max_value=float(df["log2FoldChange"].max()),
    value=1.0,
    step=0.1
)

use_padj = st.checkbox("只顯示 padj < 0.05", value=True)

direction = st.radio(
    "調控方向",
    ["Up-regulated", "Down-regulated"]
)

# =====================
# 篩選邏輯
# =====================
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
    file_name="filtered_genes.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# =====================
# Enrichr 分析
# =====================
if st.button("送到 Enrichr（GO / Pathway）"):

    genes = (
        result["Symbol"]
        .astype(str)
        .str.strip()
        .unique()
    )[:50]

    if len(genes) == 0:
        st.warning("篩選後沒有基因")
    else:
        payload = {
            "list": "\n".join(genes),
            "description": "Streamlit gene list"
        }

        r = requests.post(
            "https://maayanlab.cloud/Enrichr/addList",
            files=payload
        )

        if r.status_code == 200:
            uid = r.json()["userListId"]
            url = f"https://maayanlab.cloud/Enrichr/enrich?userListId={uid}"
            st.success("已送出到 Enrichr")
            st.markdown(f"[👉 點此查看 Enrichr 結果]({url})")
        else:
            st.error("Enrichr 傳送失敗")

# =====================
# KMplot 連結
# =====================
st.divider()

st.markdown(
    "[👉 點此進入 KMplot（Breast Cancer prognosis）]"
    "(https://kmplot.com/analysis/index.php?p=service&cancer=breast)"

)
