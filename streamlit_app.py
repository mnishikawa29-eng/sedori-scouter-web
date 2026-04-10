import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime
import time

# ==================== 設定 ====================
# 最終更新: 2026-04-10 (21,491件のデータベース)
GITHUB_REPO = "mnishikawa29-eng/sedori-scouter-web"
DATABASE_VERSION = "v2026.04.10"
DATABASE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest/download/buyback_database.json"

DEFAULT_CONFIG = {
    'min_profit_rate': 5.0,
    'max_profit_rate': 100.0,
    'rakuten_point_rate': 15.0,
    'yahoo_point_rate': 1.5,
    'yahoo_additional_line': 0.0,
    'yahoo_additional_lyp': 0.0,
    'yahoo_additional_store': 0.0,
    'yahoo_additional_bonus': 0.0,
    'yahoo_additional_campaign': 0.0,
    'point_site_rate_rakuten': 1.0,
    'point_site_rate_yahoo': 1.2,
    'coupon_discount_rate': 0.0,
    'exclude_used': True
}

# ==================== データベース読み込み ====================
@st.cache_data(ttl=60, show_spinner=False)
def load_buyback_database(version=DATABASE_VERSION):
    """GitHub Releases から買取価格データベースをダウンロード"""
    try:
        with st.spinner(f"📥 データベースを読み込んでいます... (バージョン: {version})"):
            response = requests.get(DATABASE_URL, timeout=30)
            response.raise_for_status()
            buyback_db = response.json()
            
            st.success(f"✅ データベース読み込み完了: {len(buyback_db):,} 件")
            
            prices = [info['buyback_price'] for info in buyback_db.values()]
            if prices:
                st.info(f"💰 価格範囲: ¥{min(prices):,} 〜 ¥{max(prices):,} | 📊 平均: ¥{sum(prices)//len(prices):,}")
            
            st.caption(f"📌 データベースバージョン: {version}")
            
            return buyback_db
    
    except requests.exceptions.RequestException as e:
        st.error(f"❌ データベース読み込みエラー: {str(e)}")
        return {}
    except json.JSONDecodeError as e:
        st.error(f"❌ JSONパースエラー: {str(e)}")
        return {}

# ==================== メイン ====================
st.set_page_config(page_title="せどり利益スカウター v5.3", page_icon="🔍", layout="wide")

st.title("🔍 せどり利益スカウター v5.3")

# データベース読み込み
buyback_db = load_buyback_database()

if buyback_db:
    st.write(f"**データ件数**: {len(buyback_db):,} 件")
else:
    st.warning("⚠️ データベースが空です。GitHub Releasesを確認してください。")

st.info("🚧 利益計算機能は開発中です。現在はデータベースの読み込みテストを行っています。")
