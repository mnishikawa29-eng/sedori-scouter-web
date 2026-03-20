"""
せどり利益スカウター - Streamlit版
完全無料で動作するWebアプリ
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os

# ページ設定
st.set_page_config(
    page_title="せどり利益スカウター",
    page_icon="🔍",
    layout="wide"
)

# 設定のデフォルト値
DEFAULT_CONFIG = {
    "min_profit_rate": 5.0,
    "exclude_used": True,
    "rakuten_point_rate": 15.0,
    "yahoo_point_rate": 20.0,
    "point_site_rate": 1.0,
    "enabled_sites": ["rakuten", "yahoo", "biccamera", "joshin", "edion", "yamada", "eccurrent"]
}

# セッション状態の初期化
if "config" not in st.session_state:
    st.session_state.config = DEFAULT_CONFIG.copy()

if "watch_list" not in st.session_state:
    st.session_state.watch_list = []

# 買取価格データベースの読み込み
@st.cache_data
def load_buyback_database():
    """買取価格データベースを読み込む"""
    try:
        with open("/mnt/user-data/outputs/buyback_database.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.warning("⚠️ 買取価格データベースが見つかりません。デモモードで動作します。")
        return {}

buyback_db = load_buyback_database()

def calculate_profit(jan_code: str, price: int, point_rate: float, point_site_rate: float = 1.0) -> dict:
    """利益を計算"""
    # 買取価格を取得
    buyback_price = buyback_db.get(jan_code, {}).get("buyback_price", 0)
    
    if buyback_price == 0:
        return None
    
    # 実質価格を計算
    total_rate = point_rate + point_site_rate
    effective_price = price * (1 - total_rate / 100)
    
    # 利益を計算
    profit_amount = buyback_price - effective_price
    profit_rate = (profit_amount / effective_price * 100) if effective_price > 0 else 0
    
    return {
        "buyback_price": buyback_price,
        "effective_price": int(effective_price),
        "profit_amount": int(profit_amount),
        "profit_rate": round(profit_rate, 2),
        "total_point_rate": round(total_rate, 2)
    }

def search_product(jan_code: str):
    """商品を検索（デモデータ）"""
    # デモデータ
    demo_products = [
        {
            "site": "楽天市場",
            "shop": "デモショップ楽天店",
            "price": 50000,
            "point_rate": 15.0,
            "point_site_rate": 1.0,
            "stock": "在庫あり",
            "delivery_days": 3,
            "campaign": "お買い物マラソン対象",
            "url": "https://rakuten.co.jp/demo"
        },
        {
            "site": "Yahoo!ショッピング",
            "shop": "デモショップYahoo!店",
            "price": 52000,
            "point_rate": 20.0,
            "point_site_rate": 1.2,
            "stock": "在庫あり",
            "delivery_days": 2,
            "campaign": "5のつく日",
            "url": "https://shopping.yahoo.co.jp/demo"
        },
        {
            "site": "ビックカメラ.com",
            "shop": "ビックカメラ",
            "price": 52000,
            "point_rate": 15.0,
            "point_site_rate": 0.5,
            "stock": "在庫あり",
            "delivery_days": 2,
            "campaign": "ポイント15%還元",
            "url": "https://biccamera.com/demo"
        }
    ]
    
    results = []
    for product in demo_products:
        profit_info = calculate_profit(
            jan_code,
            product["price"],
            product["point_rate"],
            product["point_site_rate"]
        )
        
        if profit_info:
            results.append({
                **product,
                **profit_info
            })
    
    return results

# ヘッダー
st.title("🔍 せどり利益スカウター")
st.markdown("---")

# サイドバー：設定
with st.sidebar:
    st.header("⚙️ 設定")
    
    st.session_state.config["min_profit_rate"] = st.slider(
        "最低利益率 (%)",
        min_value=0.0,
        max_value=50.0,
        value=st.session_state.config["min_profit_rate"],
        step=1.0
    )
    
    st.session_state.config["exclude_used"] = st.checkbox(
        "中古品を除外",
        value=st.session_state.config["exclude_used"]
    )
    
    st.subheader("還元率設定")
    
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
    
    st.session_state.config["point_site_rate"] = st.number_input(
        "ポイントサイト (%)",
        min_value=0.0,
        max_value=10.0,
        value=st.session_state.config["point_site_rate"],
        step=0.1
    )

# メインコンテンツ
tab1, tab2, tab3 = st.tabs(["🔍 商品検索", "📋 ウォッチリスト", "📊 ランキング"])

# タブ1: 商品検索
with tab1:
    st.header("商品検索")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        jan_input = st.text_input("JANコードを入力", placeholder="4902370517392")
    with col2:
        search_button = st.button("🔍 検索", type="primary", use_container_width=True)
    
    if search_button and jan_input:
        with st.spinner("検索中..."):
            results = search_product(jan_input)
            
            if not results:
                st.error("❌ 商品が見つかりませんでした。")
            else:
                # 利益率でソート
                results_sorted = sorted(results, key=lambda x: x["profit_rate"], reverse=True)
                
                # 最安値（最高利益率）の商品をハイライト
                best = results_sorted[0]
                
                st.success(f"✅ {len(results)}件の販売先が見つかりました")
                
                # ベストオファー表示
                st.subheader("🏆 最もお得な購入先")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("ECサイト", best["site"])
                with col2:
                    st.metric("利益額", f"¥{best['profit_amount']:,}")
                with col3:
                    st.metric("利益率", f"{best['profit_rate']}%")
                with col4:
                    st.metric("買取価格", f"¥{best['buyback_price']:,}")
                
                # 詳細テーブル
                st.subheader("📊 全販売先の比較")
                
                df = pd.DataFrame(results_sorted)
                df_display = df[[
                    "site", "shop", "price", "total_point_rate", "effective_price",
                    "buyback_price", "profit_amount", "profit_rate", "stock", "delivery_days", "campaign"
                ]].copy()
                
                df_display.columns = [
                    "ECサイト", "ショップ名", "表示価格", "総還元率(%)", "実質価格",
                    "買取価格", "利益額", "利益率(%)", "在庫", "配送日数", "キャンペーン"
                ]
                
                # フォーマット
                df_display["表示価格"] = df_display["表示価格"].apply(lambda x: f"¥{x:,}")
                df_display["実質価格"] = df_display["実質価格"].apply(lambda x: f"¥{x:,}")
                df_display["買取価格"] = df_display["買取価格"].apply(lambda x: f"¥{x:,}")
                df_display["利益額"] = df_display["利益額"].apply(lambda x: f"¥{x:,}")
                
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                
                # ウォッチリストに追加ボタン
                if st.button("📌 ウォッチリストに追加"):
                    if jan_input not in [item["jan"] for item in st.session_state.watch_list]:
                        st.session_state.watch_list.append({
                            "jan": jan_input,
                            "name": f"商品 {jan_input}",
                            "best_profit_rate": best["profit_rate"],
                            "best_profit_amount": best["profit_amount"],
                            "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.success("✅ ウォッチリストに追加しました")
                    else:
                        st.warning("⚠️ すでにウォッチリストに登録されています")

# タブ2: ウォッチリスト
with tab2:
    st.header("📋 ウォッチリスト")
    
    if not st.session_state.watch_list:
        st.info("ウォッチリストは空です。商品検索から商品を追加してください。")
    else:
        st.write(f"登録商品数: **{len(st.session_state.watch_list)}件**")
        
        # ウォッチリストをDataFrameに変換
        df_watch = pd.DataFrame(st.session_state.watch_list)
        df_watch_display = df_watch.copy()
        df_watch_display["best_profit_amount"] = df_watch_display["best_profit_amount"].apply(lambda x: f"¥{x:,}")
        df_watch_display.columns = ["JANコード", "商品名", "利益率(%)", "利益額", "登録日時"]
        
        st.dataframe(df_watch_display, use_container_width=True, hide_index=True)
        
        # 一括スキャンボタン
        if st.button("🔄 一括スキャン（全商品の価格を更新）", type="primary"):
            st.info("🚧 この機能は実装中です（デモ版では利用できません）")
        
        # クリアボタン
        if st.button("🗑️ ウォッチリストをクリア", type="secondary"):
            st.session_state.watch_list = []
            st.rerun()

# タブ3: ランキング
with tab3:
    st.header("📊 利益率ランキング")
    
    # データベースから上位商品を表示
    if buyback_db:
        st.info("🚧 ランキング機能は実装中です（デモ版では限定表示）")
        
        # サンプルランキング
        sample_ranking = [
            {"rank": 1, "jan": "4549292230116", "category": "カメラ", "profit_rate": 2073.22, "profit_amount": 784176},
            {"rank": 2, "jan": "4548736162075", "category": "カメラ", "profit_rate": 1850.00, "profit_amount": 700176},
            {"rank": 3, "jan": "4549995434125", "category": "カメラ", "profit_rate": 1319.95, "profit_amount": 494176},
        ]
        
        df_ranking = pd.DataFrame(sample_ranking)
        df_ranking["profit_amount"] = df_ranking["profit_amount"].apply(lambda x: f"¥{x:,}")
        df_ranking.columns = ["順位", "JANコード", "カテゴリ", "利益率(%)", "利益額"]
        
        st.dataframe(df_ranking, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ 買取価格データベースが読み込まれていません。")

# フッター
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>せどり利益スカウター v1.0 | デモ版（無料）</p>
    <p>⚠️ 価格情報はデモデータです。実際の取引前に各サイトで最新情報をご確認ください。</p>
</div>
""", unsafe_allow_html=True)
