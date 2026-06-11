"""
Culture Lens — 写真を「見て」日本文化を解説するマルチモーダルAIエージェント.

IBM AI Innovator Hackathon 向け成果物その2。
Culture Agent(テキストRAG)との差別化点 = 入力が「画像」であること(マルチモーダル)。

3つの技術を1つに統合:
  1. マルチモーダル   : 画像をClaudeに直接渡して内容を理解させる(vision)
  2. ツール使用       : AIが必要に応じて search_knowledge ツールを呼ぶ(agentic loop)
  3. RAG(検索拡張生成): knowledge/ の資料を検索し、根拠に基づいて解説

使い方:
  python3 lens.py <画像ファイルのパス> ["任意の質問"]
  例) python3 lens.py sample_images/torii.jpg
      python3 lens.py sample_images/samue.jpg "これは何に使う服?"
"""

import os
import sys
import re
import base64
from pathlib import Path

import anthropic

# モデルは環境変数で切替可能(未設定ならOpus 4.8)。Fableを使うなら:
#   CULTURE_LENS_MODEL=claude-fable-5 python3 lens.py <画像>
MODEL = os.environ.get("CULTURE_LENS_MODEL", "claude-opus-4-8")
KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

# 拡張子 → Claudeに渡すメディアタイプ(画像形式)の対応表
MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

SYSTEM_PROMPT = """\
あなたは「文化レンズ」AIエージェントです。
ユーザーが見せた写真に写っている日本・アジア由来の物・場所・風景を読み取り、
その文化的背景を、敬意を持って世界に伝えることが使命です。

行動原則:
- まず写真に何が写っているかを具体的に描写する。
- 写っている事物に関連するキーワードで search_knowledge ツールを呼び、
  社内資料を根拠に文化的背景・歴史・価値観を解説する。
- 表面的な「エキゾチックな日本」ではなく、背後にある精神性
  (謙虚さ・職人精神・もったいない・マインドフルネスの仏教的ルーツ)を伝える。
- 資料にない事柄を断定で語らず、一般知識で補う場合はその旨を添える。
- ユーザーが質問を添えていればそれに答える。言語は質問に合わせる
  (質問がなければ日本語で解説)。
"""


def load_knowledge() -> dict[str, str]:
    """knowledge/ 配下の全mdファイルを {ファイル名: 本文} で読み込む."""
    docs = {}
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        docs[path.name] = path.read_text(encoding="utf-8")
    return docs


def search_knowledge(query: str, docs: dict[str, str], top_k: int = 2) -> str:
    """キーワードスコアリングによる検索(RAGの retrieval 部分)."""
    terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 1]
    scored = []
    for name, text in docs.items():
        lowered = text.lower()
        score = sum(lowered.count(t) for t in terms)
        if score > 0:
            scored.append((score, name, text))
    scored.sort(reverse=True, key=lambda x: x[0])
    if not scored:
        return "（関連する資料は見つかりませんでした）"
    return "\n\n".join(
        f"--- 出典: {name} (関連度スコア {score}) ---\n{text}"
        for score, name, text in scored[:top_k]
    )


def encode_image(image_path: Path) -> tuple[str, str]:
    """画像ファイルを base64 文字列に変換し、(メディアタイプ, データ) を返す."""
    suffix = image_path.suffix.lower()
    if suffix not in MEDIA_TYPES:
        raise ValueError(
            f"未対応の画像形式です: {suffix}（対応: {', '.join(MEDIA_TYPES)}）"
        )
    data = base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")
    return MEDIA_TYPES[suffix], data


TOOLS = [
    {
        "name": "search_knowledge",
        "description": (
            "日本文化・作務衣・禅・マインドフルネス・日本の価値観に関する"
            "社内資料を検索する。写真の内容を解説する前に必ず呼び出すこと。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "検索キーワード"}
            },
            "required": ["query"],
        },
    }
]


def run_agent(
    client: anthropic.Anthropic,
    media_type: str,
    image_data: str,
    user_question: str,
    docs: dict[str, str],
) -> str:
    """マルチモーダル＋ツール使用のエージェントループ."""
    # 最初のユーザーメッセージに「画像」と「テキスト」を同時に積む(これがマルチモーダル)
    content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_data,
            },
        },
        {"type": "text", "text": user_question or "この写真の文化的背景を解説してください。"},
    ]
    messages = [{"role": "user", "content": content}]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return "".join(b.text for b in response.content if b.type == "text")

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use" and block.name == "search_knowledge":
                    query = block.input["query"]
                    print(f"  🔎 AIが知識ベースを検索中:「{query}」", file=sys.stderr)
                    result = search_knowledge(query, docs)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        return f"(エージェントが予期せず停止しました: {response.stop_reason})"


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 lens.py <画像ファイルのパス> [\"任意の質問\"]", file=sys.stderr)
        sys.exit(1)

    image_path = Path(sys.argv[1])
    user_question = sys.argv[2] if len(sys.argv) > 2 else ""

    if not image_path.exists():
        print(f"エラー: 画像が見つかりません: {image_path}", file=sys.stderr)
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("エラー: 環境変数 ANTHROPIC_API_KEY が設定されていません。", file=sys.stderr)
        print("README.md の手順に従ってAPIキーを設定してください。", file=sys.stderr)
        sys.exit(1)

    try:
        media_type, image_data = encode_image(image_path)
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic()
    docs = load_knowledge()

    print(f"🤖 使用モデル: {MODEL}")
    print(f"🖼  解析する画像: {image_path.name}")
    print(f"📚 知識ベース: {list(docs.keys())}\n")

    answer = run_agent(client, media_type, image_data, user_question, docs)
    print(f"\n🌸 文化レンズ> {answer}")


if __name__ == "__main__":
    main()
