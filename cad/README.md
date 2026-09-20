# FreeCAD + Codex MCP

AMRの第一案は[amr01/README.ja.md](amr01/README.ja.md)へ。FCStd・STEP・実CAD画面・部品表・費用と検証結果を収録しています。

導入日: 2026-09-20。Ubuntu 24.04 / ARM64。

- FreeCAD 1.1.3: 公式ARM64 AppImage。公式SHA-256照合済み。
- freecad-mcp 0.1.24: uv toolで専用Python環境に導入。
- アドオン: neka-nat/freecad-mcp commit `751974609a401660a58a1772ef16f3afbeba9ba1`。
- CodexのグローバルMCP設定に `freecad` を登録済み。
- RPCは `127.0.0.1:9875` のみ。FreeCAD起動時に自動開始。

## 使う

Codexを再起動し、`/mcp` で `freecad` を確認する。
例: 「FreeCADで幅100mm、奥行60mm、厚さ4mmのプレートを作って」。

FreeCADは仮想画面上のユーザーサービスとして稼働する。
ユーザーサービス起動時にも自動開始する設定。画面キャプチャはMCPの `get_view` で取得できる。
通常のリモートデスクトップには、この仮想画面のウィンドウは表示されない。

```sh
systemctl --user status freecad-mcp
systemctl --user start freecad-mcp
systemctl --user stop freecad-mcp
journalctl --user -u freecad-mcp -n 50
```

停止・再起動前に、MCPから編集中のドキュメントを保存すること。
通常のデスクトップで開く場合は、保存して上記サービスを停止した後、
デスクトップのターミナルから `freecad /home/sadasue/amr-pj/cad/CenterHolePlate.FCStd` を実行する。
今回のリモートデスクトップ `:10.0` は、起動時にQtがクリップボードの応答を待ち続けたため、
安定稼働を確認したXvfbの仮想画面を標準のMCP実行環境とした。
デスクトップ表示の問題自体は未解消。

## 動作確認

MCPの初期化・17ツールの列挙・RPC/GUIの正常状態・モデル作成・ドキュメント一覧を確認。
別プロセスの `execute_code_headless` も検証。
60 × 40 × 5 mm、中央に直径10 mmの貫通穴がある部品を作成し、
形状の妥当性・ソリッド数1・理論体積との一致を検証した。

- `CenterHolePlate.FCStd`: 編集可能なFreeCADファイル。
- `CenterHolePlate.step`: 他のCADへ渡せるSTEPファイル。
- `CenterHolePlate.png`: プレビュー。
- `create_sample.py`: サンプル再作成コード。FreeCADのGUI内で実行する。

FEM解析とCAM加工経路は今回の検証対象外。

## 配置

- 本体: `~/.local/opt/freecad/`
- 起動コマンド: `~/.local/bin/freecad`, `~/.local/bin/freecadcmd`
- MCP: `~/.local/bin/freecad-mcp`
- アドオン: `~/.local/share/FreeCAD/v1-1/Mod/FreeCADMCP/`
- アドオン設定: `~/.local/share/FreeCAD/v1-1/freecad_mcp_settings.json`
- サービス: `~/.config/systemd/user/freecad-mcp.service`

## 参照

- 記事: https://note.com/npaka/n/n50c8ca0ac16c
- FreeCAD公式配布: https://github.com/FreeCAD/FreeCAD/releases/tag/1.1.3
- MCP実装と導入方法: https://github.com/neka-nat/freecad-mcp
- OpenAI公式MCP設定: https://developers.openai.com/codex/mcp
