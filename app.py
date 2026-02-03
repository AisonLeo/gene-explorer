from pathlib import Path
from io import BytesIO
import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.common.by import By

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
# 一鍵打開 Enrichr-KG
# =====================
if st.button("🚀 一鍵打開 Enrichr-KG"):

    if len(genes_preview) == 0:
        st.warning("篩選後沒有基因")
        st.stop()

    if len(selected_libraries) == 0:
        st.warning("請至少選一個 library")
        st.stop()

    st.info("正在打開瀏覽器，請稍候...")

    # =====================
    # Selenium 打開瀏覽器
    # =====================
    driver = webdriver.Chrome()  # 若需指定路徑：webdriver.Chrome(executable_path="path/to/chromedriver")
    driver.get("https://maayanlab.cloud/enrichr-kg")
    time.sleep(3)  # 等待前端載入

    # 填左側基因框
    try:
        gene_box = driver.find_element(By.CSS_SELECTOR, "textarea#geneListInput")
        gene_box.clear()
        gene_box.send_keys("\n".join(genes_preview))
    except:
        st.error("無法找到左側基因框，請確認 Enrichr-KG 前端未改版")

    # 填 description
    try:
        desc_box = driver.find_element(By.CSS_SELECTOR, "input#descriptionInput")
        desc_box.clear()
        desc_box.send_keys(gene_input)
    except:
        st.error("無法找到 description 輸入框，請確認 Enrichr-KG 前端未改版")

    # 選 library
    for lib in selected_libraries:
        lib = lib.strip()
        try:
            checkbox = driver.find_element(By.XPATH, f"//label[contains(text(), '{lib}')]//input[@type='checkbox']")
            if not checkbox.is_selected():
                checkbox.click()
        except:
            st.warning(f"找不到 library: {lib}")

    st.success("瀏覽器已打開，左側基因與 description 已填好，請點 Analyze 開始分析！")









# =====================
# KMplot 連結
# =====================
st.divider()

st.markdown(
    "[👉 點此進入 KMplot（Breast Cancer prognosis）]"
    "(https://kmplot.com/analysis/index.php?p=service&cancer=breast)"

)






















