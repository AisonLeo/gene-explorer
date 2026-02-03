from io import BytesIO
from pathlib import Path
import re

import streamlit as st
import pandas as pd
import requests

# =====================
# Streamlit 頁面設定
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
    if gene.upper() in df["Symbol"].str.upper().values:
        gene_fc = df.loc[df["Symbol"].str.upper() == gene.upper(), "log2FoldChange"].values[0]
        st.success(f"{gene.upper()} 的 log2FoldChange = {gene_fc:.3f}")
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

# 篩選邏輯
if direction == "Up-regulated":
    result = df[df["log2FoldChange"] >= fc_threshold]
else:
    result = df[df["log2FoldChange"] <= -fc_threshold]

if use_padj:
    result = result[result["padj"] < 0.05]

# 顯示結果
st.write(f"符合條件的 gene 數量：{len(result)}")
st.dataframe(result, use_container_width=True)

# 下載 Excel
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
# Enrichr-KG 分析
# =====================
st.subheader("送到 Enrichr-KG 分析")

# ---- Enrichr-KG library 選單 ----
library_options = {
    "KEGG": "KEGG_2021_Human",
    "Reactome": "Reactome_2022",
    "WikiPathways": "WikiPathways_2022_Human",
    "GO Biological Process": "GO_Biological_Process_2021",
    "GO Molecular Function": "GO_Molecular_Function_2021",
    "GO Cellular Component": "GO_Cellular_Component_2021",
    "ARCHS4 TFs": "ARCHS4_TFs_Coexp",
    "ChEA3": "ChEA3_2022",
    "TRRUST": "TRRUST_Transcription_Factors_2019",
    "FANTOM6": "FANTOM6_TFs",
    "DisGeNET": "DisGeNET",
    "GWAS Catalog": "GWAS_Catalog_2022",
    "LINCS (Small Molecule)": "LINCS_L1000_Chem_Pert_up",
    "LINCS (CRISPR KO)": "LINCS_L1000_CRISPRKO_gene",
    "Achilles": "Achilles_2021",
    "Proteomics Drug Atlas": "Proteomics_Drug_Atlas",
    "Human Gene Atlas": "Human_Gene_Atlas",
    "CCLE Proteomics": "CCLE_Proteomics",
    "Descartes": "Descartes_Cell_Types",
    "Tabula Muris": "Tabula_Muris",
    "Tabula Sapiens": "Tabula_Sapiens",
    "Pfam": "Pfam_2021"
}

selected_library_name = st.selectbox("選擇分析庫", options=list(library_options.keys()))
selected_library = library_options[selected_library_name]

# =====================
# 送到 Enrichr-KG 按鈕
# =====================
if st.button("送出到 Enrichr-KG"):

    # 篩選前50個基因
    genes = (
        result["Symbol"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .unique()
    )
    genes = [g for g in genes if re.match(r"^[A-Z0-9\-]+$", g)]
    genes = genes[:50]

    if len(genes) == 0:
        st.warning("篩選後沒有基因可送出")
    else:

        st.subheader("送出的 Gene List（前 50 個）")
        st.text_area("Gene List (Preview)", "\n".join(genes), height=200)

        desc = st.text_input("Description（自動填入）", value=gene.upper())

        # 上傳到 Enrichr
        genes_str = "\n".join(genes)
        payload = {
            "list": (None, genes_str),
            "description": (None, desc)
        }

        try:
            r = requests.post(
                "https://maayanlab.cloud/Enrichr/addList",
                files=payload,
                timeout=10
            )
            r.raise_for_status()
            res = r.json()
            uid = res.get("userListId")

            if uid:
                enrichr_url = f"https://maayanlab.cloud/enrichr-kg/enrich?userListId={uid}&backgroundType={selected_library}"
                st.success(f"已準備好 Enrichr-KG ({selected_library_name})")

                # 一鍵打開新分頁
                st.markdown(
                    f'<a href="{enrichr_url}" target="_blank">'
                    f'👉 點此一鍵打開 Enrichr-KG (Gene List 已填)</a>',
                    unsafe_allow_html=True
                )

                st.info(f"Description: {desc} （請在 Enrichr-KG 前端手動填入）")

            else:
                st.error("Enrichr 回傳沒有 userListId，無法產生連結")

        except Exception as e:
            st.error(f"傳送到 Enrichr 發生錯誤：{e}")
            if hasattr(r, "status_code"):
                st.text(f"Status code: {r.status_code}")
            if hasattr(r, "text"):
                st.text(f"Response text: {r.text}")





# =====================
# KMplot 連結
# =====================
st.divider()

st.markdown(
    "[👉 點此進入 KMplot（Breast Cancer prognosis）]"
    "(https://kmplot.com/analysis/index.php?p=service&cancer=breast)"

)













