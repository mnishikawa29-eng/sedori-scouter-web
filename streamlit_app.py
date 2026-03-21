"""
せどり利益スカウター - Streamlit版 v4.3
カテゴリ振り分け修正版 + デバッグ情報表示
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
from collections import Counter

# ==================== 設定 ====================
DEFAULT_CONFIG = {
    "min_profit_rate": 5.0,
    "max_profit_rate": 100.0,
    "exclude_used": True,
    "rakuten_point_rate": 15.0,
    "yahoo_point_rate": 20.0,
    "point_site_rate_rakuten": 1.0,
    "point_site_rate_yahoo": 1.2,
    "coupon_discount_rate": 0.0,
    "selected_categories": ["全て"]
}

# 拡張されたジャンル分類（より広範なプレフィックス）
CATEGORIES = {
    "ゲーム機・ソフト": [
        "4902370",  # Nintendo
        "4948872",  # Nintendo (別シリーズ)
        "4976219",  # Sony PlayStation
        "4549576",  # Microsoft Xbox
        "4571331",  # ゲームソフト一般
    ],
    "家電製品": [
        "45499",   # 日本製家電（広範囲）
        "45481",   # 日本製家電
        "45487",   # 日本製家電
        "49607",   # Canon/Nikon等
        "49742",   # 家電メーカー
    ],
    "カメラ・レンズ": [
        "4960759", # Canon
        "4549292", # Nikon
        "4549980", # Sony Camera
        "4548736", # Camera accessories
        "4960999", # Camera brands
    ],
    "美容家電": [
        "4974019", # Dyson
        "4904785", # Panasonic美容
        "4549980", # Sony美容
    ],
    "スマートウォッチ": [
        "0194",    # Apple Watch
        "4549980", # Sony wearables
    ],
    "オーディオ": [
        "4548736", # Audio brands
        "4957054", # JVC
        "4953103", # Sony audio
        "0194252", # Apple AirPods
    ],
    "おもちゃ・ホビー": [
        "4904810", # Bandai
        "4573102", # Takara Tomy
        "4979750", # Konami
        "4543112", # Square Enix
    ],
}

USED_KEYWORDS = [
    "中古", "USED", "used", "Used", "リユース", "再生品", 
    "整備済", "アウトレット", "訳あり", "傷あり", "箱なし",
    "開封品", "展示品", "refurbished"
]

# ==================== 関数 ====================

def load_buyback_database():
    """買取価格データベースを読み込む"""
    possible_paths = [
        "buyback_database.json",
        "./buyback_database.json",
        "../buyback_database.json"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # データ検証
                    valid_data = {}
                    invalid_count = 0
                    
                    for jan_code, info in data.items():
                        if is_valid_jan(jan_code):
                            if isinstance(info, dict):
                                valid_data[jan_code] = info
                            elif isinstance(info, (int, float)):
                                valid_data[jan_code] = {
                                    "buyback_price": info,
                                    "store": "不明",
                                    "updated_at": ""
                                }
                        else:
                            invalid_count += 1
                    
                    st.sidebar.success(f"✅ データ読込: {len(valid_data):,}件")
                    if invalid_count > 0:
                        st.sidebar.warning(f"⚠️ 無効データ除外: {invalid_count}件")
                    
                    # デバッグ: JANコードプレフィックス分布を表示
                    show_jan_prefix_distribution(valid_data)
                    
                    return valid_data
            except Exception as e:
                st.sidebar.error(f"❌ データ読込エラー: {e}")
    
    st.sidebar.error("❌ buyback_database.json が見つかりません")
    return {}

def show_jan_prefix_distribution(data):
    """JANコードのプレフィックス分布を表示（デバッグ用）"""
    prefix_counter = Counter()
    
    for jan_code in data.keys():
        # 最初の4桁をカウント
        if len(jan_code) >= 4:
            prefix_counter[jan_code[:4]] += 1
    
    # 上位10件を表示
    st.sidebar.markdown("### 📊 JANプレフィックス分布（上位10）")
    top_prefixes = prefix_counter.most_common(10)
    
    for prefix, count in top_prefixes:
        category = get_product_category(prefix + "000000000")
        st.sidebar.text(f"{prefix}***: {count}件 → {category}")

def is_valid_jan(jan_code):
    """有効なJANコードかチェック"""
    if not isinstance(jan_code, str):
        return False
    if not jan_code.isdigit():
        return False
    if len(jan_code) not in [8, 13]:
        return False
    # テスト用コード除外
    if jan_code.startswith(("1000000", "9900000", "0000000")):
        return False
    return True

def get_product_category(jan_code):
    """JANコードからカテゴリを判定（改良版）"""
    # 完全一致の長いプレフィックスから順にチェック
    for category, prefixes in CATEGORIES.items():
        for prefix in prefixes:
            if jan_code.startswith(prefix):
                return category
    
    # プレフィックスが一致しない場合、最初の2桁で大まかに分類
    if jan_code.startswith(("45", "49")):
        return "家電製品"
    elif jan_code.startswith("0"):
        return "海外製品"
    
    return "その他"

def generate_search_url(jan_code, site):
    """商品検索URLを生成"""
    urls = {
        "楽天": f"https://search.rakuten.co.jp/search/mall/{jan_code}/",
        "Yahoo!": f"https://shopping.yahoo.co.jp/search?p={jan_code}",
        "Amazon": f"https://www.amazon.co.jp/s?k={jan_code}",
        "価格.com": f"https://kakaku.com/search_results/{jan_code}/"
    }
    return urls.get(site, "")

def is_used_item(title):
    """中古品判定"""
    if not title:
        return False
    return any(keyword in title for keyword in USED_KEYWORDS)

def calculate_profit_for_product(jan_code, buyback_info, config):
    """
    正しい段階的利益計算
    1. 表示価格設定
    2. クーポン適用
    3. ポイント還元適用
    4. 利益計算
    """
    # 買取価格取得
    if isinstance(buyback_info, dict):
        buyback_price = buyback_info.get("buyback_price", 0)
        buyback_store = buyback_info.get("store", "不明")
    elif isinstance(buyback_info, (int, float)):
        buyback_price = buyback_info
        buyback_store = "不明"
    else:
        return None
    
    # 最低買取価格チェック
    if buyback_price < 3000:
        return None
    
    # 表示価格の推定（買取価格の70-85%）
    if buyback_price >= 100000:
        display_price = buyback_price * 0.85
    elif buyback_price >= 50000:
        display_price = buyback_price * 0.80
    elif buyback_price >= 20000:
        display_price = buyback_price * 0.75
    else:
        display_price = buyback_price * 0.70
    
    results = {}
    
    # Yahoo!とRakutenで計算
    for site_name, point_rate, point_site_rate in [
        ("Yahoo!", config["yahoo_point_rate"], config["point_site_rate_yahoo"]),
        ("楽天", config["rakuten_point_rate"], config["point_site_rate_rakuten"])
    ]:
        # 1️⃣ クーポン適用後価格
        coupon_rate = config.get("coupon_discount_rate", 0)
        post_coupon_price = display_price * (1 - coupon_rate / 100)
        
        # 2️⃣ ポイント還元後の実質価格
        total_point_rate = point_rate + point_site_rate
        effective_price = post_coupon_price * (1 - total_point_rate / 100)
        
        # 3️⃣ 利益計算
        profit_amount = buyback_price - effective_price
        profit_rate = (profit_amount / effective_price * 100) if effective_price > 0 else 0
        
        results[site_name] = {
            "display_price": display_price,
            "post_coupon_price": post_coupon_price,
            "effective_price": effective_price,
            "profit_amount": profit_amount,
            "profit_rate": profit_rate,
            "coupon_rate": coupon_rate,
            "point_rate": point_rate,
            "point_site_rate": point_site_rate
        }
    
    # 利益が大きい方を選択
    best_site = max(results.keys(), key=lambda k: results[k]["profit_amount"])
    best_result = results[best_site]
    
    # 利益がマイナスなら除外
    if best_result["profit_amount"] <= 0:
        return None
    
    return {
        "jan_code": jan_code,
        "buyback_price": buyback_price,
        "buyback_store": buyback_store,
        "best_site": best_site,
        "display_price": int(best_result["display_price"]),
        "post_coupon_price": int(best_result["post_coupon_price"]),
        "effective_price": int(best_result["effective_price"]),
        "profit_amount": int(best_result["profit_amount"]),
        "profit_rate": best_result["profit_rate"],
        "coupon_rate": best_result["coupon_rate"],
        "point_rate": best_result["point_rate"],
        "point_site_rate": best_result["point_site_rate"],
        "category": get_product_category(jan_code)
    }

def create_ranking_df(buyback_db, config, limit=1000):
    """ランキングDataFrame作成"""
    results = []
    processed_count = 0
    excluded_count = 0
    category_counts = Counter()
    
    selected_cats = config.get("selected_categories", ["全て"])
    
    for jan_code, buyback_info in list(buyback_db.items())[:limit]:
        processed_count += 1
        
        result = calculate_profit_for_product(jan_code, buyback_info, config)
        
        if result is None:
            excluded_count += 1
            continue
        
        # カテゴリカウント
        category_counts[result["category"]] += 1
        
        # カテゴリフィルタ
        if "全て" not in selected_cats:
            if result["category"] not in selected_cats:
                excluded_count += 1
                continue
        
        # 利益率フィルタ
        if not (config["min_profit_rate"] <= result["profit_rate"] <= config["max_profit_rate"]):
            excluded_count += 1
            continue
        
        results.append(result)
    
    # デバッグ情報表示
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📈 カテゴリ別内訳")
    for cat, count in category_counts.most_common():
        st.sidebar.text(f"{cat}: {count}件")
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"📊 処理: {processed_count}件\n除外: {excluded_count}件\n有効: {len(results)}件")
    
    if not results:
        return pd.DataFrame()
    
    df = pd.DataFrame(results)
    
    # 検索リンク追加
    df["Yahoo!"] = df["jan_code"].apply(lambda x: generate_search_url(x, "Yahoo!"))
    df["楽天"] = df["jan_code"].apply(lambda x: generate_search_url(x, "楽天"))
    df["Amazon"] = df["jan_code"].apply(lambda x: generate_search_url(x, "Amazon"))
    df["価格.com"] = df["jan_code"].apply(lambda x: generate_search_url(x, "価格.com"))
    
    # 列名変更
    df = df.rename(columns={
        "jan_code": "JANコード",
        "buyback_price": "買取価格",
        "buyback_store": "買取店",
        "best_site": "推奨サイト",
        "display_price": "表示価格",
        "post_coupon_price": "クーポン後価格",
        "effective_price": "実質価格",
        "profit_amount": "利益額",
        "profit_rate": "利益率(%)",
        "category": "カテゴリー"
    })
    
    return df.sort_values("利益率(%)", ascending=False).reset_index(drop=True)

def format_profit_rate(rate):
    """利益率の装飾"""
    if rate >= 100:
        return f"🔥 {rate:.1f}%"
    elif rate >= 50:
        return f"⭐ {rate:.1f}%"
    elif rate >= 20:
        return f"✅ {rate:.1f}%"
    else:
        return f"{rate:.1f}%"

# ==================== Streamlit UI ====================

st.set_page_config(
    page_title="せどり利益スカウター",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 せどり利益スカウター v4.3")
st.caption("カテゴリ振り分け修正版 + デバッグ情報表示")

# データ読込
buyback_db = load_buyback_database()

if not buyback_db:
    st.error("❌ データベースが読み込めません")
    st.stop()

# ==================== サイドバー設定 ====================

st.sidebar.header("⚙️ 設定")

# 中古品除外
st.sidebar.subheader("🔍 フィルター")
exclude_used = st.sidebar.checkbox("中古品を除外", value=True)

# カテゴリ選択
st.sidebar.subheader("🏷️ ジャンル選択")
all_categories = ["全て"] + list(CATEGORIES.keys()) + ["その他", "海外製品"]
selected_categories = st.sidebar.multiselect(
    "表示するカテゴリ",
    all_categories,
    default=["全て"]
)

# ポイント還元率
st.sidebar.subheader("💳 ポイント還元率")
rakuten_point = st.sidebar.slider("楽天ポイント還元率 (%)", 0.0, 30.0, 15.0, 0.5)
yahoo_point = st.sidebar.slider("Yahoo!ポイント還元率 (%)", 0.0, 30.0, 20.0, 0.5)
rakuten_ps = st.sidebar.slider("ポイントサイト還元（楽天）(%)", 0.0, 5.0, 1.0, 0.1)
yahoo_ps = st.sidebar.slider("ポイントサイト還元（Yahoo!）(%)", 0.0, 5.0, 1.2, 0.1)

# クーポン割引率
st.sidebar.subheader("🎟️ クーポン相当割引")
coupon_discount = st.sidebar.slider(
    "クーポン値引き率 (%)",
    0.0, 20.0, 0.0, 0.5,
    help="セール期間中のクーポンによる値引き分を想定"
)

# 設定オブジェクト作成
config = {
    "min_profit_rate": 5.0,
    "max_profit_rate": 100.0,
    "exclude_used": exclude_used,
    "rakuten_point_rate": rakuten_point,
    "yahoo_point_rate": yahoo_point,
    "point_site_rate_rakuten": rakuten_ps,
    "point_site_rate_yahoo": yahoo_ps,
    "coupon_discount_rate": coupon_discount,
    "selected_categories": selected_categories
}

# ==================== フィルタ設定 ====================

st.header("📊 利益率ランキング")

col1, col2 = st.columns(2)
with col1:
    min_rate = st.number_input("最低利益率 (%)", 0.0, 500.0, 5.0, 1.0)
with col2:
    max_rate = st.number_input("最高利益率 (%)", 0.0, 10000.0, 100.0, 10.0)

if min_rate > max_rate:
    st.error("❌ 最低利益率は最高利益率より小さくしてください")
    st.stop()

config["min_profit_rate"] = min_rate
config["max_profit_rate"] = max_rate

col3, col4, col5 = st.columns(3)
with col3:
    display_limit = st.selectbox("表示件数", [10, 20, 50, 100, "全て"], index=3)
with col4:
    sort_by = st.selectbox("並び替え", ["利益率(%)", "利益額", "買取価格"])
with col5:
    calc_limit = st.number_input("計算対象件数", 100, 5000, 1000, 100)

# ==================== ランキング生成 ====================

with st.spinner("🔄 利益計算中..."):
    df = create_ranking_df(buyback_db, config, limit=calc_limit)

if df.empty:
    st.warning("⚠️ 条件に合う商品が見つかりませんでした")
    st.info("""
    **対策**:
    - 左サイドバーで「カテゴリ別内訳」を確認してください
    - 最低利益率を下げる
    - 計算対象件数を増やす
    - クーポン割引率を上げる
    - カテゴリを「全て」に変更
    """)
    st.stop()

# 並び替え
df = df.sort_values(sort_by, ascending=False)

# 表示件数制限
if display_limit != "全て":
    df_display = df.head(display_limit)
else:
    df_display = df

# ==================== 統計表示 ====================

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.metric("🛒 商品数", f"{len(df):,}件")
with col_m2:
    st.metric("💰 最高利益", f"¥{df['利益額'].max():,}")
with col_m3:
    st.metric("📈 平均利益率", f"{df['利益率(%)'].mean():.1f}%")
with col_m4:
    st.metric("💵 平均利益額", f"¥{int(df['利益額'].mean()):,}")

# ==================== テーブル表示 ====================

st.markdown("---")

# HTML形式でリンク付きテーブル作成
def make_clickable(url, text="🔗"):
    return f'<a href="{url}" target="_blank">{text}</a>'

df_html = df_display.copy()
df_html.index = df_html.index + 1
df_html["Yahoo!"] = df_html["Yahoo!"].apply(lambda x: make_clickable(x, "Yahoo!"))
df_html["楽天"] = df_html["楽天"].apply(lambda x: make_clickable(x, "楽天"))
df_html["Amazon"] = df_html["Amazon"].apply(lambda x: make_clickable(x, "Amazon"))
df_html["価格.com"] = df_html["価格.com"].apply(lambda x: make_clickable(x, "価格.com"))

# スタイル付きDataFrame
st.write(df_html.to_html(escape=False, index=True), unsafe_allow_html=True)

# ==================== CSVダウンロード ====================

st.markdown("---")

csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
st.download_button(
    label="📥 CSVダウンロード",
    data=csv,
    file_name=f"sedori_ranking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv"
)

# ==================== フッター ====================

st.markdown("---")
st.info(f"""
### ⚠️ 注意事項

**v4.3 新機能**:
- ✅ JANコードプレフィックス分布の可視化
- ✅ カテゴリ別内訳の表示
- ✅ より広範なプレフィックス対応

**計算方法**:
1. 表示価格 = 買取価格 × 0.70-0.85（価格帯により変動）
2. クーポン適用後 = 表示価格 × (1 - クーポン割引率%)
3. 実質価格 = クーポン適用後 × (1 - (ポイント還元率 + ポイントサイト還元率)%)
4. 利益 = 買取価格 - 実質価格
5. 利益率 = (利益 / 実質価格) × 100

**重要**:
- これはデモ版です（データ: {len(buyback_db):,}件）
- 実際の価格・在庫は常に変動します
- 仕入れ前に必ず最新情報を確認してください
""")
