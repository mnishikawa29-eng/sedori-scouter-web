"""
せどり利益スカウター - 共通データベースモジュール

このモジュールは sedori-scouter-web と receipt-to-mf の両方で使用できます。
GitHub Releases から最新の買取価格データベースを取得します。
"""

import json
import requests
from typing import Dict, Optional
import streamlit as st

# GitHub リポジトリ設定
GITHUB_REPO = "m-nishikawa-gh/sedori-scouter-web"  # ⚠️ 実際のユーザー名に変更
DATABASE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest/download/buyback_database.json"

class SedoriDatabase:
    """せどり買取価格データベース"""
    
    def __init__(self, repo: str = GITHUB_REPO):
        """
        初期化
        
        Args:
            repo: GitHubリポジトリ (format: "username/repository")
        """
        self.repo = repo
        self.url = f"https://github.com/{repo}/releases/latest/download/buyback_database.json"
        self._data = None
    
    @st.cache_data(ttl=3600)  # 1時間キャッシュ
    def load(_self) -> Dict:
        """
        データベースをロード
        
        Returns:
            Dict: {JAN: {buyback_price, store, updated_at}}
        """
        try:
            response = requests.get(_self.url, timeout=30)
            response.raise_for_status()
            _self._data = response.json()
            return _self._data
        
        except requests.exceptions.RequestException as e:
            print(f"❌ データベースの読み込みに失敗: {str(e)}")
            return {}
        
        except json.JSONDecodeError as e:
            print(f"❌ JSONパースエラー: {str(e)}")
            return {}
    
    def get_buyback_price(self, jan_code: str) -> Optional[Dict]:
        """
        JANコードから買取価格情報を取得
        
        Args:
            jan_code: JANコード (13桁または8桁)
        
        Returns:
            Dict: {buyback_price, store, updated_at} または None
        """
        if self._data is None:
            self._data = self.load()
        
        return self._data.get(str(jan_code))
    
    def search_by_price_range(self, min_price: int, max_price: int) -> Dict:
        """
        価格帯で検索
        
        Args:
            min_price: 最低買取価格
            max_price: 最高買取価格
        
        Returns:
            Dict: フィルタされたデータベース
        """
        if self._data is None:
            self._data = self.load()
        
        return {
            jan: info for jan, info in self._data.items()
            if min_price <= info['buyback_price'] <= max_price
        }
    
    def get_statistics(self) -> Dict:
        """
        データベース統計を取得
        
        Returns:
            Dict: {count, min_price, max_price, avg_price, stores}
        """
        if self._data is None:
            self._data = self.load()
        
        if not self._data:
            return {}
        
        prices = [info['buyback_price'] for info in self._data.values()]
        stores = {}
        for info in self._data.values():
            store = info['store']
            stores[store] = stores.get(store, 0) + 1
        
        return {
            'count': len(self._data),
            'min_price': min(prices),
            'max_price': max(prices),
            'avg_price': sum(prices) // len(prices),
            'stores': stores
        }


# ==================== 使用例 ====================

def example_usage_streamlit():
    """Streamlit アプリでの使用例"""
    import streamlit as st
    
    st.title("せどり利益スカウター")
    
    # データベース初期化
    db = SedoriDatabase()
    data = db.load()
    
    st.write(f"✅ データベース読み込み完了: {len(data):,} 件")
    
    # 統計表示
    stats = db.get_statistics()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("商品数", f"{stats['count']:,}")
    with col2:
        st.metric("最高価格", f"¥{stats['max_price']:,}")
    with col3:
        st.metric("平均価格", f"¥{stats['avg_price']:,}")
    
    # JANコード検索
    jan_input = st.text_input("JANコードを入力")
    if jan_input:
        info = db.get_buyback_price(jan_input)
        if info:
            st.success(f"""
            **買取価格**: ¥{info['buyback_price']:,}  
            **店舗**: {info['store']}  
            **更新日時**: {info['updated_at']}
            """)
        else:
            st.warning("該当する商品が見つかりませんでした")


def example_usage_python():
    """通常のPythonスクリプトでの使用例"""
    
    # データベース初期化
    db = SedoriDatabase()
    data = db.load()
    
    print(f"✅ {len(data):,} 件のデータを読み込みました")
    
    # JANコードで検索
    jan = "4902370546378"  # 例: Nintendo Switch Pro コントローラー
    info = db.get_buyback_price(jan)
    
    if info:
        print(f"買取価格: ¥{info['buyback_price']:,}")
        print(f"店舗: {info['store']}")
    else:
        print("商品が見つかりませんでした")
    
    # 価格帯で検索
    high_value_items = db.search_by_price_range(100000, 1000000)
    print(f"\n高額商品 (¥100,000〜): {len(high_value_items)} 件")
    
    # 統計表示
    stats = db.get_statistics()
    print(f"\n統計:")
    print(f"  - 総商品数: {stats['count']:,}")
    print(f"  - 価格範囲: ¥{stats['min_price']:,} 〜 ¥{stats['max_price']:,}")
    print(f"  - 平均価格: ¥{stats['avg_price']:,}")


if __name__ == "__main__":
    # コマンドライン実行時
    example_usage_python()
