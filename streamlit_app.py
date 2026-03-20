"""
せどり利益スカウター - Streamlit版 v2.0 Lite
（小規模データセットで動作確認用）
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime

# ページ設定
st.set_page_config(
    page_title="せどり利益スカウター",
    page_icon="🔍",
    layout="wide"
)

# デモ用の小規模データベース（100件のみ）
@st.cache_data
def load_demo_database():
    """デモ用の買取価格データベース（100件）"""
    demo_db = {}
    
    # サンプルJANコードと買取価格
    sample_data = [
        ("4580652114028", 4205000, "家電芸人"),
        ("4960759911247", 1269000, "家電芸人"),
        ("4905524984736", 1120000, "ブックオフ"),
        ("4901777049918", 1000000, "ブックオフ"),
        ("4548182202332", 929500, "ウイキャン"),
        ("4549292216165", 909500, "ウイキャン"),
        ("4548182202097", 901000, "ネットオフ"),
        ("4901777188679", 880000, "ネットオフ"),
        ("4548182202127", 870000, "一丁目"),
        ("4547410512786", 855000, "一丁目"),
    ]
    
    # ランダムに100件生成
    import random
    for i in range(100):
        if i < len(sample_data):
            jan, price, store = sample_data[i]
        else:
            jan = f"45{random.randint(10000000000, 99999999999)}"
            price = random.randint(10000, 500000)
            stores = ["家電芸人", "ブックオフ", "ウイキャン", "ネットオフ", "一丁目"]
            store = random.choice(stores)
        
        demo_db[jan] = {
            "buyback_price": price,
            "store": store,
            "updated_at": "2026-03-20 17:45"
        }
    
    return demo_db

# 設定のデフォルト値
DEFAULT_CONFIG = {
    "min_profit_rate": 5.0,
    "rakuten_point_rate": 15.0,
    "yahoo_point_rate": 20.0,
    "point_site_rate_rakuten": 1.0,
    "point_site_rate_yahoo": 1.2,
}

# セッション状態の初期化
if "config" not in st.session_state:
    st.session_state.config = DEFAULT_CONFIG.copy()

buyback_db = load_demo_database()

def calculate_profit(jan_code: str, price: int, point_rate: float, point_site_rate: float = 1.0) -> dict:
    """利益を計算"""
    buyback_data = buyback_db.get(jan_code, {})
    
    if isinstance(buyback_data, dict):
        buyback_price = buyback_data.get("buyback_price", 0)
        store = buyback_data.get("store", "不明")
    else:
        buyback_price = buyback_data
        store = "不明"
    
    if buyback_price == 0:
        return None
    
    total_rate = point_rate + point_site_rate
    effective_price = price * (1 - total_rate / 100)
    profit_amount = buyback_price - effective_price
    profit_rate = (profit_amount / effective_price * 100) if effective_price > 0 else 0
    
    return {
        "buyback_price": buyback_price,
        "buyback_store": store,
        "effective_price": int(effective_price),
        "profit_amount": int(profit_amount),
        "profit_rate": round(profit_rate, 2),
        "total_point_rate": round(total_rate, 2)
    }

def create_profit_ranking_dataframe():
    """利益ランキングのDataFrameを作成"""
    ranking_data = []
    
    for jan_code, buyback_data in buyback_db.items():
        if isinstance(buyback_data, dict):
            buyback_price = buyback_data.get("buyback_price", 0)
            store = buyback_data.get("store", "不明")
        else:
            buyback_price = buyback_data
            store = "不明"
        
        if buyback_price == 0:
            continue
        
        # Yahoo!ショッピングの利益計算
        yahoo_price = 48000
        yahoo_point_rate = st.session_state.config["yahoo_point_rate"]
        yahoo_point_site = st.session_state.config["point_site_rate_yahoo"]
        yahoo_total_rate = yahoo_point_rate + yahoo_point_site
        yahoo_effective = yahoo_price * (1 - yahoo_total_rate / 100)
        yahoo_profit = buyback_price - yahoo_effective
        yahoo_profit_rate = (yahoo_profit / yahoo_effective * 100) if yahoo_effective > 0 else 0
        
        # 楽天市場の利益計算
        rakuten_price = 50000
        rakuten_point_rate = st.session_state.config["rakuten_point_rate"]
        rakuten_point_site = st.session_state.config["point_site_rate_rakuten"]
        rakuten_total_rate = rakuten_point_rate + rakuten_point_site
        rakuten_effective = rakuten_price * (1 - rakuten_total_rate / 100)
        rakuten_profit = buyback_price - rakuten_effective
        rakuten_profit_rate = (rakuten_profit / rakuten_effective * 100) if rakuten_effective > 0 else 0
        
        # 最高利益を選択
        if yahoo_profit >= rakuten_profit:
            best_site = "Yahoo!ショッピング"
            best_effective = int(yahoo_effective)
            best_profit = int(yahoo_profit)
            best_profit_rate = round(yahoo_profit_rate, 2)
        else:
            best_site = "楽天市場"
            best_effective = int(rakuten_effective)
            best_profit = int(rakuten_profit)
            best_profit_rate = round(rakuten_profit_rate, 2)
        
        ranking_data.append({
            "jan": jan_code,
            "buyback_price": buyback_price,
            "buyback_store": store,
            "best_site": best_site,
            "best_effective_price": best_effective,
            "best_profit_amount": best_profit,
            "best_profit_rate": best_profit_rate,
        })
    
    df = pd.DataFrame(ranking_data)
    df = df.sort_values("best_profit_rate", ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    
    return df

# ヘッダー
st.title("🔍 せどり利益スカウター v2.0 Lite")
st.markdown(f"**登録商品数: {len(buyback_db):,}件（デモ版）** | 最終更新: 2026年3月20日")
st.info("ℹ️ これはデモ版です。100件のサンプルデータで動作確認できます。")
st.markdown("---")

# サイドバー：設定
with st.sidebar:
    st.header("⚙️ 設定")
    
    st.session_state.config["rakuten_point_rate"] = st.number_input(
        "楽天市場 (%)",
        min_value=0.0,
        max_value=50.0,
        value=st.session_state.config["rakuten_point_rate"],
        step=1.0
    )
    
    st.session_state.config["yahoo_point_rate"] = st.number_input(
        "Yahoo!ショッピング (%)",
        min_value=0.0,
        max_value=50.0,
        value=st.session_state.config["yahoo_point_rate"],
        step=1.0
    )

# メインコンテンツ
st.header("📊 利益率ランキング")

col1, col2 = st.columns(2)

with col1:
    profit_rate_filter = st.selectbox(
        "利益率フィルター",
        ["すべて", "5%以上", "10%以上", "50%以上", "100%以上", "500%以上"],
        index=1
    )

with col2:
    display_limit = st.selectbox(
        "表示件数",
        [10, 50, 100, "すべて"],
        index=0
    )

with st.spinner("ランキングを生成中..."):
    df_ranking = create_profit_ranking_dataframe()
    
    # フィルター適用
    profit_rate_map = {
        "すべて": 0,
        "5%以上": 5,
        "10%以上": 10,
        "50%以上": 50,
        "100%以上": 100,
        "500%以上": 500
    }
    min_rate = profit_rate_map.get(profit_rate_filter, 0)
    df_ranking = df_ranking[df_ranking["best_profit_rate"] >= min_rate]
    
    # 表示件数制限
    if display_limit != "すべて":
        df_ranking = df_ranking.head(display_limit)
    
    # 統計情報
    st.subheader("📈 統計情報")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("商品数", f"{len(df_ranking):,}件")
    with col2:
        if len(df_ranking) > 0:
            st.metric("平均利益率", f"{df_ranking['best_profit_rate'].mean():.2f}%")
    with col3:
        if len(df_ranking) > 0:
            st.metric("最高利益額", f"¥{df_ranking['best_profit_amount'].max():,}")
    with col4:
        if len(df_ranking) > 0:
            st.metric("平均利益額", f"¥{int(df_ranking['best_profit_amount'].mean()):,}")
    
    # ランキングテーブル
    if len(df_ranking) > 0:
        st.subheader(f"🏆 TOP {len(df_ranking)} 商品")
        
        df_display = df_ranking[[
            "rank", "jan", "buyback_price", "buyback_store",
            "best_site", "best_effective_price", "best_profit_amount", "best_profit_rate"
        ]].copy()
        
        df_display.columns = [
            "順位", "JANコード", "買取価格", "買取店",
            "推奨仕入先", "実質価格", "利益額", "利益率(%)"
        ]
        
        df_display["買取価格"] = df_display["買取価格"].apply(lambda x: f"¥{x:,}")
        df_display["実質価格"] = df_display["実質価格"].apply(lambda x: f"¥{x:,}")
        df_display["利益額"] = df_display["利益額"].apply(lambda x: f"¥{x:,}")
        
        def format_profit_rate(rate):
            if rate >= 1000:
                return f"🔥🔥🔥 {rate:.2f}%"
            elif rate >= 500:
                return f"🔥🔥 {rate:.2f}%"
            elif rate >= 100:
                return f"🔥 {rate:.2f}%"
            else:
                return f"{rate:.2f}%"
        
        df_display["利益率(%)"] = df_display["利益率(%)"].apply(format_profit_rate)
        
        st.dataframe(df_display, use_container_width=True, hide_index=True, height=600)
    else:
        st.warning("⚠️ フィルター条件に一致する商品が見つかりませんでした。")

# フッター
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: gray;'>
    <p>せどり利益スカウター v2.0 Lite（デモ版）</p>
    <p>⚠️ これは100件のサンプルデータで動作するデモ版です。</p>
</div>
""", unsafe_allow_html=True)
