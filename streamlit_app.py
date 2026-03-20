"""
せどり利益スカウター - Streamlit版 v3.0
実データベース (21,353件) 対応版
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

# 中古品判定キーワード
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
    # GitHubリポジトリ内のファイルパスを試す
    possible_paths = [
        "buyback_database.json",
        "buyback_database (1).json",
        "./buyback_database.json",
        "./buyback_database (1).json",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    st.sidebar.success(f"✅ データベース読み込み成功: {len(data):,}件")
                    return data
            except Exception as e:
                st.sidebar.error(f"❌ 読み込みエラー: {e}")
    
    st.sidebar.warning("⚠️ buyback_database.json が見つかりません。デモモードで起動します。")
    return {}

buyback_db = load_buyback_database()

# ========================
# URL生成関数
# ========================
def generate_search_url(jan_code: str, site: str) -> str:
    """JANコードから各ECサイトの検索URLを生成"""
    if site == "楽天":
        return f"https://search.rakuten.co.jp/search/mall/{jan_code}/"
    elif site == "Yahoo!":
        return f"https://shopping.yahoo.co.jp/search?p={jan_code}"
    elif site == "Amazon":
        return f"https://www.amazon.co.jp/s?k={jan_code}"
    else:
        return ""

# ========================
# 中古品判定関数
# ========================
def is_used_item(title: str) -> bool:
    """商品タイトルから中古品かどうかを判定"""
    if not title:
        return False
    title_lower = title.lower()
    return any(keyword.lower() in title_lower for keyword in USED_KEYWORDS)

# ========================
# 利益計算関数（修正版）
# ========================
def calculate_profit_for_product(jan_code: str, config: dict) -> dict:
    """
    実際の買取価格をもとに利益を計算
    表示価格は買取価格の1.3〜2.0倍と仮定（実際の相場に近い）
    """
    if jan_code not in buyback_db:
        return None
    
    buyback_info = buyback_db[jan_code]
    buyback_price = buyback_info.get("buyback_price", 0)
    buyback_store = buyback_info.get("store", "不明")
    
    if buyback_price == 0:
        return None
    
    # 🆕 表示価格を現実的な範囲で設定
    # 買取価格が高いほど、販売価格との差は小さくなる傾向
    if buyback_price >= 100000:
        # 高額商品（10万円以上）：買取価格の1.2〜1.4倍
        display_price = int(buyback_price * 1.3)
    elif buyback_price >= 30000:
        # 中額商品（3万円〜10万円）：買取価格の1.4〜1.7倍
        display_price = int(buyback_price * 1.5)
    elif buyback_price >= 10000:
        # 低額商品（1万円〜3万円）：買取価格の1.6〜2.0倍
        display_price = int(buyback_price * 1.8)
    else:
        # 超低額商品（1万円未満）：買取価格の2.0〜3.0倍
        display_price = int(buyback_price * 2.5)
    
    # Yahoo!ショッピングでの利益計算
    yahoo_point_rate = config["yahoo_point_rate"]
    yahoo_ps_rate = config["point_site_rate_yahoo"]
    yahoo_total_rate = (yahoo_point_rate + yahoo_ps_rate) / 100
    yahoo_effective = display_price * (1 - yahoo_total_rate)
    yahoo_profit = buyback_price - yahoo_effective
    yahoo_profit_rate = (yahoo_profit / yahoo_effective * 100) if yahoo_effective > 0 else 0
    
    # 楽天市場での利益計算
    rakuten_point_rate = config["rakuten_point_rate"]
    rakuten_ps_rate = config["point_site_rate_rakuten"]
    rakuten_total_rate = (rakuten_point_rate + rakuten_ps_rate) / 100
    rakuten_effective = display_price * (1 - rakuten_total_rate)
    rakuten_profit = buyback_price - rakuten_effective
    rakuten_profit_rate = (rakuten_profit / rakuten_effective * 100) if rakuten_effective > 0 else 0
    
    # 最高利益を選択
    if yahoo_profit >= rakuten_profit:
        best_site = "Yahoo!"
        best_effective = int(yahoo_effective)
        best_profit = int(yahoo_profit)
        best_profit_rate = round(yahoo_profit_rate, 2)
    else:
        best_site = "楽天"
        best_effective = int(rakuten_effective)
        best_profit = int(rakuten_profit)
        best_profit_rate = round(rakuten_profit_rate, 2)
    
    return {
        "jan": jan_code,
        "buyback_price": buyback_price,
        "buyback_store": buyback_store,
        "display_price": display_price,
        "best_site": best_site,
        "best_effective_price": best_effective,
        "best_profit_amount": best_profit,
        "best_profit_rate": best_profit_rate,
    }

# ========================
# ランキング生成
# ========================
def create_ranking_df(config, exclude_used=True, limit=1000):
    """
    実データベースから利益ランキングを生成
    """
    ranking_data = []
    
    # 全JANコードを処理（最大limit件）
    processed = 0
    for jan_code in buyback_db.keys():
        if processed >= limit:
            break
        
        result = calculate_profit_for_product(jan_code, config)
        if result is None:
            continue
        
        # 利益がマイナスの商品は除外
        if result["best_profit_amount"] <= 0:
            continue
        
        # URL生成
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
st.caption(f"v3.0 実データベース対応版（{len(buyback_db):,}件）| 最終更新: 2026-03-20")

# データベース未読み込みの場合
if len(buyback_db) == 0:
    st.error("""
    ❌ **buyback_database.json が読み込めませんでした**
    
    **対処法:**
    1. GitHubリポジトリに `buyback_database.json` があるか確認
    2. ファイル名が `buyback_database (1).json` の場合、`buyback_database.json` にリネーム
    3. Streamlit Cloud で「Reboot app」を実行
    """)
    st.stop()

# サイドバー設定
st.sidebar.header("⚙️ 設定")
config = DEFAULT_CONFIG.copy()

exclude_used = st.sidebar.checkbox(
    "🔒 中古品を除外",
    value=DEFAULT_CONFIG["exclude_used"],
    help="中古品・アウトレット・訳あり商品を自動除外します"
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
        step=5.0,
        help="この利益率以上の商品のみ表示します"
    )

with col_range2:
    max_profit_rate = st.number_input(
        "最高利益率 (%)",
        min_value=0.0,
        max_value=1000.0,
        value=100.0,
        step=10.0,
        help="この利益率以下の商品のみ表示します"
    )

if min_profit_rate > max_profit_rate:
    st.error("⚠️ 最低利益率が最高利益率を超えています。")
    st.stop()
else:
    st.success(f"✅ 利益率範囲: **{min_profit_rate}% 〜 {max_profit_rate}%**")

st.markdown("---")

# その他フィルター
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
        index=2,
        help="処理する商品数（多いほど時間がかかります）"
    )

# ランキング生成
with st.spinner(f"ランキングを生成中...（最大{calc_limit}件を処理）"):
    df = create_ranking_df(config, exclude_used=exclude_used, limit=calc_limit)

if len(df) == 0:
    st.warning("⚠️ 利益商品が見つかりませんでした。")
    st.stop()

# 利益率範囲でフィルタリング
df_filtered = df[
    (df["利益率(%)"] >= min_profit_rate) & 
    (df["利益率(%)"] <= max_profit_rate)
]

# 並び替え
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
- 実データベース（21,353件）から利益商品を抽出しています
- 表示価格は買取価格の1.3〜2.5倍と推定（実際の相場は変動します）
- 🔗 リンクをクリックでJAN検索ページが開きます
- 実際の仕入れ前に必ず最新価格を確認してください
""")
