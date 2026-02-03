import streamlit as st
import pandas as pd
import json
import requests
import urllib.parse
from io import BytesIO
from pathlib import Path

# =====================
# Streamlit 全域設定
# =====================
st.set_page_config(
    page_title="Gene Explorer - Enrichr-KG",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================
# 資料路徑設定
# =====================
# 請確保你的資料夾中有 data/578T_Tax660_vs_578T_Parental.xlsx
DATA_PATH = Path("data/578T_Tax660_vs_578T_Parental.xlsx")

# =====================
# 核心資料讀取
# =====================
@st.cache_data
def load_data():
    try:
        df = pd.read_excel(DATA_PATH)
        # 確保必要的欄位存在並去除空值
        return df[["Symbol", "log2FoldChange", "padj"]].dropna()
    except Exception as e:
        st.error(f"❌ 讀取檔案失敗，請檢查路徑是否正確：{e}")
        return pd.DataFrame(columns=["Symbol", "log2FoldChange", "padj"])

df = load_data()

# =====================
# 取得 Enrichr 所有的分析庫清單
# =====================
@st.cache_data
def load_enrichr_libraries():
    try:
        url = "https://maayanlab.cloud/Enrichr/datasetStatistics"
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        return sorted([lib["libraryName"] for lib in data["statistics"]])
    except:
        # 如果 API 失聯，提供常用的預設清單
        return ["KEGG_2021_Human", "GO_Biological_Process_2021", "WikiPathways_2019_Human", "MSigDB_Hallmark_2020"]

library_list = load_enrichr_libraries()

# =====================
# 介面設計：標題與輸入
# =====================
st.title("🧬 log2FoldChange Gene Explorer")
st.markdown("這是一個整合 **Enrichr-KG** 的自動化分析工具。篩選基因後，可直接生成知識圖譜連結。")

# 側邊欄：使用者輸入與查詢
st.sidebar.header("🔍 描述設定")
gene_description = st.sidebar.text_input(
    "請輸入 Gene Symbol (將作為 Enrichr 的 Description)", 
    placeholder="例如: TP53"
).strip()

if gene_description:
    # 檢查輸入的 Gene 是否在原始列表中
    match = df[df["Symbol"].str.upper() == gene_description.upper()]
    if not match.empty:
        fc_val = match["log2FoldChange"].values[0]
        st.sidebar.success(f"找到 {gene_description}: log2FC = {fc_val:.3f}")
    else:
        st.sidebar.info("💡 該名稱將作為分析任務的描述標題")

# =====================
# 1. 基因篩選區域
# =====================
st.subheader("1. 基因篩選條件")
c1, c2, c3 = st.columns(3)

with c1:
    fc_threshold = st.slider(
        "log2FoldChange 絕對值閾值",
        0.0, 5.0, 1.0, 0.1
    )

with c2:
    direction = st.radio("調控方向", ["Up-regulated", "Down-regulated"])

with c3:
    use_padj = st.checkbox("僅保留顯著基因 (padj < 0.05)", True)

# 執行篩選邏輯
if direction == "Up-regulated":
    result = df[df["log2FoldChange"] >= fc_threshold]
else:
    result = df[df["log2FoldChange"] <= -fc_threshold]

if use_padj:
    result = result[result["padj"] < 0.05]

st.info(f"📋 當前篩選條件下共有 **{len(result)}** 個基因。")
st.dataframe(result, use_container_width=True, height=250)

# Excel 下載功能
@st.cache_data
def convert_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

if not result.empty:
    st.download_button(
        label="📥 下載篩選後的 Excel 檔案",
        data=convert_to_excel(result),
        file_name="filtered_gene_list.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.divider()

# =====================
# 2. Enrichr-KG 整合區域
# =====================
st.subheader("2. 一鍵導出至 Enrichr-KG 知識圖譜")

col_lib, col_preview = st.columns([1, 1])

with col_lib:
    selected_libraries = st.multiselect(
        "選擇要分析的資料庫 (Library)",
        library_list,
        default=["KEGG_2021_Human"]
    )

with col_preview:
    # 僅取前 50 筆避免 API 負載過重或圖譜過於混亂
    genes_to_send = (
        result["Symbol"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .unique()
    )[:50]
    
    with st.expander("查看預覽清單 (前 50 筆)"):
        st.text("\n".join(genes_to_send))

# 執行按鈕與 API 邏輯
if st.button("🚀 生成 Enrichr-KG 分析連結"):
    if not genes_to_send.any():
        st.warning("目前沒有符合條件的基因可以分析。")
    elif not selected_libraries:
        st.warning("請至少選擇一個分析資料庫。")
    else:
        # A. 準備 Description 內容
        final_desc = gene_description if gene_description else "Streamlit_Gene_Explorer"
        
        # B. POST 到 Enrichr API 獲取 userListId
        payload = {
            "list": (None, "\n".join(genes_to_send)),
            "description": (None, final_desc)
        }

        try:
            with st.spinner("正在上傳數據至雲端資料庫..."):
                r = requests.post("https://maayanlab.cloud/Enrichr/addList", files=payload, timeout=10)
                r.raise_for_status()
                uid = r.json().get("userListId")

            if uid:
                # C. 構建雙重參數 URL
                # 1. JSON 內部的 q 參數
                q_json = {
                    "userListId": str(uid),
                    "description": final_desc, # 注入描述至 JSON
                    "libraries": [{"name": lib, "limit": 10} for lib in selected_libraries],
                    "term_limit": 10,
                    "min_lib": 1,
                    "gene_degree": 3,
                    "search": True
                }
                encoded_q = urllib.parse.quote(json.dumps(q_json))
                
                # 2. 外部額外的 description 參數 (加強覆寫)
                encoded_desc = urllib.parse.quote(final_desc)
                
                # 最終合成 URL
                kg_url = f"https://maayanlab.cloud/enrichr-kg?q={encoded_q}&description={encoded_desc}"

                # D. 介面回饋
                st.success(f"✅ 上傳成功！描述已設定為: {final_desc}")
                st.markdown(
                    f"""
                    <div style="background-color:#f0f7ff; padding:25px; border-radius:15px; border: 2px solid #2196f3; text-align:center; margin-top:10px;">
                        <p style="margin-bottom:15px; font-size:16px;">基因數據已準備就緒，請點擊下方連結：</p>
                        <a href="{kg_url}" target="_blank" style="background-color:#2196f3; color:white; padding:12px 30px; border-radius:30px; text-decoration:none; font-weight:bold; font-size:18px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                            🔗 打開 Enrichr-KG 知識圖譜
                        </a>
                        <p style="font-size:12px; color:#666; margin-top:15px;">(進入頁面後，系統將自動填入前 50 筆基因與描述文字)</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            else:
                st.error("無法取得有效的 UserListId。")
        except Exception as e:
            st.error(f"連線至 Enrichr 伺服器時發生錯誤：{e}")

# =====================
# 3. 外部工具
# =====================
st.divider()
st.subheader("3. 其他分析資源")
st.markdown(
    """
    * [KMplot (Breast Cancer)](https://kmplot.com/analysis/index.php?p=service&cancer=breast) - 用於檢查特定基因在乳腺癌中的存活曲線。
    * [Enrichr Main Site](https://maayanlab.cloud/Enrichr/) - 傳統的富集分析介面。
    """
)
