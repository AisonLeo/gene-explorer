import streamlit as st
import pandas as pd
import json
import requests
import urllib.parse
from io import BytesIO
from pathlib import Path

# =====================
# Streamlit 設定
# =====================
st.set_page_config(
    page_title="Gene Explorer - Enrichr-KG",
    layout="wide"
)

# =====================
# 資料路徑 (請確保檔案路徑正確)
# =====================
DATA_PATH = Path("data/578T_Tax660_vs_578T_Parental.xlsx")

# =====================
# 讀取基因資料
# =====================
@st.cache_data
def load_data():
    try:
        df = pd.read_excel(DATA_PATH)
        return df[["Symbol", "log2FoldChange", "padj"]].dropna()
    except Exception as e:
        st.error(f"讀取檔案失敗: {e}")
        return pd.DataFrame(columns=["Symbol", "log2FoldChange", "padj"])

df = load_data()

# =====================
# 取得全部 Enrichr Library
# =====================
@st.cache_data
def load_enrichr_libraries():
    try:
        url = "https://maayanlab.cloud/Enrichr/datasetStatistics"
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        return sorted([lib["libraryName"] for lib in data["statistics"]])
    except:
        return ["KEGG_2021_Human", "GO_Biological_Process_2021", "WikiPathways_2019_Human"]

library_list = load_enrichr_libraries()

# =====================
# 標題
# =====================
st.title("🧬 log2FoldChange Gene Explorer")

# =====================
# Gene 查詢 (會作為 Enrichr 的 Description)
# =====================
st.sidebar.header("查詢設定")
gene_description = st.sidebar.text_input("請輸入 Gene Symbol (將作為分析描述)", placeholder="例如: TP53")

if gene_description:
    if gene_description.upper() in df["Symbol"].str.upper().values:
        gene_fc = df.loc[df["Symbol"].str.upper() == gene_description.upper(), "log2FoldChange"].values[0]
        st.sidebar.success(f"找到 {gene_description}: FC = {gene_fc:.3f}")
    else:
        st.sidebar.warning("此 Symbol 不在原始清單中，但仍可用作描述")

# =====================
# 篩選條件
# =====================
st.subheader("1. 基因篩選條件")
col1, col2, col3 = st.columns(3)

with col1:
    fc_threshold = st.slider(
        "log2FoldChange 閾值",
        float(df["log2FoldChange"].min()) if not df.empty else -5.0,
        float(df["log2FoldChange"].max()) if not df.empty else 5.0,
        1.0, 0.1
    )

with col2:
    direction = st.radio("調控方向", ["Up-regulated", "Down-regulated"])

with col3:
    use_padj = st.checkbox("只顯示 padj < 0.05", True)

# 執行篩選
if direction == "Up-regulated":
    result = df[df["log2FoldChange"] >= fc_threshold]
else:
    result = df[df["log2FoldChange"] <= -fc_threshold]

if use_padj:
    result = result[result["padj"] < 0.05]

st.write(f"📊 符合條件的基因數量：**{len(result)}**")
st.dataframe(result, use_container_width=True, height=300)

# =====================
# 下載 Excel
# =====================
@st.cache_data
def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

if not result.empty:
    excel_data = convert_df_to_excel(result)
    st.download_button(
        "📥 下載篩選後基因清單",
        excel_data,
        file_name="filtered_genes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.divider()

# =====================
# 多 Library 選擇與 Enrichr-KG
# =====================
st.subheader("2. Enrichr-KG 知識圖譜分析")

selected_libraries = st.multiselect(
    "選擇分析資料庫 (建議選 1-3 個)",
    library_list,
    default=["KEGG_2021_Human"]
)

# 前 50 基因預覽
genes_preview = (
    result["Symbol"]
    .dropna()
    .astype(str)
    .str.strip()
    .str.upper()
    .unique()
)[:50]

if len(genes_preview) > 0:
    with st.expander("查看即將送出的前 50 筆基因清單"):
        st.text("\n".join(genes_preview))

    if st.button("🚀 一鍵打開 Enrichr-KG (自動填入基因與描述)"):
        if not selected_libraries:
            st.warning("請至少選擇一個資料庫")
        else:
            # 1. 準備 POST 到 Enrichr API
            # 使用 (None, value) 格式確保 multipart/form-data 正確
            description_text = gene_description if gene_description else "Streamlit_Analysis"
            
            payload = {
                "list": (None, "\n".join(genes_preview)),
                "description": (None, description_text)
            }

            try:
                with st.spinner("正在與 Enrichr 伺服器通訊..."):
                    r = requests.post("https://maayanlab.cloud/Enrichr/addList", files=payload, timeout=10)
                    r.raise_for_status()
                    uid = r.json().get("userListId")

                if uid:
                    # 2. 構建 Enrichr-KG 的 JSON 參數
                    # search: True 會讓系統自動執行分析並將基因填入左側
                    q_json = {
                        "userListId": str(uid),
                        "libraries": [{"name": lib, "limit": 10} for lib in selected_libraries],
                        "term_limit": 10,
                        "min_lib": 1,
                        "gene_degree": 3,
                        "search": True
                    }

                    # URL 編碼
                    encoded_q = urllib.parse.quote(json.dumps(q_json))
                    kg_url = f"https://maayanlab.cloud/enrichr-kg?q={encoded_q}"

                    # 3. 顯示成功訊息與連結
                    st.success(f"✅ 已成功上傳！描述為: **{description_text}**")
                    st.markdown(
                        f"""
                        <div style="background-color:#e1f5fe; padding:20px; border-radius:10px; border: 1px solid #01579b; text-align:center;">
                            <a href="{kg_url}" target="_blank" style="text-decoration:none; font-size:20px; font-weight:bold; color:#01579b;">
                                🔗 點此進入 Enrichr-KG 查看結果
                            </a>
                            <p style="color:#555; margin-top:10px;">點擊連結後，基因會自動顯示在左側 Input 框中</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                else:
                    st.error("未能取得 userListId，請重試。")
            except Exception as e:
                st.error(f"API 連線失敗: {e}")
else:
    st.info("目前的篩選條件下沒有基因可供分析。")

# =====================
# KMplot 連結
# =====================
st.divider()
st.subheader("3. 外部工具連結")
st.markdown(
    """
    [👉 進入 KMplot (Breast Cancer Prognosis)](https://kmplot.com/analysis/index.php?p=service&cancer=breast)  
    *提示：可複製上方基因清單至 KMplot 進行生存分析。*
    """
)

































