#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
週次データベース更新スクリプト

使い方:
  python update_database.py <CSVファイルパス>

例:
  python update_database.py all_data_202604101818.csv
"""

import sys
import os
import pandas as pd
import json
from datetime import datetime
import re
from collections import Counter

def clean_jan_code(jan):
    """JANコードをクリーニング"""
    if pd.isna(jan) or jan == '':
        return None
    jan_str = str(jan).strip()
    jan_clean = re.sub(r'\D', '', jan_str)
    if len(jan_clean) in [8, 13]:
        return jan_clean
    return None

def extract_buyback_price_by_index(row):
    """各店舗の買取価格を抽出して最高値を返す"""
    stores = [
        ('アバウテック', 2, 3),
        ('じゃんぱら', 6, 7),
        ('ゲオ', 10, 11),
        ('ソフマップ', 14, 15),
        ('一丁目', 18, 19),
        ('ウィキ', 23, 24),
        ('家電行商', 27, 28),
        ('モバイルーン', 31, 32),
        ('ヤマダ', 35, 36),
        ('ホソヤ', 39, 40),
        ('ヤマミ', 42, 43)
    ]
    
    max_price = 0
    best_store = None
    latest_date = None
    
    for store_name, price_col, date_col in stores:
        if price_col < len(row) and pd.notna(row.iloc[price_col]):
            try:
                price = int(float(row.iloc[price_col]))
                if price > max_price:
                    max_price = price
                    best_store = store_name
                    if date_col < len(row) and pd.notna(row.iloc[date_col]):
                        latest_date = str(row.iloc[date_col])
            except (ValueError, TypeError):
                continue
    
    if max_price > 0:
        return {
            'buyback_price': max_price,
            'store': best_store,
            'updated_at': latest_date or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    return None

def convert_csv_to_json(csv_path, output_path='buyback_database.json'):
    """CSVをJSONに変換"""
    print("=" * 70)
    print("🔄 せどり利益スカウター - 週次データベース更新")
    print("=" * 70)
    print()
    
    # CSVファイル存在確認
    if not os.path.exists(csv_path):
        print(f"❌ エラー: ファイルが見つかりません: {csv_path}")
        return False
    
    print(f"📥 CSVファイル読み込み: {csv_path}")
    df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
    print(f"✅ 読み込み完了: {len(df):,} 行, {len(df.columns)} 列")
    print()
    
    # データベース構築
    buyback_db = {}
    valid_count = 0
    invalid_count = 0
    
    print("🔨 データベースを構築中...")
    for idx, row in df.iterrows():
        jan_code = clean_jan_code(row.iloc[0])
        if not jan_code:
            invalid_count += 1
            continue
        
        buyback_info = extract_buyback_price_by_index(row)
        if buyback_info and buyback_info['buyback_price'] > 0:
            if jan_code in buyback_db:
                if buyback_info['buyback_price'] > buyback_db[jan_code]['buyback_price']:
                    buyback_db[jan_code] = buyback_info
            else:
                buyback_db[jan_code] = buyback_info
            valid_count += 1
        
        if (idx + 1) % 2000 == 0:
            print(f"  処理中... {idx + 1:,}/{len(df):,} 行 (有効: {len(buyback_db):,})")
    
    print()
    
    # JSON保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(buyback_db, f, ensure_ascii=False, indent=2)
    
    # 統計
    prices = [info['buyback_price'] for info in buyback_db.values()]
    store_counts = Counter([info['store'] for info in buyback_db.values()])
    
    print("=" * 70)
    print("✅ データベース作成完了!")
    print("=" * 70)
    print()
    print("📊 統計情報:")
    print(f"   - 総レコード数: {len(df):,}")
    print(f"   - 有効なJANコード: {len(buyback_db):,}")
    print(f"   - 無効なJANコード: {invalid_count:,}")
    print(f"   - 買取価格あり: {valid_count:,}")
    print()
    print("💰 価格帯分析:")
    print(f"   - 最低価格: ¥{min(prices):,}")
    print(f"   - 最高価格: ¥{max(prices):,}")
    print(f"   - 平均価格: ¥{sum(prices)//len(prices):,}")
    print()
    print("🏪 店舗別商品数 (Top 5):")
    for store, count in store_counts.most_common(5):
        print(f"   - {store}: {count:,} 件 ({count/len(buyback_db)*100:.1f}%)")
    print()
    print(f"💾 保存先: {output_path}")
    print()
    print("=" * 70)
    print("🚀 次のステップ:")
    print("=" * 70)
    print()
    print("1️⃣  GitHub Releases にアップロード:")
    print("    https://github.com/[ユーザー名]/sedori-scouter-web/releases/new")
    print()
    print(f"2️⃣  Tag version: v{datetime.now().strftime('%Y.%m.%d')}")
    print(f"3️⃣  Release title: 買取価格データベース v{datetime.now().strftime('%Y.%m.%d')}")
    print()
    print("4️⃣  Description:")
    print(f"""
## 📊 データベース更新情報

- **更新日**: {datetime.now().strftime('%Y年%m月%d日')}
- **有効JANコード**: {len(buyback_db):,}件
- **ファイルサイズ**: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB
- **価格範囲**: ¥{min(prices):,} 〜 ¥{max(prices):,}
- **平均買取価格**: ¥{sum(prices)//len(prices):,}

### 店舗別商品数
""")
    for store, count in store_counts.most_common(10):
        print(f"- {store}: {count:,}件 ({count/len(buyback_db)*100:.1f}%)")
    
    print()
    print("=" * 70)
    
    return True

def main():
    if len(sys.argv) < 2:
        print("使い方: python update_database.py <CSVファイルパス>")
        print()
        print("例:")
        print("  python update_database.py all_data_202604101818.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    success = convert_csv_to_json(csv_path)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
