# herdr-focus-attention（日本語）

対応が必要なエージェントを、前後に移動するための Herdr プラグインです。

対象はステータスの優先度順（既定では `blocked` > `done` > `idle`）に並び、
同じステータスの中では状態が変わった時刻が新しい順になります。
いま見ているエージェントが一覧に含まれていれば、その次（または前）に進むため、
繰り返し押すだけで順に対応すべきエージェントを回れます。
対象がいないときは黙って失敗せず、トーストで知らせます。

[English](README.md) | [日本語](README.ja.md) | [中文](README.zh-CN.md)

## インストール

```bash
herdr plugin install kuwa72/herdr-focus-attention
```

`PATH` 上に Python 3.11 以降が `python3` として必要です（標準ライブラリのみ使用）。
Windows 11 では `python3` のアプリ実行エイリアスで動きます。使えない場合は
python.org やストアから Python を入れて、`python3` で起動できるようにします。

## キーバインド

キーバインドは Herdr 側で持つため、`~/.config/herdr/config.toml` に書きます。

```toml
[[keys.command]]
key = "prefix+a"
type = "plugin_action"
command = "kuwa72.focus-attention.next"
description = "対応が必要な次のエージェントに移動"

[[keys.command]]
key = "prefix+shift+a"
type = "plugin_action"
command = "kuwa72.focus-attention.prev"
description = "対応が必要な前のエージェントに戻る"
```

反映します。

```bash
herdr server reload-config
```

`f9` や `f10` などのファンクションキーは、プレフィックスを挟まず直接割り当てられます。
印字キーと違って文字入力を奪わないため、1打で呼び出せます。

```toml
[[keys.command]]
key = "f9"
type = "plugin_action"
command = "kuwa72.focus-attention.next"
description = "対応が必要な次のエージェントに移動"

[[keys.command]]
key = "shift+f9"  # "f10" でもよい
type = "plugin_action"
command = "kuwa72.focus-attention.prev"
description = "対応が必要な前のエージェントに戻る"
```

## 設定

初回実行時に、プラグインの設定ディレクトリーへ `config.toml` を作ります。場所の確認はこちらです。

```bash
herdr plugin config-dir kuwa72.focus-attention
```

```toml
# 「対応が必要」とみなすエージェントのステータス。先に書いた方を優先します。
# ここにないステータスへは移動しません。
# 指定できる値: blocked, done, working, idle, unknown
priority = ["blocked", "done", "idle"]

# "all" = すべてのワークスペースを見る。"workspace" = 作業中のものだけ見る
scope = "all"
```

設定は呼び出すたびに読み込むため、再読み込みは要りません。

## トラブルシューティング

```bash
herdr plugin action invoke kuwa72.focus-attention.next
herdr plugin log list --plugin kuwa72.focus-attention
```

## ライセンス

0BSD — [LICENSE](LICENSE) を参照してください。
