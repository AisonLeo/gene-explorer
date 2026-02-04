from io import BytesIO
from pathlib import Path
import streamlit as st
import pandas as pd
import json
import requests
import urllib.parse

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
# 取得全部 Enrichr Library
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
gene = st.text_input("請輸入 Gene Symbol")

if gene:
    if gene in df["Symbol"].values:
        gene_fc = df.loc[df["Symbol"] == gene, "log2FoldChange"].values[0]
        st.success(f"{gene} 的 log2FoldChange = {gene_fc:.3f}")
    else:
        st.error("找不到此 Gene")
        # 這裡不 stop，讓使用者仍可使用此名稱作為 Description
        # st.stop() 

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
# 多 Library 選擇
# =====================
selected_libraries = st.multiselect(
    "選擇分析庫（可多選）",
    library_list,
    default=["KEGG_2021_Human"]
)
st.markdown("💡 多選方式：點選下拉選單中的項目，列表中會累加，點叉號可取消")

# =====================
# 前50基因預覽
# =====================
genes_preview = (
    result["Symbol"]
    .dropna()
    .astype(str)
    .str.strip()
    .str.upper()
    .unique()
)[:50]

if len(genes_preview) > 0:
    st.subheader("前50筆基因預覽（送到 Enrichr-KG）")
    st.text_area("Gene List Preview", "\n".join(genes_preview), height=200)

# =====================
# 一鍵打開 Enrichr-KG（自動填 description）
# =====================
if st.button("🚀 一鍵匯入 Enrichr-KG"):

    if len(genes_preview) == 0:
        st.warning("篩選後沒有基因")
        st.stop()

    if len(selected_libraries) == 0:
        st.warning("請至少選一個 library")
        st.stop()

    # 使用者輸入的 gene 作為 description
    description_text = gene if gene else "Streamlit_Analysis"

    # ---------------------
    # 1️⃣ POST gene list 到 Enrichr
    # ---------------------
    payload = {
        "list": (None, "\n".join(genes_preview)),
        "description": (None, description_text)
    }

    try:
        r = requests.post(
            "https://maayanlab.cloud/Enrichr/addList",
            files=payload,
            timeout=10
        )
        r.raise_for_status()
        uid = r.json().get("userListId")
        if not uid:
            st.error("Enrichr-KG 回傳沒有 userListId，無法生成 URL")
            st.stop()
    except Exception as e:
        st.error(f"傳送 Enrichr-KG 發生錯誤：{e}")
        st.stop()

    # ---------------------
    # 2️⃣ 生成 Enrichr-KG q= JSON URL（整合 Description）
    # ---------------------
    libraries_json = [{"name": lib, "limit": 10} for lib in selected_libraries]
    q_json = {
        "userListId": str(uid),
        "description": description_text, # 核心修正：將描述放入 JSON
        "libraries": libraries_json,
        "term_limit": 10,
        "min_lib": 1,
        "gene_degree": 3,
        "search": True
    }

    # URL 編碼處理
    encoded_q = urllib.parse.quote(json.dumps(q_json))
    encoded_desc = urllib.parse.quote(description_text)
    
    # 最終組合 URL (雙重確保填入)
    kg_url = f"https://maayanlab.cloud/enrichr-kg?q={encoded_q}&description={encoded_desc}"

    # ---------------------
    # 3️⃣ 顯示連結
    # ---------------------
    st.markdown(
        f'<div style="margin: 20px 0;"><a href="{kg_url}" target="_blank" style="padding: 10px 20px; background-color: #ff4b4b; color: white; border-radius: 5px; text-decoration: none; font-weight: bold;">🔗 點此打開 Enrichr-KG</a></div>',
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



