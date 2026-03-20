"""
せどり利益スカウター - Streamlit版 v3.2
利益計算ロジック修正版
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os

# ========================
# 設定
# ========================
DEFAULT_CONFIG = {
    "min_profit_rate": 5.0,
    "max_profit_rate": 100.0,
    "exclude_used": True,
    "rakuten_point_rate": 15.0,
    "yahoo_point_rate": 20.0,
    "point_site_rate_rakuten": 1.0,
    "point_site_rate_yahoo": 1.2,
}

USED_KEYWORDS = [
    "中古", "USED", "used", "Used", "リユース", "再生品",
    "整備済", "アウトレット", "訳あり", "傷あり", "箱なし", "展示品"
]

# ========================
# データベース読み込み
# ========================
@st.cache_data
def load_buyback_database():
    """買取価格データベースを読み込み"""
    possible_paths = [
        "buyback_database.json",
        "buyback_database (1).json",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if len(data) > 0:
                        st.sidebar.success(f"✅ データベース読み込み成功: {len(data):,}件")
                    return data
            except Exception as e:
                st.sidebar.error(f"❌ エラー: {e}")
    
    st.sidebar.warning("⚠️ buyback_database.json が見つかりません")
    return {}

buyback_db = load_buyback_database()

# ========================
# URL生成関数
# ========================
def generate_search_url(jan_code: str, site: str) -> str:
    if site == "楽天":
        return f"https://search.rakuten.co.jp/search/mall/{jan_code}/"
    elif site == "Yahoo!":
        return f"https://shopping.yahoo.co.jp/search?p={jan_code}"
    elif site == "Amazon":
        return f"https://www.amazon.co.jp/s?k={jan_code}"
    return ""

def is_used_item(title: str) -> bool:
    if not title:
        return False
    title_lower = title.lower()
    return any(keyword.lower() in title_lower for keyword in USED_KEYWORDS)

# ========================
# 🆕 修正版：利益計算関数
# ========================
def calculate_profit_for_product(jan_code: str, config: dict) -> dict:
    """
    実際の買取価格をもとに利益を計算（修正版）
    表示価格は「買取価格 ÷ (1 - 還元率) × マージン係数」で計算
    """
    if jan_code not in buyback_db:
        return None
    
    buyback_info = buyback_db[jan_code]
    
    if isinstance(buyback_info, dict):
        buyback_price = buyback_info.get("buyback_price", 0)
        buyback_store = buyback_info.get("store", "不明")
    elif isinstance(buyback_info, (int, float)):
        buyback_price = buyback_info
        buyback_store = "不明"
    else:
        return None
    
    if buyback_price == 0 or buyback_price < 500:
        return None
    
    # 🆕 逆算ロジック：利益率10%を確保する表示価格を計算
    yahoo_point_rate = config["yahoo_point_rate"]
    yahoo_ps_rate = config["point_site_rate_yahoo"]
    yahoo_total_rate = (yahoo_point_rate + yahoo_ps_rate) / 100  # 0.212
    
    rakuten_point_rate = config["rakuten_point_rate"]
    rakuten_ps_rate = config["point_site_rate_rakuten"]
    rakuten_total_rate = (rakuten_point_rate + rakuten_ps_rate) / 100  # 0.16
    
    # 🆕 利益率10%を確保する表示価格を計算
    # 買取価格 = 表示価格 × (1 - 還元率) × (1 - 目標利益率)
    # → 表示価格 = 買取価格 / ((1 - 還元率) × (1 - 目標利益率))
    
    target_profit_margin = 0.10  # 目標利益率10%
    
    # Yahoo!での計算
    yahoo_display_price = int(buyback_price / ((1 - yahoo_total_rate) * (1 - target_profit_margin)))
    yahoo_effective = yahoo_display_price * (1 - yahoo_total_rate)
    yahoo_profit = buyback_price - yahoo_effective
    yahoo_profit_rate = (yahoo_profit / yahoo_effective * 100) if yahoo_effective > 0 else 0
    
    # 楽天での計算
    rakuten_display_price = int(buyback_price / ((1 - rakuten_total_rate) * (1 - target_profit_margin)))
    rakuten_effective = rakuten_display_price * (1 - rakuten_total_rate)
    rakuten_profit = buyback_price - rakuten_effective
    rakuten_profit_rate = (rakuten_profit / rakuten_effective * 100) if rakuten_effective > 0 else 0
    
    # 最高利益を選択
    if yahoo_profit >= rakuten_profit:
        best_site = "Yahoo!"
        best_display_price = yahoo_display_price
        best_effective = int(yahoo_effective)
        best_profit = int(yahoo_profit)
        best_profit_rate = round(yahoo_profit_rate, 2)
    else:
        best_site = "楽天"
        best_display_price = rakuten_display_price
        best_effective = int(rakuten_effective)
        best_profit = int(rakuten_profit)
        best_profit_rate = round(rakuten_profit_rate, 2)
    
    return {
        "jan": jan_code,
        "buyback_price": buyback_price,
        "buyback_store": buyback_store,
        "display_price": best_display_price,
        "best_site": best_site,
        "best_effective_price": best_effective,
        "best_profit_amount": best_profit,
        "best_profit_rate": best_profit_rate,
    }

# ========================
# ランキング生成
# ========================
def create_ranking_df(config, exclude_used=True, limit=1000):
    ranking_data = []
    processed = 0
    errors = 0
    
    for jan_code in list(buyback_db.keys())[:limit]:
        try:
            result = calculate_profit_for_product(jan_code, config)
            if result is None:
                continue
            
            if result["best_profit_amount"] <= 0:
                continue
            
            yahoo_url = generate_search_url(jan_code, "Yahoo!")
            rakuten_url = generate_search_url(jan_code, "楽天")
            amazon_url = generate_search_url(jan_code, "Amazon")
            
            ranking_data.append({
                "JAN": jan_code,
                "買取価格": result["buyback_price"],
                "買取店": result["buyback_store"],
                "表示価格": result["display_price"],
                "実質価格": result["best_effective_price"],
                "利益額": result["best_profit_amount"],
                "利益率(%)": result["best_profit_rate"],
                "推奨仕入先": result["best_site"],
                "Yahoo!": yahoo_url,
                "楽天": rakuten_url,
                "Amazon": amazon_url,
            })
            
            processed += 1
            
        except Exception as e:
            errors += 1
            continue
    
    if errors > 0:
        st.sidebar.info(f"ℹ️ 処理: 成功 {processed}件 / エラー {errors}件")
    
    if len(ranking_data) == 0:
        return pd.DataFrame()
    
    df = pd.DataFrame(ranking_data)
    df = df.sort_values("利益率(%)", ascending=False).reset_index(drop=True)
    df.index = df.index + 1
    return df

def format_profit_rate(rate):
    if rate >= 100:
        return f"🔥 {rate:.1f}%"
    elif rate >= 50:
        return f"⭐ {rate:.1f}%"
    elif rate >= 20:
        return f"✅ {rate:.1f}%"
    else:
        return f"{rate:.1f}%"

# ========================
# Streamlit UI
# ========================
st.set_page_config(
    page_title="せどり利益スカウター",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 せどり利益スカウター - 利益ランキング")
st.caption(f"v3.2 利益計算ロジック修正版（{len(buyback_db):,}件）| 最終更新: 2026-03-20")

if len(buyback_db) == 0:
    st.error("❌ buyback_database.json が読み込めませんでした")
    st.stop()

# サイドバー設定
st.sidebar.header("⚙️ 設定")
config = DEFAULT_CONFIG.copy()

exclude_used = st.sidebar.checkbox(
    "🔒 中古品を除外",
    value=DEFAULT_CONFIG["exclude_used"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("還元率設定")

config["rakuten_point_rate"] = st.sidebar.slider(
    "楽天ポイント還元率 (%)", 0.0, 30.0, DEFAULT_CONFIG["rakuten_point_rate"], 0.5
)
config["yahoo_point_rate"] = st.sidebar.slider(
    "Yahoo!ポイント還元率 (%)", 0.0, 30.0, DEFAULT_CONFIG["yahoo_point_rate"], 0.5
)
config["point_site_rate_rakuten"] = st.sidebar.slider(
    "ポイントサイト還元率（楽天）(%)", 0.0, 5.0, DEFAULT_CONFIG["point_site_rate_rakuten"], 0.1
)
config["point_site_rate_yahoo"] = st.sidebar.slider(
    "ポイントサイト還元率（Yahoo!）(%)", 0.0, 5.0, DEFAULT_CONFIG["point_site_rate_yahoo"], 0.1
)

# メイン画面
st.header("📊 利益率ランキング")

filter_status = "🔒 新品のみ" if exclude_used else "📦 新品 + 中古"
st.info(f"**現在のフィルター設定**: {filter_status}")

# 利益率範囲設定
st.subheader("🎯 利益率範囲設定")
col_range1, col_range2 = st.columns(2)

with col_range1:
    min_profit_rate = st.number_input(
        "最低利益率 (%)",
        min_value=0.0,
        max_value=1000.0,
        value=5.0,
        step=5.0
    )

with col_range2:
    max_profit_rate = st.number_input(
        "最高利益率 (%)",
        min_value=0.0,
        max_value=1000.0,
        value=50.0,  # デフォルトを50%に変更
        step=10.0
    )

if min_profit_rate > max_profit_rate:
    st.error("⚠️ 最低利益率が最高利益率を超えています。")
    st.stop()
else:
    st.success(f"✅ 利益率範囲: **{min_profit_rate}% 〜 {max_profit_rate}%**")

st.markdown("---")

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    display_limit = st.selectbox(
        "表示件数",
        [10, 20, 50, 100, 200],
        index=2
    )

with col2:
    sort_by = st.selectbox(
        "並び替え",
        ["利益率順", "利益額順"],
        index=0
    )

with col3:
    calc_limit = st.selectbox(
        "計算対象件数",
        [100, 500, 1000, 5000],
        index=1  # デフォルト500件
    )

# ランキング生成
with st.spinner(f"ランキングを生成中...（{calc_limit}件を処理）"):
    df = create_ranking_df(config, exclude_used=exclude_used, limit=calc_limit)

if len(df) == 0:
    st.warning("⚠️ 利益商品が見つかりませんでした。計算対象件数を増やしてみてください。")
    st.stop()

# 利益率範囲でフィルタリング
df_filtered = df[
    (df["利益率(%)"] >= min_profit_rate) & 
    (df["利益率(%)"] <= max_profit_rate)
]

if sort_by == "利益額順":
    df_filtered = df_filtered.sort_values("利益額", ascending=False)

df_filtered = df_filtered.head(display_limit)

# 統計情報
col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
with col_stat1:
    st.metric("対象商品数", f"{len(df_filtered):,}件")
with col_stat2:
    if len(df_filtered) > 0:
        st.metric("最高利益額", f"¥{df_filtered['利益額'].max():,}")
with col_stat3:
    if len(df_filtered) > 0:
        st.metric("平均利益率", f"{df_filtered['利益率(%)'].mean():.2f}%")
with col_stat4:
    if len(df_filtered) > 0:
        st.metric("平均利益額", f"¥{int(df_filtered['利益額'].mean()):,}")

# テーブル表示
if len(df_filtered) > 0:
    df_display = df_filtered.copy()
    df_display["Yahoo!"] = df_display["Yahoo!"].apply(lambda x: f'<a href="{x}" target="_blank">🔗</a>')
    df_display["楽天"] = df_display["楽天"].apply(lambda x: f'<a href="{x}" target="_blank">🔗</a>')
    df_display["Amazon"] = df_display["Amazon"].apply(lambda x: f'<a href="{x}" target="_blank">🔗</a>')
    
    df_display["買取価格"] = df_display["買取価格"].apply(lambda x: f"¥{x:,}")
    df_display["表示価格"] = df_display["表示価格"].apply(lambda x: f"¥{x:,}")
    df_display["実質価格"] = df_display["実質価格"].apply(lambda x: f"¥{x:,}")
    df_display["利益額"] = df_display["利益額"].apply(lambda x: f"¥{x:,}")
    df_display["利益率(%)"] = df_display["利益率(%)"].apply(format_profit_rate)
    
    st.markdown(
        df_display.to_html(escape=False, index=True),
        unsafe_allow_html=True
    )
    
    csv = df_filtered.to_csv(index=True, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="📥 CSVダウンロード",
        data=csv,
        file_name=f"profit_ranking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
else:
    st.warning("⚠️ 指定された条件に該当する商品が見つかりませんでした。")

# フッター
st.markdown("---")
st.info("""
⚠️ **注意事項**  
- 表示価格は「目標利益率10%を確保できる価格」として逆算
- 実際の販売価格とは異なる場合があります
- 🔗 リンクをクリックで実際の販売価格を確認してください
- 仕入れ前に必ず最新価格を確認してください
""")
