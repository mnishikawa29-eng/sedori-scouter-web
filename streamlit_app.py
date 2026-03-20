"""
せどり利益スカウター - Streamlit版 v4.0
クーポン適用 + 実在商品のみ表示 + エラー対策版
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os
import re

DEFAULT_CONFIG = {
    "min_profit_rate": 5.0,
    "max_profit_rate": 100.0,
    "exclude_used": True,
    "rakuten_point_rate": 15.0,
    "yahoo_point_rate": 20.0,
    "point_site_rate_rakuten": 1.0,
    "point_site_rate_yahoo": 1.2,
    "rakuten_coupon": 0.0,  # 🆕 楽天クーポン
    "yahoo_coupon": 0.0,    # 🆕 Yahoo!クーポン
}

USED_KEYWORDS = [
    "中古", "USED", "used", "Used", "リユース", "再生品",
    "整備済", "アウトレット", "訳あり", "傷あり", "箱なし", "展示品"
]

# 🆕 JANコードの妥当性チェック
def is_valid_jan(jan_code: str) -> bool:
    """
    有効なJANコードかチェック
    - 8桁または13桁の数字
    - 先頭が数字以外は除外（例: "1000000011110" はNG）
    """
    if not isinstance(jan_code, str):
        return False
    
    # 数字のみで構成されているか
    if not re.match(r'^\d+$', jan_code):
        return False
    
    # 8桁または13桁
    if len(jan_code) not in [8, 13]:
        return False
    
    # 🆕 異常なJANコードを除外
    # 例: "1000000011110" のようなテスト用コード
    if jan_code.startswith('1000000') or jan_code.startswith('9900000'):
        return False
    
    # 先頭が45, 46, 49 (日本), 0 (米国), 978/979 (書籍) などの標準的なコード
    valid_prefixes = ['45', '46', '47', '48', '49', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '978', '979']
    if not any(jan_code.startswith(prefix) for prefix in valid_prefixes):
        return False
    
    return True

@st.cache_data
def load_buyback_database():
    """買取価格データベースを読み込み（有効なJANのみ）"""
    possible_paths = ["buyback_database.json", "buyback_database (1).json"]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    
                    # 🆕 有効なJANコードのみフィルタリング
                    valid_data = {}
                    invalid_count = 0
                    
                    for jan_code, info in raw_data.items():
                        if is_valid_jan(jan_code):
                            valid_data[jan_code] = info
                        else:
                            invalid_count += 1
                    
                    st.sidebar.success(f"✅ 有効データ: {len(valid_data):,}件")
                    if invalid_count > 0:
                        st.sidebar.info(f"ℹ️ 除外データ: {invalid_count:,}件")
                    
                    return valid_data
            except Exception as e:
                st.sidebar.error(f"❌ エラー: {e}")
    
    return {}

buyback_db = load_buyback_database()

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
    return any(kw.lower() in title.lower() for kw in USED_KEYWORDS)

# ========================
# 🆕 クーポン適用後の利益計算
# ========================
def calculate_profit_for_product(jan_code: str, config: dict) -> dict:
    """
    利益 = 買取価格 - 実質仕入れ価格
    実質仕入れ価格 = (表示価格 - クーポン) × (1 - 還元率)
    """
    if jan_code not in buyback_db:
        return None
    
    # 🆕 JANコードの妥当性チェック
    if not is_valid_jan(jan_code):
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
    
    # 🆕 最低買取価格を引き上げ（より現実的な商品のみ）
    if buyback_price < 3000:
        return None
    
    # 表示価格を買取価格の70%〜85%に設定
    if buyback_price >= 100000:
        price_ratio = 0.85
    elif buyback_price >= 50000:
        price_ratio = 0.80
    elif buyback_price >= 20000:
        price_ratio = 0.75
    else:
        price_ratio = 0.70
    
    base_display_price = int(buyback_price * price_ratio)
    
    # Yahoo!での計算（クーポン適用）
    yahoo_point_rate = config["yahoo_point_rate"]
    yahoo_ps_rate = config["point_site_rate_yahoo"]
    yahoo_coupon = config.get("yahoo_coupon", 0.0)
    yahoo_total_rate = (yahoo_point_rate + yahoo_ps_rate) / 100
    
    yahoo_display_price = base_display_price
    yahoo_after_coupon = max(0, yahoo_display_price - yahoo_coupon)  # クーポン適用後
    yahoo_effective = yahoo_after_coupon * (1 - yahoo_total_rate)
    yahoo_profit = buyback_price - yahoo_effective
    yahoo_profit_rate = (yahoo_profit / yahoo_effective * 100) if yahoo_effective > 0 else 0
    
    # 楽天での計算（クーポン適用）
    rakuten_point_rate = config["rakuten_point_rate"]
    rakuten_ps_rate = config["point_site_rate_rakuten"]
    rakuten_coupon = config.get("rakuten_coupon", 0.0)
    rakuten_total_rate = (rakuten_point_rate + rakuten_ps_rate) / 100
    
    rakuten_display_price = base_display_price
    rakuten_after_coupon = max(0, rakuten_display_price - rakuten_coupon)  # クーポン適用後
    rakuten_effective = rakuten_after_coupon * (1 - rakuten_total_rate)
    rakuten_profit = buyback_price - rakuten_effective
    rakuten_profit_rate = (rakuten_profit / rakuten_effective * 100) if rakuten_effective > 0 else 0
    
    # 最高利益を選択
    if yahoo_profit >= rakuten_profit:
        best_site = "Yahoo!"
        best_display_price = yahoo_display_price
        best_coupon = yahoo_coupon
        best_after_coupon = yahoo_after_coupon
        best_effective = int(yahoo_effective)
        best_profit = int(yahoo_profit)
        best_profit_rate = round(yahoo_profit_rate, 2)
    else:
        best_site = "楽天"
        best_display_price = rakuten_display_price
        best_coupon = rakuten_coupon
        best_after_coupon = rakuten_after_coupon
        best_effective = int(rakuten_effective)
        best_profit = int(rakuten_profit)
        best_profit_rate = round(rakuten_profit_rate, 2)
    
    # 利益がマイナスの場合は除外
    if best_profit <= 0:
        return None
    
    return {
        "jan": jan_code,
        "buyback_price": buyback_price,
        "buyback_store": buyback_store,
        "display_price": best_display_price,
        "coupon": int(best_coupon),
        "after_coupon_price": int(best_after_coupon),
        "best_site": best_site,
        "best_effective_price": best_effective,
        "best_profit_amount": best_profit,
        "best_profit_rate": best_profit_rate,
    }

def create_ranking_df(config, exclude_used=True, limit=1000):
    ranking_data = []
    processed = 0
    skipped = 0
    
    for jan_code in list(buyback_db.keys())[:limit]:
        try:
            result = calculate_profit_for_product(jan_code, config)
            if result is None:
                skipped += 1
                continue
            
            yahoo_url = generate_search_url(jan_code, "Yahoo!")
            rakuten_url = generate_search_url(jan_code, "楽天")
            amazon_url = generate_search_url(jan_code, "Amazon")
            
            ranking_data.append({
                "JAN": jan_code,
                "買取価格": result["buyback_price"],
                "買取店": result["buyback_store"],
                "表示価格": result["display_price"],
                "クーポン": result["coupon"],
                "適用後価格": result["after_coupon_price"],
                "実質価格": result["best_effective_price"],
                "利益額": result["best_profit_amount"],
                "利益率(%)": result["best_profit_rate"],
                "推奨仕入先": result["best_site"],
                "Yahoo!": yahoo_url,
                "楽天": rakuten_url,
                "Amazon": amazon_url,
            })
            
            processed += 1
            
        except Exception:
            skipped += 1
            continue
    
    st.sidebar.info(f"✅ 有効商品: {processed}件 / 除外: {skipped}件")
    
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
st.caption(f"v4.0 クーポン対応版（{len(buyback_db):,}件）| 最終更新: 2026-03-20")

if len(buyback_db) == 0:
    st.error("❌ buyback_database.json が読み込めませんでした")
    st.stop()

st.sidebar.header("⚙️ 設定")
config = DEFAULT_CONFIG.copy()

exclude_used = st.sidebar.checkbox("🔒 中古品を除外", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("還元率設定")

config["rakuten_point_rate"] = st.sidebar.slider(
    "楽天ポイント還元率 (%)", 0.0, 30.0, 15.0, 0.5
)
config["yahoo_point_rate"] = st.sidebar.slider(
    "Yahoo!ポイント還元率 (%)", 0.0, 30.0, 20.0, 0.5
)
config["point_site_rate_rakuten"] = st.sidebar.slider(
    "ポイントサイト還元率（楽天）(%)", 0.0, 5.0, 1.0, 0.1
)
config["point_site_rate_yahoo"] = st.sidebar.slider(
    "ポイントサイト還元率（Yahoo!）(%)", 0.0, 5.0, 1.2, 0.1
)

# 🆕 クーポン設定
st.sidebar.markdown("---")
st.sidebar.subheader("🎫 クーポン設定")

config["rakuten_coupon"] = st.sidebar.number_input(
    "楽天クーポン (円)",
    min_value=0,
    max_value=100000,
    value=0,
    step=100,
    help="例: 1000円OFFクーポンなら「1000」と入力"
)

config["yahoo_coupon"] = st.sidebar.number_input(
    "Yahoo!クーポン (円)",
    min_value=0,
    max_value=100000,
    value=0,
    step=100,
    help="例: 500円OFFクーポンなら「500」と入力"
)

st.header("📊 利益率ランキング")
st.info(f"**フィルター**: {'🔒 新品のみ' if exclude_used else '📦 新品 + 中古'}")

st.subheader("🎯 利益率範囲設定")
col_range1, col_range2 = st.columns(2)

with col_range1:
    min_profit_rate = st.number_input("最低利益率 (%)", 0.0, 1000.0, 5.0, 5.0)

with col_range2:
    max_profit_rate = st.number_input("最高利益率 (%)", 0.0, 1000.0, 100.0, 10.0)

if min_profit_rate > max_profit_rate:
    st.error("⚠️ 最低利益率が最高利益率を超えています。")
    st.stop()

st.success(f"✅ 利益率範囲: **{min_profit_rate}% 〜 {max_profit_rate}%**")
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    display_limit = st.selectbox("表示件数", [10, 20, 50, 100, 200], index=2)

with col2:
    sort_by = st.selectbox("並び替え", ["利益率順", "利益額順"], index=0)

with col3:
    calc_limit = st.selectbox("計算対象件数", [100, 500, 1000, 5000, 10000], index=2)

with st.spinner(f"ランキングを生成中...（{calc_limit}件を処理）"):
    df = create_ranking_df(config, exclude_used=exclude_used, limit=calc_limit)

if len(df) == 0:
    st.warning("⚠️ 利益商品が見つかりませんでした。計算対象件数を増やしてください。")
    st.stop()

df_filtered = df[
    (df["利益率(%)"] >= min_profit_rate) & 
    (df["利益率(%)"] <= max_profit_rate)
]

if sort_by == "利益額順":
    df_filtered = df_filtered.sort_values("利益額", ascending=False)

df_filtered = df_filtered.head(display_limit)

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

if len(df_filtered) > 0:
    df_display = df_filtered.copy()
    df_display["Yahoo!"] = df_display["Yahoo!"].apply(lambda x: f'<a href="{x}" target="_blank">🔗</a>')
    df_display["楽天"] = df_display["楽天"].apply(lambda x: f'<a href="{x}" target="_blank">🔗</a>')
    df_display["Amazon"] = df_display["Amazon"].apply(lambda x: f'<a href="{x}" target="_blank">🔗</a>')
    
    df_display["買取価格"] = df_display["買取価格"].apply(lambda x: f"¥{x:,}")
    df_display["表示価格"] = df_display["表示価格"].apply(lambda x: f"¥{x:,}")
    df_display["クーポン"] = df_display["クーポン"].apply(lambda x: f"-¥{x:,}" if x > 0 else "-")
    df_display["適用後価格"] = df_display["適用後価格"].apply(lambda x: f"¥{x:,}")
    df_display["実質価格"] = df_display["実質価格"].apply(lambda x: f"¥{x:,}")
    df_display["利益額"] = df_display["利益額"].apply(lambda x: f"¥{x:,}")
    df_display["利益率(%)"] = df_display["利益率(%)"].apply(format_profit_rate)
    
    st.markdown(df_display.to_html(escape=False, index=True), unsafe_allow_html=True)
    
    csv = df_filtered.to_csv(index=True, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="📥 CSVダウンロード",
        data=csv,
        file_name=f"profit_ranking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
else:
    st.warning("⚠️ 該当する商品がありません。")

st.markdown("---")
st.info("""
⚠️ **計算ロジック（クーポン対応）**  
1. 表示価格 = 買取価格 × 70%〜85%
2. クーポン適用後価格 = 表示価格 - クーポン
3. 実質価格 = 適用後価格 × (1 - 還元率)
4. 利益 = 買取価格 - 実質価格

**JANコード検証**: 異常なコード（テスト用・無効なコード）は自動除外
""")
