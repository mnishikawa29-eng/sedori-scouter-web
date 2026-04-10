# GitHub Releases へのデータベースアップロード手順

## 📋 概要
週1回の買取価格データベース更新を GitHub Releases で管理します。

---

## 🚀 初回アップロード手順

### 1. GitHub リポジトリページを開く
https://github.com/[ユーザー名]/sedori-scouter-web

### 2. Releases セクションへ移動
- 右サイドバーの **"Releases"** をクリック
- または直接アクセス: `https://github.com/[ユーザー名]/sedori-scouter-web/releases`

### 3. 新しいリリースを作成
1. **"Create a new release"** (または "Draft a new release") をクリック
2. 以下の情報を入力:

#### Tag version
```
v2026.04.10
```
**命名規則**: `vYYYY.MM.DD` (年.月.日)

#### Release title
```
買取価格データベース v2026.04.10
```

#### Description
```markdown
## 📊 データベース更新情報

- **更新日**: 2026年4月10日
- **有効JANコード**: 21,491件
- **ファイルサイズ**: 2.5 MB
- **価格範囲**: ¥150 〜 ¥4,205,000
- **平均買取価格**: ¥43,868

### 店舗別商品数
- 家電行商: 6,333件 (29.5%)
- ソフマップ: 5,228件 (24.3%)
- ウィキ: 3,877件 (18.0%)
- ゲオ: 3,350件 (15.6%)
- その他: 2,703件 (12.6%)

### 主な変更点
- 週次データ更新
- 新規商品追加
- 価格情報の最新化
```

### 4. ファイルをアップロード
- **"Attach binaries by dropping them here or selecting them."** の部分に
- `/home/user/buyback_database.json` をドラッグ&ドロップ
- または **"choose them"** をクリックしてファイル選択

### 5. 公開
- **"Publish release"** をクリック

---

## 🔗 生成される URL

リリース公開後、以下の恒久URLが生成されます:

```
https://github.com/[ユーザー名]/sedori-scouter-web/releases/download/v2026.04.10/buyback_database.json
```

### URL構造
```
https://github.com/
  [ユーザー名]/
  [リポジトリ名]/
  releases/download/
  [タグ名]/
  [ファイル名]
```

---

## 🔄 週次更新手順

毎週同じ手順を繰り返します:

### 手順
1. 新しい CSV を受け取る
2. `buyback_database.json` を生成 (Python スクリプト)
3. GitHub Releases で新しいリリースを作成
   - Tag: `v2026.04.17` (次週の日付)
   - Title: `買取価格データベース v2026.04.17`
   - ファイル: 新しい `buyback_database.json`
4. **"Publish release"** をクリック

### アプリ側の対応
- Streamlit アプリは常に **"latest" リリース** から自動ダウンロード
- コード変更不要
- 自動的に新しいデータが反映されます

---

## 🎯 メリット

✅ **恒久的なURL**: リンク切れなし  
✅ **バージョン管理**: 過去データにもアクセス可能  
✅ **無料**: GitHub Releases は無制限  
✅ **CDN配信**: ダウンロードが高速  
✅ **履歴管理**: いつ、どのデータを公開したか記録  

---

## 🛠️ トラブルシューティング

### Q: ファイルサイズ制限は?
**A**: GitHub Releases は 1ファイル 2GB まで対応。現在の 2.5MB は問題なし。

### Q: 古いリリースを削除できる?
**A**: 可能。Releases ページから古いバージョンを個別に削除できます。

### Q: アプリが古いデータを表示する
**A**: Streamlit のキャッシュをクリア。サイドバーに「データ再読み込み」ボタンを追加予定。

---

## 📌 次回更新時のチェックリスト

- [ ] 新しい CSV を受け取った
- [ ] `buyback_database.json` を生成した
- [ ] データ件数・価格範囲を確認した
- [ ] GitHub Releases で新しいタグを作成した
- [ ] ファイルをアップロードした
- [ ] リリースを公開した
- [ ] Streamlit アプリで動作確認した

---

**作成日**: 2026-04-10  
**次回更新予定**: 2026-04-17 (木)
