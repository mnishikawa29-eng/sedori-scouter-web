"""
せどり利益スカウター - Streamlit版 v2.4
多様なジャンルの現実的な利益商品リスト搭載
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# ========================
# デモ用買取価格データベース（100件）
# 🆕 現実的な利益率（5%〜100%程度）の商品を中心に
# ========================
DEMO_BUYBACK_DB = {
    # 家電製品（利益率 10%〜30%）
    "4974019973593": {"price": 52000, "store": "家電芸人", "name": "ダイソン V12 Detect Slim コードレスクリーナー"},
    "4548736123454": {"price": 48000, "store": "ジョーシン", "name": "シャープ 加湿空気清浄機 KI-PX70"},
    "4902370546378": {"price": 31000, "store": "エディオン", "name": "Nintendo Switch 有機ELモデル ホワイト"},
    "4549980594049": {"price": 42000, "store": "ビックカメラ", "name": "ソニー ワイヤレスヘッドホン WH-1000XM5"},
    "4960759908841": {"price": 55000, "store": "家電芸人", "name": "パナソニック 食洗機 NP-TZ300"},
    
    # 美容家電（利益率 15%〜35%）
    "4580564694766": {"price": 38000, "store": "ウイキャン", "name": "ヤーマン メディリフト アイ EPE-10"},
    "4549660358473": {"price": 25000, "store": "ブックオフ", "name": "パナソニック ナノケア ドライヤー EH-NA0J"},
    "4589785690051": {"price": 33000, "store": "ネットオフ", "name": "リファ ビューテック ドライヤー プロ"},
    
    # ゲーム機本体・周辺機器（利益率 8%〜25%）
    "4948872016148": {"price": 28000, "store": "駿河屋", "name": "PlayStation 5 デジタル・エディション"},
    "4902370548495": {"price": 6500, "store": "一丁目", "name": "Nintendo Switch Proコントローラー"},
    "0889842976991": {"price": 52000, "store": "マップカメラ", "name": "Xbox Series X 本体"},
    
    # ゲームソフト（利益率 10%〜40%）
    "4902370549041": {"price": 5200, "store": "駿河屋", "name": "ゼルダの伝説 ティアーズ オブ ザ キングダム"},
    "4948872310734": {"price": 4800, "store": "ブックオフ", "name": "ファイナルファンタジー XVI"},
    "4940261523220": {"price": 5500, "store": "駿河屋", "name": "スプラトゥーン3"},
    
    # 調理家電（利益率 12%〜28%）
    "4589919823581": {"price": 13500, "store": "家電芸人", "name": "ティファール クックフォーミー 3L"},
    "4562359411175": {"price": 18000, "store": "エディオン", "name": "シャープ ヘルシオ ホットクック 1.6L"},
    "4967576492126": {"price": 9500, "store": "ジョーシン", "name": "象印 炊飯器 極め炊き NW-VD10"},
    
    # スマートウォッチ・ウェアラブル（利益率 10%〜30%）
    "0194253905257": {"price": 38000, "store": "ビックカメラ", "name": "Apple Watch Series 9 GPS 45mm"},
    "8806094927955": {"price": 28000, "store": "エディオン", "name": "Samsung Galaxy Watch6 Classic"},
    "6942351711323": {"price": 12000, "store": "家電芸人", "name": "Xiaomi Smart Band 8 Pro"},
    
    # イヤホン・オーディオ（利益率 15%〜35%）
    "0194252721049": {"price": 28000, "store": "ビックカメラ", "name": "Apple AirPods Pro 第2世代"},
    "4549980633687": {"price": 22000, "store": "ジョーシン", "name": "ソニー WF-1000XM5 ワイヤレスイヤホン"},
    "8809755746023": {"price": 18000, "store": "エディオン", "name": "Samsung Galaxy Buds2 Pro"},
    
    # PC周辺機器（利益率 10%〜25%）
    "4988617432543": {"price": 8500, "store": "家電芸人", "name": "ロジクール MXマスター 3S ワイヤレスマウス"},
    "0097855163370": {"price": 12000, "store": "ビックカメラ", "name": "Logicool G PRO X SUPERLIGHT ゲーミングマウス"},
    "4537694297431": {"price": 15000, "store": "エディオン", "name": "Keychron K8 Pro メカニカルキーボード"},
    
    # タブレット・電子書籍リーダー（利益率 8%〜20%）
    "0194253092391": {"price": 52000, "store": "ビックカメラ", "name": "iPad 第10世代 Wi-Fi 256GB"},
    "0840268953744": {"price": 15000, "store": "家電芸人", "name": "Amazon Kindle Paperwhite シグニチャー"},
    
    # カメラ関連（利益率 10%〜50%）※一部高利益商品を残す
    "4549292230116": {"price": 85000, "store": "マップカメラ", "name": "Canon EOS R6 Mark II ボディ"},
    "4548736162075": {"price": 72000, "store": "マップカメラ", "name": "Sony α7 IV ボディ"},
    "4960759911247": {"price": 120000, "store": "マップカメラ", "name": "Nikon Z9 ボディ"},
    
    # 生活家電（利益率 12%〜30%）
    "4974019206080": {"price": 42000, "store": "家電芸人", "name": "ダイソン Pure Hot+Cool HP07"},
    "4549980644829": {"price": 18000, "store": "エディオン", "name": "ソニー グラスサウンドスピーカー LSPX-S3"},
    "4580652110075": {"price": 32000, "store": "ジョーシン", "name": "バルミューダ The Toaster Pro"},
    
    # 健康器具（利益率 15%〜35%）
    "4975479419126": {"price": 48000, "store": "家電芸人", "name": "タニタ 体組成計 インナースキャンデュアル RD-917L"},
    "4975479419751": {"price": 15000, "store": "ビックカメラ", "name": "オムロン 体重体組成計 HBF-702T"},
    
    # おもちゃ・ホビー（利益率 20%〜50%）
    "4549660868880": {"price": 8500, "store": "駿河屋", "name": "プラレール トーマス 大冒険セット"},
    "4904810192534": {"price": 12000, "store": "一丁目", "name": "LEGO テクニック ランボルギーニ 42115"},
    "4902425719443": {"price": 15000, "store": "駿河屋", "name": "タカラトミー トミカ プレミアム 25周年セット"},
    
    # 日用品・消耗品（利益率 5%〜15%）
    "4902430916230": {"price": 2800, "store": "家電芸人", "name": "ブラウン 替刃 シリーズ9 92S"},
    "4987176068729": {"price": 3500, "store": "ウイキャン", "name": "パナソニック シェーバー替刃 ES9036"},
}

# 中古品判定キーワード
USED_KEYWORDS = [
    "中古", "USED", "used", "Used", "リユース", "再生品",
    "整備済", "アウトレット", "訳あり", "傷あり", "箱なし", "展示品"
]

# ========================
# 設定
# ========================
DEFAULT_CONFIG = {
    "min_profit_rate": 5.0,
    "max_profit_rate": 100.0,  # デフォルトを500→100に変更（現実的な範囲）
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
    buyback_info = DEMO_BUYBACK_DB.get(jan_code, {"price": 0, "store": "不明", "name": "不明"})
    buyback_price = buyback_info["price"]
    buyback_store = buyback_info["store"]
    product_name = buyback_info.get("name", "不明")
    
    total_rate = (ec_point_rate + point_site_rate) / 100
    effective_price = display_price * (1 - total_rate)
    
    profit_amount = buyback_price - effective_price
    profit_rate = (profit_amount / effective_price * 100) if effective_price > 0 else 0
    
    return {
        "product_name": product_name,
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
    # 🆕 価格を商品ごとに変動させる（より現実的に）
    ranking_data = []
    
    for jan_code, info in DEMO_BUYBACK_DB.items():
        product_name = info.get("name", "不明")
        buyback_price = info["price"]
        
        # 商品カテゴリーに応じて表示価格を設定
        if buyback_price >= 80000:
            display_price = int(buyback_price * 0.6)  # 高額商品は利益率低め
        elif buyback_price >= 30000:
            display_price = int(buyback_price * 0.7)  # 中額商品
        else:
            display_price = int(buyback_price * 0.8)  # 低額商品は利益率高め
        
        # 中古品フィルター（デモなので商品名でチェック）
        if exclude_used and is_used_item(product_name):
            continue
        
        # Yahoo!ショッピングでの利益計算
        ec_rate = config["yahoo_point_rate"]
        ps_rate = config["point_site_rate_yahoo"]
        
        result = calculate_profit(jan_code, display_price, ec_rate, ps_rate)
        
        # URL生成
        yahoo_url = generate_search_url(jan_code, "Yahoo!")
        rakuten_url = generate_search_url(jan_code, "楽天")
        amazon_url = generate_search_url(jan_code, "Amazon")
        
        ranking_data.append({
            "JAN": jan_code,
            "商品名": result["product_name"],
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
st.caption("v2.4 多様なジャンル対応版（45商品データ）| 最終更新: 2026-03-20")

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
        value=100.0,  # デフォルトを100%に変更
        step=10.0,
        help="この利益率以下の商品のみ表示します（高すぎる利益率は価格ミスの可能性）"
    )

# 利益率範囲の表示
if min_profit_rate > max_profit_rate:
    st.error("⚠️ 最低利益率が最高利益率を超えています。設定を見直してください。")
else:
    st.success(f"✅ 利益率範囲: **{min_profit_rate}% 〜 {max_profit_rate}%**")

st.markdown("---")

# その他フィルター
col1, col2 = st.columns([1, 1])

with col1:
    display_limit = st.selectbox(
        "表示件数",
        [10, 20, 50, 100],
        index=1  # デフォルト20件
    )

with col2:
    sort_by = st.selectbox(
        "並び替え",
        ["利益率順", "利益額順"],
        index=0
    )

# ランキング生成
df = create_ranking_df(config, exclude_used=exclude_used)

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

# テーブル表示用にURLをリンク化
if len(df_filtered) > 0:
    df_display = df_filtered.copy()
    df_display["Yahoo!"] = df_display["Yahoo!"].apply(lambda x: f'<a href="{x}" target="_blank">🔗 検索</a>')
    df_display["楽天"] = df_display["楽天"].apply(lambda x: f'<a href="{x}" target="_blank">🔗 検索</a>')
    df_display["Amazon"] = df_display["Amazon"].apply(lambda x: f'<a href="{x}" target="_blank">🔗 検索</a>')
    
    # 価格フォーマット
    df_display["買取価格"] = df_display["買取価格"].apply(lambda x: f"¥{x:,}")
    df_display["表示価格"] = df_display["表示価格"].apply(lambda x: f"¥{x:,}")
    df_display["実質価格"] = df_display["実質価格"].apply(lambda x: f"¥{x:,}")
    df_display["利益額"] = df_display["利益額"].apply(lambda x: f"¥{x:,}")
    df_display["利益率(%)"] = df_display["利益率(%)"].apply(format_profit_rate)
    
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
else:
    st.warning("⚠️ 指定された利益率範囲に該当する商品が見つかりませんでした。")

# フッター
st.markdown("---")
st.info("""
⚠️ **注意事項**  
- これはデモ版です（45商品のサンプルデータ）
- 🔗 各ECサイトの「検索」リンクをクリックでJAN検索ページが開きます
- 🎯 利益率範囲のデフォルトは5%〜100%（現実的な範囲）
- 家電、ゲーム、美容、PC周辺機器など多様なジャンルを収録
- 実際の価格・在庫は変動します
- 仕入れ前に必ず最新情報を確認してください
""")
