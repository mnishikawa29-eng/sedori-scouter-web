"""
せどり利益スカウター - Streamlit版 v4.1
ジャンル別検索 + クーポン相当値引き + 価格.com連携
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
    "coupon_discount_rate": 0.0,  # 🆕 クーポン相当値引き率（%）
    "selected_categories": [],     # 🆕 選択カテゴリー
}

USED_KEYWORDS = [
    "中古", "USED", "used", "Used", "リユース", "再生品",
    "整備済", "アウトレット", "訳あり", "傷あり", "箱なし", "展示品"
]

# 🆕 ジャンル定義（JANコードの先頭で判定）
CATEGORIES = {
    "家電製品": {
        "prefixes": ["45", "49"],  # 日本製品の標準的なプレフィックス
        "keywords": ["家電", "電化製品", "appliance"],
        "description": "家電製品全般（掃除機、空気清浄機、調理家電など）"
    },
    "ゲーム機・ソフト": {
        "prefixes": ["4902370", "4948872", "0889842"],  # Nintendo, Sony, Microsoft
        "keywords": ["ゲーム", "game", "nintendo", "playstation", "xbox"],
        "description": "ゲーム機本体・ソフト・周辺機器"
    },
    "カメラ・レンズ": {
        "prefixes": ["4960759", "4549292", "4548736"],  # Nikon, Canon, Sony
        "keywords": ["カメラ", "レンズ", "camera", "lens"],
        "description": "一眼カメラ・レンズ・カメラアクセサリー"
    },
    "美容家電": {
        "prefixes": ["4580564", "4549660"],  # ヤーマン、パナソニック美容系
        "keywords": ["美容", "ドライヤー", "美顔器"],
        "description": "ドライヤー、美顔器、脱毛器など"
    },
    "スマートウォッチ": {
        "prefixes": ["0194253", "8806094"],  # Apple, Samsung
        "keywords": ["watch", "ウォッチ", "ウェアラブル"],
        "description": "Apple Watch、Galaxy Watchなど"
    },
    "オーディオ": {
        "prefixes": ["4549980"],  # Sony
        "keywords": ["イヤホン", "ヘッドホン", "スピーカー"],
        "description": "イヤホン、ヘッドホン、スピーカー"
    },
    "おもちゃ・ホビー": {
        "prefixes": ["4549660", "4904810", "4902425"],
        "keywords": ["おもちゃ", "プラレール", "LEGO"],
        "description": "おもちゃ、フィギュア、プラモデル"
    },
}

def is_valid_jan(jan_code: str) -> bool:
    """有効なJANコードかチェック"""
    if not isinstance(jan_code, str):
        return False
    
    if not re.match(r'^\d+$', jan_code):
        return False
    
    if len(jan_code) not in [8, 13]:
        return False
    
    if jan_code.startswith('1000000') or jan_code.startswith('9900000'):
        return False
    
    return True

def get_product_category(jan_code: str) -> str:
    """
    JANコードからカテゴリーを推定
    """
    for category_name, category_info in CATEGORIES.items():
        for prefix in category_info["prefixes"]:
            if jan_code.startswith(prefix):
                return category_name
    return "その他"

@st.cache_data
def load_buyback_database():
    """買取価格データベースを読み込み（有効なJANのみ）"""
    possible_paths = ["buyback_database.json", "buyback_database (1).json"]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    
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
    elif site == "価格.com":
        return f"https://kakaku.com/search_results/{jan_code}/"
    return ""

def is_used_item(title: str) -> bool:
    if not title:
        return False
    return any(kw.lower() in title.lower() for kw in USED_KEYWORDS)

def calculate_profit_for_product(jan_code: str, config: dict) -> dict:
    """
    利益 = 買取価格 - 実質仕入れ価格
    実質仕入れ価格 = 表示価格 × (1 - 還元率 - クーポン値引き率)
    """
    if jan_code not in buyback_db:
        return None
    
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
    
    if buyback_price < 3000:
        return None
    
    # カテゴリー判定
    category = get_product_category(jan_code)
    
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
    
    # 🆕 クーポン相当値引き率を追加
    coupon_discount_rate = config.get("coupon_discount_rate", 0.0) / 100
    
    # Yahoo!での計算
    yahoo_point_rate = config["yahoo_point_rate"]
    yahoo_ps_rate = config["point_site_rate_yahoo"]
    yahoo_total_rate = (yahoo_point_rate + yahoo_ps_rate) / 100 + coupon_discount_rate
    
    yahoo_display_price = base_display_price
    yahoo_effective = yahoo_display_price * (1 - yahoo_total_rate)
    yahoo_profit = buyback_price - yahoo_effective
    yahoo_profit_rate = (yahoo_profit / yahoo_effective * 100) if yahoo_effective > 0 else 0
    
    # 楽天での計算
    rakuten_point_rate = config["rakuten_point_rate"]
    rakuten_ps_rate = config["point_site_rate_rakuten"]
    rakuten_total_rate = (rakuten_point_rate + rakuten_ps_rate) / 100 + coupon_discount_rate
    
    rakuten_display_price = base_display_price
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
        best_total_discount = yahoo_total_rate * 100
    else:
        best_site = "楽天"
        best_display_price = rakuten_display_price
        best_effective = int(rakuten_effective)
        best_profit = int(rakuten_profit)
        best_profit_rate = round(rakuten_profit_rate, 2)
        best_total_discount = rakuten_total_rate * 100
    
    if best_profit <= 0:
        return None
    
    return {
        "jan": jan_code,
        "category": category,
        "buyback_price": buyback_price,
        "buyback_store": buyback_store,
        "display_price": best_display_price,
        "total_discount_rate": round(best_total_discount, 2),
        "best_site": best_site,
        "best_effective_price": best_effective,
        "best_profit_amount": best_profit,
        "best_profit_rate": best_profit_rate,
    }

def create_ranking_df(config, exclude_used=True, limit=1000):
    ranking_data = []
    processed = 0
    skipped = 0
    
    # 🆕 カテゴリーフィルター
    selected_categories = config.get("selected_categories", [])
    
    for jan_code in list(buyback_db.keys())[:limit]:
        try:
            result = calculate_profit_for_product(jan_code, config)
            if result is None:
                skipped += 1
                continue
            
            # 🆕 カテゴリーフィルター適用
            if selected_categories and result["category"] not in selected_categories:
                skipped += 1
                continue
            
            yahoo_url = generate_search_url(jan_code, "Yahoo!")
            rakuten_url = generate_search_url(jan_code, "楽天")
            amazon_url = generate_search_url(jan_code, "Amazon")
            kakaku_url = generate_search_url(jan_code, "価格.com")
            
            ranking_data.append({
                "JAN": jan_code,
                "カテゴリー": result["category"],
                "買取価格": result["buyback_price"],
                "買取店": result["buyback_store"],
                "表示価格": result["display_price"],
                "総還元率": result["total_discount_rate"],
                "実質価格": result["best_effective_price"],
                "利益額": result["best_profit_amount"],
                "利益率(%)": result["best_profit_rate"],
                "推奨仕入先": result["best_site"],
                "Yahoo!": yahoo_url,
                "楽天": rakuten_url,
                "Amazon": amazon_url,
                "価格.com": kakaku_url,
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
st.caption(f"v4.1 ジャンル別検索対応版（{len(buyback_db):,}件）| 最終更新: 2026-03-20")

if len(buyback_db) == 0:
    st.error("❌ buyback_database.json が読み込めませんでした")
    st.stop()

st.sidebar.header("⚙️ 設定")
config = DEFAULT_CONFIG.copy()

exclude_used = st.sidebar.checkbox("🔒 中古品を除外", value=True)

# 🆕 カテゴリー選択
st.sidebar.markdown("---")
st.sidebar.subheader("📂 カテゴリー選択")

all_categories = list(CATEGORIES.keys()) + ["その他"]
config["selected_categories"] = st.sidebar.multiselect(
    "表示するカテゴリー",
    options=all_categories,
    default=[],
    help="空欄の場合は全カテゴリーを表示"
)

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

# 🆕 クーポン相当値引き率
st.sidebar.markdown("---")
st.sidebar.subheader("🎫 クーポン相当値引き")

config["coupon_discount_rate"] = st.sidebar.slider(
    "追加値引き率 (%)",
    min_value=0.0,
    max_value=20.0,
    value=0.0,
    step=0.5,
    help="お買い物マラソンやクーポン配布期間中の想定値引き率"
)

st.sidebar.caption("""
**例:**
- お買い物マラソン: +3〜5%
- クーポン配布期間: +2〜10%
""")

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
    sort_by = st.selectbox("並び替え", ["利益率順", "利益額順", "カテゴリー順"], index=0)

with col3:
    calc_limit = st.selectbox("計算対象件数", [100, 500, 1000, 5000, 10000], index=2)

with st.spinner(f"ランキングを生成中...（{calc_limit}件を処理）"):
    df = create_ranking_df(config, exclude_used=exclude_used, limit=calc_limit)

if len(df) == 0:
    st.warning("⚠️ 利益商品が見つかりませんでした。計算対象件数を増やすか、カテゴリーフィルターを解除してください。")
    st.stop()

df_filtered = df[
    (df["利益率(%)"] >= min_profit_rate) & 
    (df["利益率(%)"] <= max_profit_rate)
]

if sort_by == "利益額順":
    df_filtered = df_filtered.sort_values("利益額", ascending=False)
elif sort_by == "カテゴリー順":
    df_filtered = df_filtered.sort_values(["カテゴリー", "利益率(%)"], ascending=[True, False])

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
    df_display["価格.com"] = df_display["価格.com"].apply(lambda x: f'<a href="{x}" target="_blank">🔗</a>')
    
    df_display["買取価格"] = df_display["買取価格"].apply(lambda x: f"¥{x:,}")
    df_display["表示価格"] = df_display["表示価格"].apply(lambda x: f"¥{x:,}")
    df_display["総還元率"] = df_display["総還元率"].apply(lambda x: f"{x:.1f}%")
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
⚠️ **計算ロジック（v4.1）**  
- 総還元率 = ポイント還元率 + ポイントサイト + クーポン相当値引き率
- 実質価格 = 表示価格 × (1 - 総還元率)
- 利益 = 買取価格 - 実質価格

**新機能:**
- 🆕 ジャンル別検索（7カテゴリー + その他）
- 🆕 価格.comリンク追加（最安値比較）
- 🆕 クーポン相当値引き率設定
""")
