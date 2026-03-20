"""
せどり利益スカウター - Streamlit版 v2.2
中古品フィルター + 販売店URL搭載
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# ========================
# デモ用買取価格データベース（100件）
# ========================
DEMO_BUYBACK_DB = {
    "4549292230116": {"price": 822000, "store": "家電芸人"},
    "4548736162075": {"price": 738000, "store": "ウイキャン"},
    "4549995434125": {"price": 532000, "store": "ブックオフ"},
    "4549292229141": {"price": 495000, "store": "家電芸人"},
    "4548736172357": {"price": 492000, "store": "ネットオフ"},
    "4960759909947": {"price": 453000, "store": "家電芸人"},
    "4549292246339": {"price": 445000, "store": "ウイキャン"},
    "4549980946060": {"price": 408000, "store": "ブックオフ"},
    "4960759916433": {"price": 387000, "store": "家電芸人"},
    "4549995667752": {"price": 373000, "store": "一丁目"},
    "4549292246391": {"price": 366000, "store": "家電芸人"},
    "4548736148888": {"price": 353000, "store": "ウイキャン"},
    "4549980894231": {"price": 338000, "store": "ブックオフ"},
    "4549980946053": {"price": 326000, "store": "家電芸人"},
    "4548736153967": {"price": 317000, "store": "ネットオフ"},
    "4548736153936": {"price": 317000, "store": "ネットオフ"},
    "4548736173774": {"price": 312000, "store": "家電芸人"},
    "4960759916181": {"price": 302000, "store": "ウイキャン"},
    "4960759919755": {"price": 286000, "store": "ブックオフ"},
    "4549980979037": {"price": 281000, "store": "家電芸人"},
    "4548736115538": {"price": 277000, "store": "一丁目"},
    "4549292081909": {"price": 273000, "store": "家電芸人"},
    "4549292247022": {"price": 269000, "store": "ウイキャン"},
    "4580546890908": {"price": 260000, "store": "ブックオフ"},
    "4549980994504": {"price": 258000, "store": "家電芸人"},
    "4960759913784": {"price": 255000, "store": "ネットオフ"},
    "4545350056599": {"price": 247000, "store": "家電芸人"},
    "4549980950463": {"price": 245000, "store": "ウイキャン"},
    "4548736154292": {"price": 242000, "store": "ブックオフ"},
    "4548736154353": {"price": 242000, "store": "家電芸人"},
    "4580620259812": {"price": 241000, "store": "一丁目"},
    "4547410559101": {"price": 233000, "store": "家電芸人"},
    "4549995656701": {"price": 233000, "store": "ウイキャン"},
    "4549995656763": {"price": 233000, "store": "ブックオフ"},
    "4960759917157": {"price": 232000, "store": "家電芸人"},
    "4549980973073": {"price": 229000, "store": "ネットオフ"},
    "4549995648348": {"price": 228000, "store": "家電芸人"},
    "4549995648324": {"price": 228000, "store": "ウイキャン"},
    "4545350056056": {"price": 227000, "store": "ブックオフ"},
    "4549980978993": {"price": 224000, "store": "家電芸人"},
    "4549995648331": {"price": 224000, "store": "一丁目"},
    "4573640684979": {"price": 217000, "store": "家電芸人"},
    "4548736146723": {"price": 216000, "store": "ウイキャン"},
    "4549292058239": {"price": 215000, "store": "ブックオフ"},
    "4960759910936": {"price": 214000, "store": "家電芸人"},
    "4549292058383": {"price": 214000, "store": "ネットオフ"},
    "4549980976548": {"price": 213000, "store": "家電芸人"},
    "4549980982570": {"price": 210000, "store": "ウイキャン"},
    "4573189165564": {"price": 205000, "store": "ブックオフ"},
    "4573189165540": {"price": 205000, "store": "家電芸人"},
    "4548736181458": {"price": 205000, "store": "一丁目"},
    "4548736181397": {"price": 205000, "store": "家電芸人"},
    "4960759917201": {"price": 203000, "store": "ウイキャン"},
    "4549995895698": {"price": 203000, "store": "ブックオフ"},
    "4549995895667": {"price": 203000, "store": "家電芸人"},
    "4549292072853": {"price": 201000, "store": "ネットオフ"},
    "4548736154506": {"price": 199000, "store": "家電芸人"},
    "4548736154469": {"price": 199000, "store": "ウイキャン"},
    "4548736170427": {"price": 196000, "store": "ブックオフ"},
    "4549980888209": {"price": 195000, "store": "家電芸人"},
    "4549980974131": {"price": 194000, "store": "一丁目"},
    "4548736182479": {"price": 194000, "store": "家電芸人"},
    "4573640685037": {"price": 192000, "store": "ウイキャン"},
    "4549980998953": {"price": 192000, "store": "ブックオフ"},
    "4549980928503": {"price": 192000, "store": "家電芸人"},
    "4549292093063": {"price": 192000, "store": "ネットオフ"},
    "4549292014938": {"price": 190000, "store": "家電芸人"},
    "4549980988244": {"price": 188000, "store": "ウイキャン"},
    "4549980970683": {"price": 187000, "store": "ブックオフ"},
    "4549292247008": {"price": 186000, "store": "家電芸人"},
    "4549292082296": {"price": 184000, "store": "一丁目"},
    "4548736179547": {"price": 180000, "store": "家電芸人"},
    "4960759909985": {"price": 180000, "store": "ウイキャン"},
    "4548736152014": {"price": 179000, "store": "ブックオフ"},
    "4549980973271": {"price": 179000, "store": "家電芸人"},
    "4549980983287": {"price": 178000, "store": "ネットオフ"},
    "4548736181809": {"price": 177000, "store": "家電芸人"},
    "4548736173477": {"price": 175000, "store": "ウイキャン"},
    "4549980934900": {"price": 174000, "store": "ブックオフ"},
    "4549980988367": {"price": 174000, "store": "家電芸人"},
    "4549980964583": {"price": 174000, "store": "一丁目"},
    "4549980983393": {"price": 174000, "store": "家電芸人"},
    "4549980997468": {"price": 172000, "store": "ウイキャン"},
    "4548736182882": {"price": 172000, "store": "ブックオフ"},
    "4548736116788": {"price": 171000, "store": "家電芸人"},
    "4548736164246": {"price": 171000, "store": "ネットオフ"},
    "4548736182806": {"price": 170000, "store": "家電芸人"},
    "4548736154315": {"price": 170000, "store": "ウイキャン"},
    "4549980990858": {"price": 170000, "store": "ブックオフ"},
    "4548736152038": {"price": 170000, "store": "家電芸人"},
    "4549980978672": {"price": 169000, "store": "一丁目"},
    "4549980972457": {"price": 169000, "store": "家電芸人"},
    "4548736163485": {"price": 168000, "store": "ウイキャン"},
    "4548736169254": {"price": 168000, "store": "ブックオフ"},
    "4549980986691": {"price": 168000, "store": "家電芸人"},
    "4548736174337": {"price": 168000, "store": "ネットオフ"},
    "4548736179844": {"price": 167000, "store": "家電芸人"},
    "4549980940383": {"price": 166000, "store": "ウイキャン"},
    "4548736182738": {"price": 166000, "store": "ブックオフ"},
}

# 中古品判定キーワード
USED_KEYWORDS = [
    "中古", "USED", "used", "Used", "リユース", "再生品",
    "整備済", "アウトレット", "訳あり", "傷あり", "箱なし"
]

# ========================
# 設定
# ========================
DEFAULT_CONFIG = {
    "min_profit_rate": 5.0,
    "exclude_used": True,
    "rakuten_point_rate": 15.0,
    "yahoo_point_rate": 20.0,
    "point_site_rate_rakuten": 1.0,
    "point_site_rate_yahoo": 1.2,
}

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
# 利益計算関数
# ========================
def calculate_profit(jan_code, display_price, ec_point_rate, point_site_rate):
    buyback_info = DEMO_BUYBACK_DB.get(jan_code, {"price": 0, "store": "不明"})
    buyback_price = buyback_info["price"]
    buyback_store = buyback_info["store"]
    
    total_rate = (ec_point_rate + point_site_rate) / 100
    effective_price = display_price * (1 - total_rate)
    
    profit_amount = buyback_price - effective_price
    profit_rate = (profit_amount / effective_price * 100) if effective_price > 0 else 0
    
    return {
        "buyback_price": buyback_price,
        "buyback_store": buyback_store,
        "effective_price": effective_price,
        "profit_amount": profit_amount,
        "profit_rate": profit_rate
    }

# ========================
# ランキング生成
# ========================
def create_ranking_df(config, exclude_used=True):
    display_price = 48000
    ec_rate = config["yahoo_point_rate"]
    ps_rate = config["point_site_rate_yahoo"]
    
    # デモ用商品名リスト
    demo_titles = [
        "Canon EOS R5 ボディ 新品未開封",
        "Sony α7 IV【中古・美品】",
        "Nikon Z9 ミラーレス一眼カメラ",
        "Panasonic LUMIX S5II 新品",
        "FUJIFILM X-T5【アウトレット】",
        "Olympus OM-1 新品未使用",
    ]
    
    ranking_data = []
    for idx, (jan_code, info) in enumerate(DEMO_BUYBACK_DB.items()):
        demo_title = demo_titles[idx % len(demo_titles)]
        
        # 中古品フィルター
        if exclude_used and is_used_item(demo_title):
            continue
        
        result = calculate_profit(jan_code, display_price, ec_rate, ps_rate)
        
        # URL生成
        yahoo_url = generate_search_url(jan_code, "Yahoo!")
        rakuten_url = generate_search_url(jan_code, "楽天")
        amazon_url = generate_search_url(jan_code, "Amazon")
        
        ranking_data.append({
            "JAN": jan_code,
            "商品名": demo_title,
            "買取価格": result["buyback_price"],
            "買取店": result["buyback_store"],
            "表示価格": display_price,
            "実質価格": int(result["effective_price"]),
            "利益額": int(result["profit_amount"]),
            "利益率(%)": round(result["profit_rate"], 2),
            "Yahoo!": yahoo_url,
            "楽天": rakuten_url,
            "Amazon": amazon_url,
        })
    
    df = pd.DataFrame(ranking_data)
    df = df.sort_values("利益率(%)", ascending=False).reset_index(drop=True)
    df.index = df.index + 1
    return df

def format_profit_rate(rate):
    if rate >= 1000:
        return f"🔥🔥🔥 {rate:.1f}%"
    elif rate >= 500:
        return f"🔥🔥 {rate:.1f}%"
    elif rate >= 100:
        return f"🔥 {rate:.1f}%"
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
st.caption("v2.2 販売店URL搭載版（100商品データ）| 最終更新: 2026-03-20")

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
st.header("📊 Yahoo!ショッピング 利益率ランキング")

filter_status = "🔒 新品のみ" if exclude_used else "📦 新品 + 中古"
st.info(f"**現在のフィルター設定**: {filter_status}")

# フィルター
col1, col2 = st.columns([1, 1])
with col1:
    min_rate_filter = st.selectbox(
        "最低利益率",
        [5, 10, 20, 50, 100, 200, 500, 1000],
        index=0
    )
with col2:
    display_limit = st.selectbox(
        "表示件数",
        [10, 20, 50, 100],
        index=3
    )

# ランキング生成
df = create_ranking_df(config, exclude_used=exclude_used)
df_filtered = df[df["利益率(%)"] >= min_rate_filter].head(display_limit)

# 統計情報
col_stat1, col_stat2, col_stat3 = st.columns(3)
with col_stat1:
    st.metric("対象商品数", f"{len(df):,}件")
with col_stat2:
    st.metric("最高利益額", f"¥{df['利益額'].max():,}")
with col_stat3:
    st.metric("平均利益率", f"{df['利益率(%)'].mean():.2f}%")

# テーブル表示用にURLをリンク化
df_display = df_filtered.copy()
df_display["Yahoo!"] = df_display["Yahoo!"].apply(lambda x: f'<a href="{x}" target="_blank">🔗 検索</a>')
df_display["楽天"] = df_display["楽天"].apply(lambda x: f'<a href="{x}" target="_blank">🔗 検索</a>')
df_display["Amazon"] = df_display["Amazon"].apply(lambda x: f'<a href="{x}" target="_blank">🔗 検索</a>')

# HTML形式で表示
st.markdown(
    df_display.to_html(escape=False, index=True),
    unsafe_allow_html=True
)

# ダウンロードボタン
csv = df_filtered.to_csv(index=True, encoding="utf-8-sig").encode("utf-8-sig")
st.download_button(
    label="📥 CSVダウンロード",
    data=csv,
    file_name=f"yahoo_ranking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv"
)

# フッター
st.markdown("---")
st.info("""
⚠️ **注意事項**  
- これはデモ版です（100件のサンプルデータ）
- 🔗 各ECサイトの「検索」リンクをクリックでJAN検索ページが開きます
- 中古品フィルターは商品名のキーワード判定で動作します
- 実際の価格・在庫は変動します
- 仕入れ前に必ず最新情報を確認してください
""")
