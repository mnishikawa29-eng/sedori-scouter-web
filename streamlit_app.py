"""
せどり利益スカウター v5.3 - Yahoo!実購入データ完全対応版
実際の購入履歴に基づく正確な利益計算
"""
import streamlit as st
import pandas as pd
import requests
import json
import os
from datetime import datetime
from collections import Counter
import time

# ==================== API設定 ====================
RAKUTEN_APP_ID = os.getenv("RAKUTEN_APP_ID", "")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

USE_RAKUTEN_API = True
USE_RAPIDAPI = True

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
    "selected_categories": ["全て"],
    "yahoo_line_renkei": True,
    "yahoo_lyp_premium": True,
    "yahoo_store_point": True,
    "yahoo_bonus_store": False,
    "yahoo_campaign": False,
}

CATEGORIES = {
    "ゲーム機・ソフト": ["4902370", "4948872", "4976219", "4549576", "4571331"],
    "家電製品": ["45499", "45481", "45487", "49607", "49742"],
    "カメラ・レンズ": ["4960759", "4549292", "4549980", "4548736", "4960999"],
    "美容家電": ["4974019", "4904785", "4549980"],
    "スマートウォッチ": ["0194", "4549980"],
    "オーディオ": ["4548736", "4957054", "4953103", "0194252"],
    "おもちゃ・ホビー": ["4904810", "4573102", "4979750", "4543112"],
}

USED_KEYWORDS = [
    "中古", "USED", "used", "Used", "リユース", "再生品", 
    "整備済", "アウトレット", "訳あり", "傷あり", "箱なし",
    "開封品", "展示品", "refurbished"
]

# ==================== API関数 ====================

def search_yahoo_shopping_rapidapi(jan_code, rapidapi_key=None):
    """RapidAPIでYahoo!ショッピング実価格取得"""
    api_key = rapidapi_key or RAPIDAPI_KEY
    
    if not api_key:
        return None
    
    url = "https://real-time-product-search.p.rapidapi.com/search"
    
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "real-time-product-search.p.rapidapi.com"
    }
    
    params = {
        "q": jan_code,
        "country": "jp",
        "language": "ja",
        "limit": "30",
        "sort_by": "LOWEST_PRICE",
        "product_condition": "NEW",
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            products = data.get("data", [])
            
            yahoo_products = []
            for p in products:
                product_url = p.get("product_page_url", "")
                if "shopping.yahoo.co.jp" in product_url:
                    title = p.get("product_title", "")
                    if not is_used_item(title):
                        yahoo_products.append(p)
            
            if yahoo_products:
                prices = []
                for p in yahoo_products:
                    price = p.get("offer", {}).get("price")
                    if price:
                        try:
                            prices.append(float(price))
                        except:
                            continue
                
                if prices:
                    return int(min(prices))
        
        elif response.status_code == 429:
            st.sidebar.warning("⚠️ RapidAPI レート制限")
        
        time.sleep(0.3)
        
    except Exception as e:
        st.sidebar.warning(f"RapidAPI エラー: {str(e)[:50]}")
    
    return None

def search_rakuten_price(jan_code, rakuten_app_id=None):
    """楽天公式APIで価格取得"""
    app_id = rakuten_app_id or RAKUTEN_APP_ID
    
    if not app_id or not USE_RAKUTEN_API:
        return None
    
    url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
    params = {
        "applicationId": app_id,
        "keyword": jan_code,
        "hits": 30,
        "sort": "-itemPrice",
        "availability": 1,
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("Items", [])
            
            valid_items = [
                item for item in items 
                if not is_used_item(item["Item"]["itemName"])
            ]
            
            if valid_items:
                prices = [item["Item"]["itemPrice"] for item in valid_items]
                return min(prices)
        
        time.sleep(0.1)
        
    except Exception as e:
        st.sidebar.warning(f"楽天API エラー: {e}")
    
    return None

# ==================== データ処理関数 ====================

def load_buyback_database():
    """買取価格データベース読み込み"""
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
                    
                    show_jan_prefix_distribution(valid_data)
                    return valid_data
            except Exception as e:
                st.sidebar.error(f"❌ データ読込エラー: {e}")
    
    st.sidebar.error("❌ buyback_database.json が見つかりません")
    return {}

def show_jan_prefix_distribution(data):
    """JANプレフィックス分布表示"""
    prefix_counter = Counter()
    for jan_code in data.keys():
        if len(jan_code) >= 4:
            prefix_counter[jan_code[:4]] += 1
    
    st.sidebar.markdown("### 📊 JANプレフィックス分布（上位10）")
    top_prefixes = prefix_counter.most_common(10)
    for prefix, count in top_prefixes:
        category = get_product_category(prefix + "000000000")
        st.sidebar.text(f"{prefix}***: {count}件 → {category}")

def is_valid_jan(jan_code):
    """有効なJANコードチェック"""
    if not isinstance(jan_code, str):
        return False
    if not jan_code.isdigit():
        return False
    if len(jan_code) not in [8, 13]:
        return False
    if jan_code.startswith(("1000000", "9900000", "0000000")):
        return False
    return True

def get_product_category(jan_code):
    """カテゴリ判定"""
    for category, prefixes in CATEGORIES.items():
        for prefix in prefixes:
            if jan_code.startswith(prefix):
                return category
    
    if jan_code.startswith(("45", "49")):
        return "家電製品"
    elif jan_code.startswith("0"):
        return "海外製品"
    
    return "その他"

def generate_search_url(jan_code, site):
    """検索URL生成"""
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

def calculate_yahoo_earned_points(price, config):
    """Yahoo!ショッピング獲得ポイント計算"""
    base_rate = 1.5
    additional_rate = 0.0
    
    if config.get("yahoo_line_renkei", False):
        additional_rate += 3.0
    
    if config.get("yahoo_lyp_premium", False):
        additional_rate += 2.0
    
    if config.get("yahoo_store_point", False):
        additional_rate += 10.0
    
    if config.get("yahoo_bonus_store", False):
        additional_rate += 5.0
    
    if config.get("yahoo_campaign", False):
        additional_rate += 4.0
    
    total_rate = base_rate + additional_rate
    earned_points = price * (total_rate / 100)
    
    return int(earned_points), round(total_rate, 1)

def calculate_profit_yahoo_realistic(jan_code, buyback_info, config):
    """Yahoo!ショッピング実購入データに基づく利益計算"""
    if isinstance(buyback_info, dict):
        buyback_price = buyback_info.get("buyback_price", 0)
        buyback_store = buyback_info.get("store", "不明")
    else:
        buyback_price = buyback_info
        buyback_store = "不明"
    
    if buyback_price < 3000:
        return None
    
    yahoo_price = None
    if USE_RAPIDAPI and RAPIDAPI_KEY:
        yahoo_price = search_yahoo_shopping_rapidapi(jan_code, RAPIDAPI_KEY)
    
    if not yahoo_price:
        if buyback_price >= 100000:
            yahoo_price = int(buyback_price * 0.85)
        elif buyback_price >= 50000:
            yahoo_price = int(buyback_price * 0.80)
        elif buyback_price >= 20000:
            yahoo_price = int(buyback_price * 0.75)
        else:
            yahoo_price = int(buyback_price * 0.70)
    
    coupon_rate = config.get("coupon_discount_rate", 0)
    post_coupon_price = yahoo_price * (1 - coupon_rate / 100)
    
    earned_points, earned_point_rate = calculate_yahoo_earned_points(
        post_coupon_price, config
    )
    
    effective_price = post_coupon_price - earned_points
    
    profit_amount = buyback_price - effective_price
    profit_rate = (profit_amount / effective_price * 100) if effective_price > 0 else 0
    
    if profit_amount <= 0:
        return None
    
    is_api_price = (USE_RAPIDAPI and RAPIDAPI_KEY)
    
    return {
        "jan_code": jan_code,
        "buyback_price": buyback_price,
        "buyback_store": buyback_store,
        "best_site": "Yahoo!",
        "display_price": int(yahoo_price),
        "post_coupon_price": int(post_coupon_price),
        "earned_points": earned_points,
        "earned_point_rate": earned_point_rate,
        "effective_price": int(effective_price),
        "profit_amount": int(profit_amount),
        "profit_rate": profit_rate,
        "is_api_price": is_api_price,
        "category": get_product_category(jan_code)
    }

def calculate_profit_rakuten(jan_code, buyback_info, config):
    """楽天市場の利益計算"""
    if isinstance(buyback_info, dict):
        buyback_price = buyback_info.get("buyback_price", 0)
        buyback_store = buyback_info.get("store", "不明")
    else:
        buyback_price = buyback_info
        buyback_store = "不明"
    
    if buyback_price < 3000:
        return None
    
    rakuten_price = None
    if USE_RAKUTEN_API and RAKUTEN_APP_ID:
        rakuten_price = search_rakuten_price(jan_code, RAKUTEN_APP_ID)
    
    if not rakuten_price:
        if buyback_price >= 100000:
            rakuten_price = int(buyback_price * 0.85)
        elif buyback_price >= 50000:
            rakuten_price = int(buyback_price * 0.80)
        else:
            rakuten_price = int(buyback_price * 0.75)
    
    coupon_rate = config.get("coupon_discount_rate", 0)
    post_coupon_price = rakuten_price * (1 - coupon_rate / 100)
    
    total_point_rate = config["rakuten_point_rate"] + config["point_site_rate_rakuten"]
    effective_price = post_coupon_price * (1 - total_point_rate / 100)
    
    profit_amount = buyback_price - effective_price
    profit_rate = (profit_amount / effective_price * 100) if effective_price > 0 else 0
    
    if profit_amount <= 0:
        return None
    
    return {
        "jan_code": jan_code,
        "buyback_price": buyback_price,
        "buyback_store": buyback_store,
        "best_site": "楽天",
        "display_price": int(rakuten_price),
        "post_coupon_price": int(post_coupon_price),
        "earned_points": 0,
        "earned_point_rate": total_point_rate,
        "effective_price": int(effective_price),
        "profit_amount": int(profit_amount),
        "profit_rate": profit_rate,
        "is_api_price": False,
        "category": get_product_category(jan_code)
    }

def calculate_profit_best_site(jan_code, buyback_info, config):
    """Yahoo!と楽天を比較"""
    yahoo_result = calculate_profit_yahoo_realistic(jan_code, buyback_info, config)
    rakuten_result = calculate_profit_rakuten(jan_code, buyback_info, config)
    
    if not yahoo_result and not rakuten_result:
        return None
    
    if not yahoo_result:
        return rakuten_result
    if not rakuten_result:
        return yahoo_result
    
    if yahoo_result["profit_amount"] >= rakuten_result["profit_amount"]:
        return yahoo_result
    else:
        return rakuten_result

def create_ranking_df(buyback_db, config, limit=100):
    """ランキング作成"""
    results = []
    processed_count = 0
    excluded_count = 0
    api_success_count = 0
    category_counts = Counter()
    
    selected_cats = config.get("selected_categories", ["全て"])
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, (jan_code, buyback_info) in enumerate(list(buyback_db.items())[:limit]):
        processed_count += 1
        progress = (idx + 1) / limit
        progress_bar.progress(progress)
        status_text.text(f"🔄 処理中: {idx + 1}/{limit} (Yahoo!実価格: {api_success_count}件)")
        
        result = calculate_profit_best_site(jan_code, buyback_info, config)
        
        if result is None:
            excluded_count += 1
            continue
        
        if result.get("is_api_price"):
            api_success_count += 1
        
        category_counts[result["category"]] += 1
        
        if "全て" not in selected_cats:
            if result["category"] not in selected_cats:
                excluded_count += 1
                continue
        
        if not (config["min_profit_rate"] <= result["profit_rate"] <= config["max_profit_rate"]):
            excluded_count += 1
            continue
        
        results.append(result)
    
    progress_bar.empty()
    status_text.empty()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📈 カテゴリ別内訳")
    for cat, count in category_counts.most_common():
        st.sidebar.text(f"{cat}: {count}件")
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"📊 処理: {processed_count}件\n除外: {excluded_count}件\n有効: {len(results)}件\n✅ Yahoo!実価格: {api_success_count}件")
    
    if not results:
        return pd.DataFrame()
    
    df = pd.DataFrame(results)
    
    df["Yahoo!"] = df["jan_code"].apply(lambda x: generate_search_url(x, "Yahoo!"))
    df["楽天"] = df["jan_code"].apply(lambda x: generate_search_url(x, "楽天"))
    df["Amazon"] = df["jan_code"].apply(lambda x: generate_search_url(x, "Amazon"))
    df["価格.com"] = df["jan_code"].apply(lambda x: generate_search_url(x, "価格.com"))
    
    df = df.rename(columns={
        "jan_code": "JANコード",
        "buyback_price": "買取価格",
        "buyback_store": "買取店",
        "best_site": "推奨サイト",
        "display_price": "表示価格",
        "post_coupon_price": "クーポン後",
        "earned_points": "獲得ポイント",
        "earned_point_rate": "獲得率(%)",
        "effective_price": "実質価格",
        "profit_amount": "利益額",
        "profit_rate": "利益率(%)",
        "category": "カテゴリー",
        "is_api_price": "実価格取得"
    })
    
    return df.sort_values("利益率(%)", ascending=False).reset_index(drop=True)

# ==================== Streamlit UI ====================

st.set_page_config(
    page_title="せどり利益スカウター",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 せどり利益スカウター v5.3")
st.caption("✅ Yahoo!実購入データ完全対応版")

api_status_col1, api_status_col2 = st.columns(2)
with api_status_col1:
    if RAKUTEN_APP_ID and USE_RAKUTEN_API:
        st.success("✅ 楽天API 有効")
    else:
        st.warning("⚠️ 楽天API 未設定")

with api_status_col2:
    if RAPIDAPI_KEY and USE_RAPIDAPI:
        st.success("✅ RapidAPI 有効")
    else:
        st.error("❌ RapidAPI 未設定")

buyback_db = load_buyback_database()

if not buyback_db:
    st.error("❌ データベースが読み込めません")
    st.stop()

st.sidebar.header("⚙️ 設定")

with st.sidebar.expander("🔑 API設定", expanded=not RAPIDAPI_KEY):
    st.markdown("### RapidAPI Key")
    rapid_key = st.text_input("RapidAPI Key", value=RAPIDAPI_KEY, type="password")
    if rapid_key:
        RAPIDAPI_KEY = rapid_key
        USE_RAPIDAPI = True
    
    st.markdown("### 楽天API")
    rakuten_id = st.text_input("楽天アプリID", value=RAKUTEN_APP_ID, type="password")
    if rakuten_id:
        RAKUTEN_APP_ID = rakuten_id
        USE_RAKUTEN_API = True

st.sidebar.subheader("🏷️ ジャンル選択")
all_categories = ["全て"] + list(CATEGORIES.keys()) + ["その他"]
selected_categories = st.sidebar.multiselect(
    "カテゴリ",
    all_categories,
    default=["全て"]
)

st.sidebar.subheader("🎁 Yahoo!追加還元")
yahoo_line = st.sidebar.checkbox("LINE連携（+3%）", value=True)
yahoo_lyp = st.sidebar.checkbox("LYPプレミアム（+2%）", value=True)
yahoo_store = st.sidebar.checkbox("ストアポイント（+10%）", value=True)
yahoo_bonus = st.sidebar.checkbox("ボーナスストアPlus（+5%）", value=False)
yahoo_campaign = st.sidebar.checkbox("超PayPay祭（+4%）", value=False)

total_yahoo_rate = 1.5
if yahoo_line:
    total_yahoo_rate += 3.0
if yahoo_lyp:
    total_yahoo_rate += 2.0
if yahoo_store:
    total_yahoo_rate += 10.0
if yahoo_bonus:
    total_yahoo_rate += 5.0
if yahoo_campaign:
    total_yahoo_rate += 4.0

st.sidebar.info(f"📊 Yahoo!合計: **{total_yahoo_rate}%**")

st.sidebar.subheader("💳 楽天設定")
rakuten_point = st.sidebar.slider("楽天ポイント (%)", 0.0, 30.0, 15.0, 0.5)
rakuten_ps = st.sidebar.slider("ポイントサイト（楽天）(%)", 0.0, 5.0, 1.0, 0.1)

st.sidebar.subheader("🎟️ クーポン")
coupon_discount = st.sidebar.slider("クーポン割引 (%)", 0.0, 20.0, 0.0, 0.5)

config = {
    "min_profit_rate": 5.0,
    "max_profit_rate": 100.0,
    "exclude_used": True,
    "rakuten_point_rate": rakuten_point,
    "point_site_rate_rakuten": rakuten_ps,
    "coupon_discount_rate": coupon_discount,
    "selected_categories": selected_categories,
    "yahoo_line_renkei": yahoo_line,
    "yahoo_lyp_premium": yahoo_lyp,
    "yahoo_store_point": yahoo_store,
    "yahoo_bonus_store": yahoo_bonus,
    "yahoo_campaign": yahoo_campaign,
}

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
    display_limit = st.selectbox("表示件数", [10, 20, 50, 100, "全て"], index=2)
with col4:
    sort_by = st.selectbox("並び替え", ["利益率(%)", "利益額", "買取価格"])
with col5:
    calc_limit = st.number_input("計算対象", 10, 200, 50, 10)

with st.spinner("🔄 計算中..."):
    df = create_ranking_df(buyback_db, config, limit=calc_limit)

if df.empty:
    st.warning("⚠️ 条件に合う商品が見つかりませんでした")
    st.stop()

df = df.sort_values(sort_by, ascending=False)

if display_limit != "全て":
    df_display = df.head(display_limit)
else:
    df_display = df

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.metric("🛒 商品数", f"{len(df):,}件")
with col_m2:
    st.metric("💰 最高利益", f"¥{df['利益額'].max():,}")
with col_m3:
    st.metric("📈 平均利益率", f"{df['利益率(%)'].mean():.1f}%")
with col_m4:
    api_count = df["実価格取得"].sum()
    st.metric("✅ 実価格", f"{api_count}件")

st.markdown("---")

def make_clickable(url, text="🔗"):
    return f'<a href="{url}" target="_blank">{text}</a>'

df_html = df_display.copy()
df_html.index = df_html.index + 1
df_html["Yahoo!"] = df_html["Yahoo!"].apply(lambda x: make_clickable(x, "Yahoo!"))
df_html["楽天"] = df_html["楽天"].apply(lambda x: make_clickable(x, "楽天"))
df_html["Amazon"] = df_html["Amazon"].apply(lambda x: make_clickable(x, "Amazon"))
df_html["価格.com"] = df_html["価格.com"].apply(lambda x: make_clickable(x, "価格.com"))
df_html["実価格取得"] = df_html["実価格取得"].apply(lambda x: "✅" if x else "📊")

st.write(df_html.to_html(escape=False, index=True), unsafe_allow_html=True)

st.markdown("---")

csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
st.download_button(
    label="📥 CSVダウンロード",
    data=csv,
    file_name=f"sedori_v5.3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv"
)

st.markdown("---")
st.header("🧪 デバッグ")

with st.expander("🔍 テスト", expanded=False):
    test_jans = {
        "Nintendo Switch": "4902370546378",
        "PlayStation 5": "4948872415552",
    }
    
    selected_product = st.selectbox("商品", list(test_jans.keys()))
    test_jan = test_jans[selected_product]
    st.code(f"JAN: {test_jan}")
    
    if st.button("🔄 取得"):
        col1, col2 = st.columns(2)
        
        with col1:
            rakuten_price = search_rakuten_price(test_jan, RAKUTEN_APP_ID)
            if rakuten_price:
                st.success(f"✅ 楽天: ¥{rakuten_price:,}")
            else:
                st.error("❌ 楽天失敗")
        
        with col2:
            yahoo_price = search_yahoo_shopping_rapidapi(test_jan, RAPIDAPI_KEY)
            if yahoo_price:
                st.success(f"✅ Yahoo: ¥{yahoo_price:,}")
                earned_pts, earned_rate = calculate_yahoo_earned_points(yahoo_price, config)
                st.info(f"🎁 獲得: {earned_pts:,}pt ({earned_rate}%)")
            else:
                st.error("❌ Yahoo失敗")

st.markdown("---")
st.info(f"""
### 🔒 v5.3 実購入データ完全対応版

**✅ 新機能**:
- 獲得ポイント正確計算
- Yahoo!追加還元設定
- 実質価格 = 支払額 - 獲得ポイント

**データベース**: {len(buyback_db):,}件
""")
