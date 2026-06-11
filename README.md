# Culture Lens 🖼🌸

写真を「見て」日本文化を解説する**マルチモーダルAIエージェント**。
IBM AI Innovator Hackathon 応募に向けた成果物。

## 目的（成功条件）
日本・アジア由来の物・場所・風景の写真をAIに見せると、画像を理解した上で
社内資料を検索し、その文化的背景・歴史・価値観を敬意を持って解説する。
旅行・美術館のお供のように、「カメラを向けた対象の物語」を引き出すツール。

## 技術構成（3つを統合）
| 技術 | 実装箇所 | 何のため |
|---|---|---|
| **マルチモーダル（vision）** | `lens.py` が画像をbase64でClaudeに直接渡す | 写真の内容を理解する |
| **ツール使用（エージェント）** | AIが `search_knowledge` を自分で呼ぶ agentic loop | 必要な情報を自律的に取りに行く |
| **RAG（検索拡張生成）** | `knowledge/` の資料を検索して回答 | 根拠に基づき、でっち上げを防ぐ |

姉妹プロジェクト [Culture Agent](../culture-agent/)（テキストRAG）に対し、
本プロジェクトは**入力が画像**である点が技術的な差別化。
同じ「日本文化を正しく世界に伝える」ミッションを、異なるAI技術で実装している。

---

## 作成物の概要（IBM AI Innovator Hackathon 提出用）

### 何を作ったか・目的/背景
日本文化を世界に正しく伝えるという同一ミッションを、テキストではなく「画像」起点で
実現するために制作。日本・アジア由来の物や場所の写真を見せると、AIが内容を理解し、
社内資料を検索して文化的背景を敬意を持って解説する。旅行・美術館のお供のように、
カメラを向けた対象の「物語」を引き出すツール。

### 担当した役割（実装箇所・担当工程）
個人開発。コンセプト設計、アーキテクチャ選定（マルチモーダル＋RAG＋エージェントの
統合方式の決定）、Culture Agent との差別化戦略（入力モダリティを画像に変える設計判断）、
画像エンコード・エージェントループ・RAG検索の実装までを一人で担当。実装は生成AIを
活用した開発手法（Claude Code）で進めた。

### 直面した課題と解決方法
- 課題1：姉妹プロジェクトとテーマが重複し「同じものの焼き直し」になりかねない。
  → 解決：入力モダリティを「テキスト」から「画像」へ変えることで、技術（vision）も
     使い方（対話型→かざす型）も差別化。一貫ミッション×異なるAI技術の構成にした。
- 課題2：画像形式（jpg/png/gif/webp）ごとにAPIへ渡すメディアタイプが異なる。
  → 解決：拡張子→メディアタイプの対応表を実装し、未対応形式は明示的にエラー化して
     安全に処理する設計にした。

### 技術情報（モデル・API・アーキテクチャ・実装方法）
- 言語：Python
- モデル：Claude Opus 4.8（環境変数で Fable 5 へ切替可能な設計）
- API：Anthropic Messages API（`anthropic` SDK）／画像はbase64で content に同梱
- アーキテクチャ：①画像理解（マルチモーダル/vision）②Tool Use による agentic loop
  ③RAG（knowledge/ の文化資料を検索して根拠化）の3技術を統合
- 実装：`lens.py`（エージェント本体）＋ `knowledge/`（文化資料）

## セットアップ

### 1. APIキー
```bash
export ANTHROPIC_API_KEY="sk-ant-自分のキー"
```
（取得方法は https://console.anthropic.com → API Keys）

### 2. ライブラリ（インストール済みなら不要）
```bash
pip3 install anthropic
```

### 3. 実行
```bash
cd ~/RIO/Workspace/Dev/culture-lens
python3 lens.py sample_images/あなたの写真.jpg
python3 lens.py sample_images/torii.jpg "これは何の建造物?"
```
対応形式: jpg / jpeg / png / gif / webp

#### モデル切替（Opus 4.8 ⇄ Fable 5）
```bash
CULTURE_LENS_MODEL=claude-fable-5 python3 lens.py sample_images/写真.jpg
```

## 動作イメージ
```
🤖 使用モデル: claude-opus-4-8
🖼  解析する画像: torii.jpg
🔎 AIが知識ベースを検索中:「torii shrine zen」
🌸 文化レンズ> この写真には朱色の鳥居が写っています。鳥居は神社の…
   （文化的背景を資料に基づいて解説）
```

## sample_images/ について
ここに自分で撮った写真（作務衣・神社・茶碗・庭など）を置いて試してください。
※個人が特定できる写真は避ける（GitHub公開時の配慮）。

## 次の拡張アイデア
- 複数枚の比較解説
- 位置情報や撮影日からの文脈補強
- Web UI化（写真ドラッグ＆ドロップ）
