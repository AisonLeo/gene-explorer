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
# Enrichr 分析（漂亮輸出版 + 按鈕）
# =====================
if st.button("送到 Enrichr（GO / Pathway）"):

    # 取 gene list，清理格式
    genes = (
        result["Symbol"]
        .dropna()
        .astype(str)
        .str.strip()        # 去掉空白
        .str.upper()        # 轉大寫
        .unique()
    )

    # 過濾非字母數字（避免奇怪符號）
    genes = [g for g in genes if g.isalnum()]

    # 只取前 50 個基因
    genes = genes[:50]

    # 檢查是否有 gene
    if len(genes) == 0:
        st.warning("篩選後沒有基因可送出")
    else:
        # =====================
        # 乾淨顯示送出的 genes
        # =====================
        st.subheader("送出的 Gene List（前 50 個）")
        st.markdown("```\n" + "\n".join(genes) + "\n```")

        genes_str = "\n".join(genes)

        # 使用官方建議的 files 格式
        payload = {
            "list": (None, genes_str),
            "description": (None, "Streamlit gene list")
        }

        try:
            r = requests.post(
                "https://maayanlab.cloud/Enrichr/addList",
                files=payload,
                timeout=10  # 避免 Cloud 過久無回應
            )

            # 顯示 HTTP status
            st.write("HTTP status:", r.status_code)

            if not r.ok:
                st.error(f"Enrichr 傳送失敗：HTTP {r.status_code}")
            else:
                uid = r.json().get("userListId")
                if uid:
                    enrichr_url = f"https://maayanlab.cloud/Enrichr/enrich?userListId={uid}"
                    st.success("已送出到 Enrichr")
                    # =====================
                    # 使用按鈕直接打開
                    # =====================
                    if st.button("👉 打開 Enrichr 網頁"):
                        st.experimental_set_query_params()  # 清除 Streamlit URL 錯誤提示
                        st.write(f"[點此查看 Enrichr 結果]({enrichr_url})")
                else:
                    st.error("Enrichr 回傳沒有 userListId，無法產生連結")

        except Exception as e:
            st.error(f"傳送 Enrichr 發生錯誤：{e}")


# =====================
# KMplot 連結
# =====================
st.divider()

st.markdown(
    "[👉 點此進入 KMplot（Breast Cancer prognosis）]"
    "(https://kmplot.com/analysis/index.php?p=service&cancer=breast)"

)


