import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime
import time

# ==================== 設定 ====================
GITHUB_REPO = "mnishikawa29-eng/sedori-scouter-web"
DATABASE_VERSION = "v2026.04.10"  # データベースバージョン (更新時に変更)
DATABASE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest/download/buyback_database.json"

DEFAULT_CONFIG = {
    'min_profit_rate': 5.0,
    'max_profit_rate': 100.0,
    'rakuten_point_rate': 15.0,
    'yahoo_point_rate': 1.5,  # 基本還元率
    'yahoo_additional_line': 0.0,  # LINE連携
    'yahoo_additional_lyp': 0.0,  # LYPプレミアム
    'yahoo_additional_store': 0.0,  # ストアポイント
    'yahoo_additional_bonus': 0.0,  # ボーナスストアPlus
    'yahoo_additional_campaign': 0.0,  # キャンペーン
    'point_site_rate_rakuten': 1.0,
    'point_site_rate_yahoo': 1.2,
    'coupon_discount_rate': 0.0,
    'exclude_used': True
}

# ==================== データベース読み込み ====================
@st.cache_data(ttl=3600, show_spinner=False)  # 1時間キャッシュ
def load_buyback_database(version=DATABASE_VERSION):
    """GitHub Releases から買取価格データベースをダウンロード"""
    try:
        st.info(f"📥 データベースを読み込んでいます...\n\nURL: `{DATABASE_URL}`")
        
        response = requests.get(DATABASE_URL, timeout=30)
        response.raise_for_status()
        
        buyback_db = response.json()
        
        st.success(f"✅ データベース読み込み完了: {len(buyback_db):,} 件")
        
        # データ統計
        prices = [info['buyback_price'] for info in buyback_db.values()]
        if prices:
            st.write(f"💰 価格範囲: ¥{min(prices):,} 〜 ¥{max(prices):,}")
            st.write(f"📊 平均価格: ¥{sum(prices)//len(prices):,}")
        
        # バージョン情報を追加
        st.caption(f"📌 データベースバージョン: {version}")
        
        return buyback_db
    
    except requests.exceptions.RequestException as e:
        st.error(f"""
        ❌ データベースの読み込みに失敗しました
        
        **エラー**: {str(e)}
        
        **考えられる原因**:
        1. GitHub Releases にファイルがアップロードされていない
        2. リポジトリ名が間違っている (現在: `{GITHUB_REPO}`)
        3. ネットワーク接続エラー
        
        **対処方法**:
        1. [GitHub Releases]({f'https://github.com/{GITHUB_REPO}/releases'}) を確認
        2. `buyback_database.json` がアップロードされているか確認
        3. このページの左上 `GITHUB_REPO` 変数を正しいリポジトリ名に変更
        """)
        return {}
    
    except json.JSONDecodeError as e:
        st.error(f"❌ JSONパースエラー: {str(e)}")
        return {}

# ==================== API設定 ====================
def get_api_keys():
    """APIキーを取得（環境変数 or サイドバー入力）"""
    rapidapi_key = st.secrets.get("RAPIDAPI_KEY", "")
    rakuten_app_id = st.secrets.get("RAKUTEN_APP_ID", "")
    
    with st.sidebar.expander("🔑 API設定", expanded=False):
        rapidapi_key_input = st.text_input(
            "RapidAPI Key", 
            value=rapidapi_key,
            type="password",
            help="Yahoo!実価格取得用"
        )
        rakuten_app_id_input = st.text_input(
            "楽天アプリID",
            value=rakuten_app_id,
            type="password",
            help="楽天実価格取得用"
        )
        
        if rapidapi_key_input:
            rapidapi_key = rapidapi_key_input
        if rakuten_app_id_input:
            rakuten_app_id = rakuten_app_id_input
    
    return rapidapi_key, rakuten_app_id

# ==================== 価格取得関数 ====================
def search_yahoo_shopping_rapidapi(jan_code, rapidapi_key=None):
    """RapidAPI経由でYahoo!ショッピング価格を取得"""
    if not rapidapi_key:
        return None
    
    try:
        url = "https://real-time-product-search.p.rapidapi.com/search"
        headers = {
            "X-RapidAPI-Key": rapidapi_key,
            "X-RapidAPI-Host": "real-time-product-search.p.rapidapi.com"
        }
        params = {
            "q": jan_code,
            "country": "jp",
            "language": "ja",
            "limit": "30",
            "sort_by": "LOWEST_PRICE"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json().get("data", [])
            yahoo_products = [
                p for p in data 
                if "shopping.yahoo.co.jp" in p.get("product_page_url", "")
            ]
            
            if yahoo_products:
                min_price = min(float(p["offer"]["price"]) for p in yahoo_products)
                return int(min_price)
        
        return None
    
    except Exception as e:
        return None

def search_rakuten_price(jan_code, rakuten_app_id=None):
    """楽天APIで価格を取得"""
    if not rakuten_app_id:
        return None
    
    try:
        url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
        params = {
            "applicationId": rakuten_app_id,
            "keyword": jan_code,
            "hits": 30,
            "sort": "-itemPrice",
            "availability": 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("Items", [])
            if items:
                prices = [item["Item"]["itemPrice"] for item in items]
                return min(prices)
        
        return None
    
    except Exception as e:
        return None

# ==================== 利益計算 ====================
def calculate_profit_yahoo_realistic(jan_code, buyback_info, config, yahoo_price=None):
    """Yahoo!ショッピングの獲得ポイントを考慮した利益計算"""
    # 表示価格（API取得 or 推定）
    if yahoo_price:
        display_price = yahoo_price
    else:
        # 推定価格
        display_price = int(buyback_info['buyback_price'] * 0.80)
    
    # クーポン適用後価格
    post_coupon_price = display_price * (1 - config.get('coupon_discount_rate', 0) / 100)
    
    # Yahoo!合計還元率
    total_yahoo_rate = (
        config.get('yahoo_point_rate', 1.5) +
        config.get('yahoo_additional_line', 0) +
        config.get('yahoo_additional_lyp', 0) +
        config.get('yahoo_additional_store', 0) +
        config.get('yahoo_additional_bonus', 0) +
        config.get('yahoo_additional_campaign', 0) +
        config.get('point_site_rate_yahoo', 1.2)
    )
    
    # 獲得ポイント
    earned_points = post_coupon_price * total_yahoo_rate / 100
    
    # 実質価格
    effective_price = post_coupon_price - earned_points
    
    # 利益
    profit = buyback_info['buyback_price'] - effective_price
    profit_rate = (profit / effective_price * 100) if effective_price > 0 else 0
    
    return {
        'jan_code': jan_code,
        'buyback_price': buyback_info['buyback_price'],
        'store': buyback_info['store'],
        'display_price': int(display_price),
        'post_coupon_price': int(post_coupon_price),
        'earned_points': int(earned_points),
        'earned_points_rate': round(total_yahoo_rate, 1),
        'effective_price': int(effective_price),
        'profit_amount': int(profit),
        'profit_rate': round(profit_rate, 1),
        'site': 'Yahoo!ショッピング',
        'api_success': yahoo_price is not None
    }

# ==================== ランキング生成 ====================
def create_ranking_df(buyback_db, config, limit=50, rapidapi_key=None, rakuten_app_id=None):
    """利益ランキングを生成"""
    results = []
    api_success_count = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    items = list(buyback_db.items())[:limit]
    
    for idx, (jan, info) in enumerate(items):
        status_text.text(f"処理中... {idx+1}/{len(items)}")
        progress_bar.progress((idx + 1) / len(items))
        
        # Yahoo!価格取得
        yahoo_price = search_yahoo_shopping_rapidapi(jan, rapidapi_key)
        if yahoo_price:
            api_success_count += 1
        
        # 利益計算
        result = calculate_profit_yahoo_realistic(jan, info, config, yahoo_price)
        
        # フィルタ
        if config['min_profit_rate'] <= result['profit_rate'] <= config['max_profit_rate']:
            results.append(result)
        
        time.sleep(0.1)  # API制限対策
    
    progress_bar.empty()
    status_text.empty()
    
    # DataFrame作成
    df = pd.DataFrame(results)
    
    if not df.empty:
        st.success(f"✅ Yahoo!実価格取得: {api_success_count}/{len(items)} 件")
    
    return df

# ==================== メインUI ====================
def main():
    st.set_page_config(
        page_title="せどり利益スカウター v5.3",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 せどり利益スカウター v5.3")
    st.caption("週次データ更新対応版 (GitHub Releases連携)")
    
    # データベース読み込み
    buyback_db = load_buyback_database()
    
    if not buyback_db:
        st.stop()
    
    # APIキー取得
    rapidapi_key, rakuten_app_id = get_api_keys()
    
    # サイドバー設定
    st.sidebar.header("⚙️ 設定")
    
    # Yahoo!還元率設定
    with st.sidebar.expander("📊 Yahoo!還元率設定", expanded=True):
        yahoo_base_rate = st.slider("PayPayクレジット基本還元", 0.0, 5.0, 1.5, 0.1)
        line_renkei = st.checkbox("LINE連携 (+5.0%)", value=False)
        lyp_premium = st.checkbox("LYPプレミアム (+2.0%)", value=False)
        store_point = st.checkbox("ストアポイント (+10.0%)", value=True)
        bonus_store = st.checkbox("ボーナスストアPlus (+5.0%)", value=False)
        campaign = st.checkbox("超PayPay祭 (+7.0%)", value=False)
        point_site_yahoo = st.slider("ポイントサイト還元 (Yahoo!)", 0.0, 3.0, 1.2, 0.1)
        
        total_yahoo_rate = (
            yahoo_base_rate +
            (5.0 if line_renkei else 0) +
            (2.0 if lyp_premium else 0) +
            (10.0 if store_point else 0) +
            (5.0 if bonus_store else 0) +
            (7.0 if campaign else 0) +
            point_site_yahoo
        )
        
        st.metric("合計還元率", f"{total_yahoo_rate:.1f}%")
    
    # 利益率フィルタ
    with st.sidebar.expander("💰 利益率フィルタ", expanded=True):
        min_rate = st.number_input("最低利益率 (%)", 0.0, 100.0, 5.0, 1.0)
        max_rate = st.number_input("最高利益率 (%)", 0.0, 200.0, 100.0, 5.0)
    
    # 表示設定
    with st.sidebar.expander("📊 表示設定", expanded=False):
        display_limit = st.number_input("表示件数", 10, 500, 50, 10)
        calc_limit = st.number_input("計算対象件数", 10, 1000, 100, 50)
        sort_by = st.selectbox("並び替え", ["利益率(%)", "利益額", "買取価格"])
    
    # 設定を辞書にまとめる
    config = {
        'min_profit_rate': min_rate,
        'max_profit_rate': max_rate,
        'yahoo_point_rate': yahoo_base_rate,
        'yahoo_additional_line': 5.0 if line_renkei else 0,
        'yahoo_additional_lyp': 2.0 if lyp_premium else 0,
        'yahoo_additional_store': 10.0 if store_point else 0,
        'yahoo_additional_bonus': 5.0 if bonus_store else 0,
        'yahoo_additional_campaign': 7.0 if campaign else 0,
        'point_site_rate_yahoo': point_site_yahoo,
        'coupon_discount_rate': 0.0
    }
    
    # ランキング生成ボタン
    if st.button("🚀 ランキングを生成", type="primary"):
        with st.spinner("利益商品を検索中..."):
            df = create_ranking_df(
                buyback_db,
                config,
                limit=calc_limit,
                rapidapi_key=rapidapi_key,
                rakuten_app_id=rakuten_app_id
            )
        
        if df.empty:
            st.warning("条件に合う商品が見つかりませんでした")
        else:
            # ソート
            sort_col_map = {
                "利益率(%)": "profit_rate",
                "利益額": "profit_amount",
                "買取価格": "buyback_price"
            }
            df = df.sort_values(by=sort_col_map[sort_by], ascending=False)
            
            # 表示
            st.success(f"✅ {len(df)} 件の利益商品を発見!")
            
            # メトリクス
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("商品数", f"{len(df)} 件")
            with col2:
                st.metric("最高利益", f"¥{df['profit_amount'].max():,}")
            with col3:
                st.metric("平均利益率", f"{df['profit_rate'].mean():.1f}%")
            with col4:
                st.metric("平均利益額", f"¥{int(df['profit_amount'].mean()):,}")
            
            # テーブル表示
            st.dataframe(
                df[['jan_code', 'buyback_price', 'display_price', 'earned_points', 
                    'earned_points_rate', 'effective_price', 'profit_amount', 
                    'profit_rate', 'store', 'api_success']].head(display_limit),
                use_container_width=True
            )
            
            # CSV ダウンロード
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                "📥 CSV ダウンロード",
                csv,
                f"profit_ranking_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
    
    # フッター
    st.markdown("---")
    st.info(f"""
    ### 🔒 v5.3 GitHub Releases連携版
    
    **✅ 新機能**:
    - GitHub Releases から最新データを自動取得
    - 週次更新に対応
    - リポジトリサイズを軽量化
    
    **データベース**: {len(buyback_db):,}件
    **データソース**: [GitHub Releases]({f'https://github.com/{GITHUB_REPO}/releases'})
    """)

if __name__ == "__main__":
    main()
