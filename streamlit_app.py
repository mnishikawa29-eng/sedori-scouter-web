import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime
import time
from collections import Counter

# ==================== 設定 ====================
# 最終更新: 2026-04-10 (21,491件のデータベース)
GITHUB_REPO = "mnishikawa29-eng/sedori-scouter-web"
DATABASE_VERSION = "v2026.04.10"  # データベースバージョン (更新時に変更)
DATABASE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest/download/buyback_database.json"

# カテゴリ定義（JANコード先頭4桁でマッピング）
CATEGORY_MAPPING = {
    "カメラ・レンズ": ["4960", "4957", "4547"],
    "ゲーム機・ソフト": ["4902", "4976", "4571"],
    "家電": ["4905", "4974", "4901"],
    "おもちゃ・ホビー": ["4979", "4543", "4904"],
    "美容・健康": ["4903", "4511"],
    "スマートウォッチ": ["4549"],
    "オーディオ": ["4963", "4582"]
}

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
        response = requests.get(DATABASE_URL, timeout=30)
        response.raise_for_status()
        
        buyback_db = response.json()
        
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

# ==================== JANカテゴリ判定 ====================
def get_category_from_jan(jan_code):
    """JANコード先頭4桁からカテゴリを判定"""
    jan_prefix = jan_code[:4]
    for category, prefixes in CATEGORY_MAPPING.items():
        if jan_prefix in prefixes:
            return category
    return "その他"

# ==================== JANプレフィックス分析 ====================
def analyze_jan_prefixes(buyback_db):
    """JANコード先頭4桁の分布を分析"""
    prefixes = [jan[:4] for jan in buyback_db.keys()]
    prefix_counts = Counter(prefixes).most_common(20)
    
    df = pd.DataFrame(prefix_counts, columns=['JANプレフィックス', '商品数'])
    df['割合(%)'] = (df['商品数'] / len(buyback_db) * 100).round(1)
    df['カテゴリ'] = df['JANプレフィックス'].apply(
        lambda x: next((cat for cat, prefs in CATEGORY_MAPPING.items() if x in prefs), "その他")
    )
    
    return df

# ==================== API設定 ====================
def get_api_keys():
    """APIキーを取得（環境変数 or サイドバー入力）"""
    rapidapi_key = st.secrets.get("RAPIDAPI_KEY", "")
    
    with st.sidebar.expander("🔑 API設定", expanded=False):
        rapidapi_key_input = st.text_input(
            "RapidAPI Key", 
            value=rapidapi_key,
            type="password",
            help="Yahoo!ショッピング実価格取得用 (必須)"
        )
        
        if rapidapi_key_input:
            rapidapi_key = rapidapi_key_input
    
    return rapidapi_key

# ==================== Yahoo!ショッピング価格取得（改善版） ====================
def search_yahoo_shopping_rapidapi(jan_code, rapidapi_key=None):
    """RapidAPI経由でYahoo!ショッピング価格を取得（改善版）"""
    if not rapidapi_key:
        return None, "API Key未設定"
    
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
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json().get("data", [])
            
            # Yahoo!ショッピングの商品のみフィルタ
            yahoo_products = [
                p for p in data 
                if "shopping.yahoo.co.jp" in p.get("product_page_url", "")
            ]
            
            if yahoo_products:
                # 最安値を取得
                min_price = min(float(p["offer"]["price"]) for p in yahoo_products)
                return int(min_price), "成功"
            else:
                return None, "Yahoo!商品なし"
        
        elif response.status_code == 403:
            return None, "API制限"
        elif response.status_code == 429:
            return None, "レート制限"
        else:
            return None, f"HTTP {response.status_code}"
    
    except requests.exceptions.Timeout:
        return None, "タイムアウト"
    except requests.exceptions.RequestException as e:
        return None, f"通信エラー"
    except Exception as e:
        return None, f"不明なエラー"

# ==================== 利益計算 ====================
def calculate_profit_yahoo(jan_code, buyback_info, config, yahoo_price=None, api_status="推定"):
    """Yahoo!ショッピングの獲得ポイントを考慮した利益計算"""
    # 表示価格（API取得 or 推定）
    if yahoo_price:
        display_price = yahoo_price
        price_type = "実価格"
    else:
        # 推定価格（買取価格の85%と仮定）※より現実的な値に調整
        display_price = int(buyback_info['buyback_price'] / 0.85)
        price_type = "推定"
    
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
        'category': get_category_from_jan(jan_code),
        'display_price': int(display_price),
        'price_type': price_type,
        'post_coupon_price': int(post_coupon_price),
        'earned_points': int(earned_points),
        'earned_points_rate': round(total_yahoo_rate, 1),
        'effective_price': int(effective_price),
        'profit_amount': int(profit),
        'profit_rate': round(profit_rate, 1),
        'site': 'Yahoo!ショッピング',
        'api_status': api_status
    }

# ==================== ランキング生成（実API対応版） ====================
def create_ranking_df(buyback_db, config, selected_category="すべて", limit=50, rapidapi_key=None):
    """利益ランキングを生成（Yahoo!実API対応版）"""
    
    # APIキーチェック
    if not rapidapi_key:
        st.error("❌ RapidAPI Key が設定されていません。左サイドバーの「🔑 API設定」から設定してください。")
        return pd.DataFrame()
    
    results = []
    api_success_count = 0
    api_fail_reasons = Counter()
    
    # カテゴリフィルタ適用
    if selected_category != "すべて":
        filtered_items = [
            (jan, info) for jan, info in buyback_db.items()
            if get_category_from_jan(jan) == selected_category
        ]
    else:
        filtered_items = list(buyback_db.items())
    
    # 件数制限
    filtered_items = filtered_items[:limit]
    
    if not filtered_items:
        st.warning(f"カテゴリ「{selected_category}」に該当する商品が見つかりませんでした")
        return pd.DataFrame()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, (jan, info) in enumerate(filtered_items):
        status_text.text(f"🔍 Yahoo!価格取得中... {idx+1}/{len(filtered_items)} ({selected_category})")
        progress_bar.progress((idx + 1) / len(filtered_items))
        
        # Yahoo!価格取得
        yahoo_price, api_status = search_yahoo_shopping_rapidapi(jan, rapidapi_key)
        
        if yahoo_price:
            api_success_count += 1
        else:
            api_fail_reasons[api_status] += 1
        
        # 利益計算
        result = calculate_profit_yahoo(jan, info, config, yahoo_price, api_status)
        
        # フィルタ
        if config['min_profit_rate'] <= result['profit_rate'] <= config['max_profit_rate']:
            results.append(result)
        
        # API制限対策（0.2秒待機）
        time.sleep(0.2)
    
    progress_bar.empty()
    status_text.empty()
    
    # DataFrame作成
    df = pd.DataFrame(results)
    
    # 結果サマリー表示
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ API成功", f"{api_success_count}/{len(filtered_items)}")
    with col2:
        success_rate = (api_success_count / len(filtered_items) * 100) if filtered_items else 0
        st.metric("📊 成功率", f"{success_rate:.1f}%")
    with col3:
        st.metric("🎯 利益商品", f"{len(df)} 件")
    
    # 失敗理由の内訳
    if api_fail_reasons:
        with st.expander("⚠️ API取得失敗の詳細", expanded=False):
            fail_df = pd.DataFrame(api_fail_reasons.items(), columns=['理由', '件数'])
            fail_df = fail_df.sort_values('件数', ascending=False)
            st.dataframe(fail_df, use_container_width=True)
    
    return df

# ==================== メインUI ====================
def main():
    st.set_page_config(
        page_title="せどり利益スカウター v6.1",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 せどり利益スカウター v6.1")
    st.caption("Yahoo!ショッピング実価格取得対応版 (GitHub Releases連携)")
    
    # データベース読み込み
    buyback_db = load_buyback_database()
    
    if not buyback_db:
        st.stop()
    
    # データベース情報表示
    st.success(f"✅ データベース読み込み完了: **{len(buyback_db):,} 件**")
    
    prices = [info['buyback_price'] for info in buyback_db.values()]
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 最低買取価格", f"¥{min(prices):,}")
    with col2:
        st.metric("💰 最高買取価格", f"¥{max(prices):,}")
    with col3:
        st.metric("📊 平均買取価格", f"¥{sum(prices)//len(prices):,}")
    
    st.caption(f"📌 データベースバージョン: **{DATABASE_VERSION}**")
    
    # APIキー取得
    rapidapi_key = get_api_keys()
    
    # APIキー警告
    if not rapidapi_key:
        st.warning("""
        ⚠️ **RapidAPI Key が設定されていません**
        
        Yahoo!ショッピングの実価格を取得するには、左サイドバーの「🔑 API設定」から RapidAPI Key を入力してください。
        
        **RapidAPI Key の取得方法**:
        1. [RapidAPI](https://rapidapi.com/) にアクセスして登録
        2. [Real-Time Product Search API](https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-product-search) をサブスクライブ
        3. API Key をコピー
        4. 左サイドバーに貼り付け
        """)
    
    # JANプレフィックス分析
    with st.expander("📊 JANプレフィックス分布（Top 20）", expanded=False):
        prefix_df = analyze_jan_prefixes(buyback_db)
        st.dataframe(prefix_df, use_container_width=True)
    
    # サイドバー設定
    st.sidebar.header("⚙️ 設定")
    
    # カテゴリ選択
    with st.sidebar.expander("📂 カテゴリ選択", expanded=True):
        categories = ["すべて"] + list(CATEGORY_MAPPING.keys())
        selected_category = st.selectbox("カテゴリ", categories, index=0)
    
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
        calc_limit = st.number_input("計算対象件数", 10, 1000, 100, 50, 
                                     help="処理時間目安: 100件=約20秒, 500件=約2分")
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
    if st.button("🚀 ランキングを生成", type="primary", disabled=not rapidapi_key):
        with st.spinner(f"Yahoo!ショッピング実価格を取得中...（カテゴリ: {selected_category}）"):
            df = create_ranking_df(
                buyback_db,
                config,
                selected_category=selected_category,
                limit=calc_limit,
                rapidapi_key=rapidapi_key
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
            st.success(f"🎉 {len(df)} 件の利益商品を発見!")
            
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
            
            # 価格タイプ分布
            price_type_counts = df['price_type'].value_counts()
            if '実価格' in price_type_counts:
                st.info(f"📊 実価格取得: {price_type_counts.get('実価格', 0)} 件 / 推定価格: {price_type_counts.get('推定', 0)} 件")
            
            # テーブル表示
            display_df = df[['category', 'jan_code', 'buyback_price', 'display_price', 'price_type',
                            'earned_points', 'earned_points_rate', 'effective_price', 
                            'profit_amount', 'profit_rate', 'store', 'api_status']].head(display_limit)
            
            # 列名を日本語化
            display_df.columns = ['カテゴリ', 'JANコード', '買取価格', '表示価格', '価格種別',
                                 '獲得pt', '還元率(%)', '実質価格', '利益額', '利益率(%)', 
                                 '買取店', 'API状態']
            
            st.dataframe(display_df, use_container_width=True)
            
            # CSV ダウンロード
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                "📥 CSV ダウンロード",
                csv,
                f"profit_ranking_{selected_category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv"
            )
    
    # フッター
    st.markdown("---")
    st.info(f"""
    ### 🔥 v6.1 Yahoo!ショッピング実価格取得対応版
    
    **✅ 新機能**:
    - Yahoo!ショッピングの実価格を RapidAPI 経由で取得
    - カテゴリ別検索対応（カメラ・ゲーム・家電等）
    - JANプレフィックス分布表示
    - API成功率・失敗理由の詳細表示
    - GitHub Releases から最新データを自動取得
    
    **データベース**: {len(buyback_db):,}件
    **データソース**: [GitHub Releases]({f'https://github.com/{GITHUB_REPO}/releases'})
    
    **処理時間目安**:
    - 50件: 約10秒
    - 100件: 約20秒
    - 500件: 約2分
    """)

if __name__ == "__main__":
    main()
