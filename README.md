# jev-test-prioritizer

`jev-test-prioritizer` は、AIなどによって生成されたテストコードについて、**今後もソースコードとして保守する価値があるか**を Jev で評価する実験的なCLIツールです。

テストを次の3種類に分類します。

- `KEEP` — 保守する価値がある
- `REVIEW` — 判断材料が不足している、または改善を検討すべき
- `REMOVE` — 保守する価値が低く、削除候補

このツールはテストの実行・削除・ソースコードの変更も行いません。

```text
AI / Coding Agent
        │
        ├─ production code を生成
        └─ test code を生成
                    │
                    ▼
          jev-test-prioritizer
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
        KEEP      REVIEW    REMOVE
```

主に Codex などの Coding Agent が生成したテストを、コードベースへ残す前にレビューする用途を想定しています。

## 何を評価するのか

候補となるテストについて、以下の4つの観点を Jev で評価します。

### Behavioral value

そのテストが、意味のある振る舞い・仕様・ビジネスルール・不変条件・エッジケースなどを検証しているかを評価します。

| 値 | 意味 |
| ---: | --- |
| 0 | ほぼ意味のある振る舞いを検証していない |
| 1 | 弱い |
| 2 | 意味のある振る舞いを検証している |
| 3 | 重要な振る舞いや契約を検証している |

assertionの数が多いだけでは高評価にはなりません。

### Regression protection

将来コードに現実的な回帰が発生した場合、そのテストが問題を検出できる可能性を評価します。

| 値 | 意味 |
| ---: | --- |
| 0 | ほとんど回帰を検出できない |
| 1 | 限定的 |
| 2 | 有用 |
| 3 | 強い回帰防止効果がある |

例えば、実装を間違えてもテストが通ってしまう場合、この値は低くなります。

### Implementation coupling

外部から意味のある振る舞いではなく、内部実装の詳細にどれだけ依存しているかを評価します。

**この値だけは高いほど望ましくありません。**

| 値 | 意味 |
| ---: | --- |
| 0 | 振る舞い中心 |
| 1 | 軽度に実装依存 |
| 2 | 強く実装依存 |
| 3 | 主に実装詳細をテストしている |

例えば以下のようなテストは高くなりやすくなります。

- private methodを直接検証する
- 内部メソッドの呼び出し回数を過度に固定する
- 内部オブジェクト構造を固定する
- 本質的でない処理順序を検証する

Mockを使うこと自体を問題視するものではありません。

### Specification alignment

候補テストが、現在の実装ではなく**本来の要求仕様を正しく検証しているか**を評価します。

| 値 | 意味 |
| ---: | --- |
| 0 | 明示された要求仕様と矛盾する |
| 1 | 整合性が弱い・曖昧 |
| 2 | おおむね要求仕様に沿っている |
| 3 | 明確に要求仕様を検証している |

これはAIによるコード生成では特に重要です。

AIが誤ったproduction codeを生成し、その誤った実装に合わせてテストまで生成する可能性があるため、

```text
production code と test が一致している
```

こと自体は、そのテストが正しい根拠にはなりません。

`--context` で与えられた要求や仕様を優先して評価します。

## インストール

Python 3.10 以上が必要です。

```bash
git clone https://github.com/ResonTypoc/jev-test-prioritizer.git
cd jev-test-prioritizer

python3 -m venv .venv
source .venv/bin/activate

python -m pip install .
```

開発用依存関係もインストールする場合:

```bash
python -m pip install -e '.[dev]'
```

## APIキー

Jev / TypeSafe のAPIキーを環境変数として設定します。

```bash
export TYPESAFE_API_KEY="your-api-key"
```

`.env` を使用する場合、このCLIは `.env` を自動では読み込みません。

例えば次のようにシェルへ読み込めます。

```bash
set -a
source .env
set +a
```

キーが設定されているかは、値そのものを表示せず次のように確認できます。

```bash
test -n "$TYPESAFE_API_KEY" && echo "API key is set"
```

## 使い方

基本形:

```bash
jev-test-prioritizer evaluate \
  --source <production-code> \
  --test <candidate-test> \
  --context "<requirement or intended behavior>"
```

例えば:

```bash
jev-test-prioritizer evaluate \
  --source examples/payment_service.rb \
  --test examples/payment_service_test.rb \
  --context "Invalid payments must be rejected before reaching the payment gateway."
```

`--source` には評価対象テストに関連するproduction codeを指定します。

`--test` には、残す価値を評価したい候補テストを指定します。

`--context` には、そのコードが本来満たすべき要求・仕様・バグ修正内容などを指定します。

Ruby、Rails、RSpec、Minitest、JavaScript、React、Vitest、Jest、Python、pytestなどの特定言語やテストフレームワークには依存しません。

入力されたコードはテキストとしてJevへ送信されます。

## サンプル

### 1. 意味のある振る舞いを守るテスト

`examples/payment_service.rb` では、0以下の金額が決済Gatewayへ渡らないようにしています。

候補テスト `examples/payment_service_test.rb` は、

- 0や負数が拒否される
- `ArgumentError` が発生する
- 無効な決済がGatewayまで到達しない

ことを検証しています。

実行:

```bash
jev-test-prioritizer evaluate \
  --source examples/payment_service.rb \
  --test examples/payment_service_test.rb \
  --context "Invalid payments must be rejected before reaching the payment gateway."
```

実際の実行例:

```text
Test retention evaluation

Behavioral value         2.9 / 3 (confidence 0.90)
Regression protection    2.21 / 3 (confidence 0.55)
Implementation coupling  0.37 / 3 (confidence 0.63)
Specification alignment  2.96 / 3 (confidence 0.96)

Decision                 KEEP
Confidence               0.97
```

この例では、

- 要求仕様に直接関係する振る舞いを検証している
- 将来の回帰を検出する価値がある
- private methodなどの内部実装にはほぼ依存していない
- `--context` で与えられた要求と強く一致している

ため、`KEEP` と判定されています。

`Regression protection` が満点ではないのは、このテストが決済処理全体ではなく「無効な金額をGatewayへ渡さない」という特定の振る舞いを守っているためです。

`Implementation coupling` が完全な0ではない理由としては、例外メッセージの完全一致など、一部に実装詳細へ依存する要素が含まれていることが考えられます。

### 2. 実装詳細に強く依存するテスト

`examples/formatter_test.rb` は、public APIではなくprivate methodである `normalize` を直接呼び出しています。

さらに、

```ruby
normalize("Ada")
```

という、そもそも前後に空白がない値を検証しています。

要求は、

```text
The requirement is a public greeting with surrounding whitespace removed.
```

です。

実行:

```bash
jev-test-prioritizer evaluate \
  --source examples/formatter.rb \
  --test examples/formatter_test.rb \
  --context "The requirement is a public greeting with surrounding whitespace removed."
```

実際の実行例:

```text
Test retention evaluation

Behavioral value         0.56 / 3 (confidence 0.50)
Regression protection    0.66 / 3 (confidence 0.58)
Implementation coupling  2.82 / 3 (confidence 0.82)
Specification alignment  1.09 / 3 (confidence 0.80)

Decision                 REMOVE
Confidence               0.35
```

JSON出力の一例:

```json
{
  "behavioral_value": {
    "score": 0.57,
    "confidence": 0.49,
    "probabilities": {
      "0": 0.47,
      "1": 0.5,
      "2": 0.03,
      "3": 0.0
    }
  },
  "regression_protection": {
    "score": 0.67,
    "confidence": 0.58,
    "probabilities": {
      "0": 0.38,
      "1": 0.58,
      "2": 0.04,
      "3": 0.0
    }
  },
  "implementation_coupling": {
    "score": 2.86,
    "confidence": 0.86,
    "probabilities": {
      "0": 0.0,
      "1": 0.01,
      "2": 0.12,
      "3": 0.87
    }
  },
  "specification_alignment": {
    "score": 1.09,
    "confidence": 0.78,
    "probabilities": {
      "0": 0.07,
      "1": 0.79,
      "2": 0.12,
      "3": 0.02
    }
  },
  "decision": {
    "value": "remove",
    "confidence": 0.45,
    "probabilities": {
      "keep": 0.03,
      "review": 0.34,
      "remove": 0.63
    }
  }
}
```

このテストについてJevは、

- 意味のある外部振る舞いをほとんど検証していない
- 実際の要求に対する回帰検出力が低い
- private methodへの依存が非常に強い
- 要求仕様との整合性が弱い

と評価しています。

特に、

```json
"implementation_coupling": {
  "probabilities": {
    "3": 0.87
  }
}
```

から、実装詳細への依存をかなり明確に問題視していることが分かります。

一方、最終判定は、

```json
"probabilities": {
  "keep": 0.03,
  "review": 0.34,
  "remove": 0.63
}
```

となっています。

`REMOVE` が最有力ではありますが、`REVIEW` にも一定の確率を残しています。

これは「削除して安全である」と断定しているわけではなく、

> 現在与えられている情報だけを見ると、このテスト単体を今後も保守する価値は低い

という判断です。

## score と confidence

各評価値には `score` と `confidence` があります。

例えば:

```json
{
  "score": 2.86,
  "confidence": 0.86
}
```

`score` は0〜3の各評価レベルについてJevが出した確率分布から計算される期待値です。

そのため整数とは限らず、`2.86` のような値になります。

`confidence` は、その評価に対するJevの確信度です。

例えば、

```text
Regression protection 2.21 / 3 (confidence 0.55)
```

は、

> 回帰防止効果はおおむね2付近と考えるが、その強さにはある程度不確実性がある

と読むことができます。

なお、各評価軸のconfidenceと最終的な `KEEP / REVIEW / REMOVE` のconfidenceは別々の判断です。

そのため、

```text
Regression protection confidence = 0.55
Decision KEEP confidence = 0.97
```

のような結果もあり得ます。

「回帰防止効果が2なのか3なのかは迷うが、このテストを残すべきという判断自体には強い確信がある」という状態を表せます。

## JSON出力

Coding Agentなどから利用する場合は `--json` を使用します。

```bash
jev-test-prioritizer evaluate \
  --source examples/payment_service.rb \
  --test examples/payment_service_test.rb \
  --context "Invalid payments must be rejected before reaching the payment gateway." \
  --json
```

成功時、stdoutにはJSONのみを出力します。

このため、CodexなどからCLIを実行して結果を機械的に扱うことができます。

## 注意事項

このツールの判定はあくまでレビューのためのシグナルです。

`REMOVE` は、

```text
このテストを削除しても安全である
```

ことを証明するものではありません。

現在のMVPでは以下は行いません。

- テストの実行
- repository全体のテスト探索
- 他テストとの重複判定
- coverage解析
- mutation testing
- テストファイルの自動削除
- CIでのテスト選択
- 特定言語・テストランナー向けの解析

また、production code・candidate test・`--context` の内容はJevサービスへ送信されます。

機密情報を含むコードを使用する場合は、利用環境のデータ取り扱い要件を確認してください。

AIによる判定のため、モデルのバージョンや実行ごとに結果が多少変動する場合があります。

## 開発

このプロジェクト自身のテスト:

```bash
python -m pip install -e '.[dev]'
python -m pytest
```

自動テストでは実際のJev APIを呼び出しません。

## License

MIT License