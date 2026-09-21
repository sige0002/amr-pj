# amr-pj — 家庭向け小型AMR / 将来MoMa

現行案は **D3：一枚アルミ天板を、元の下段3030へ直接固定する構成**。分割PLA天板から戻し、嵩上げ用フレーム・天板下スペーサーを取り除きました。天板上面は床上103mmです。

M0601C_111二輪、100.7mmタイヤ、TYG-50キャスター、下段460×300mmの骨格を継承。通常積載10kg、構造検証15kg・静的安全率2、電池・電装込み車体10kg以下を設計目標とします。運用範囲は平坦な屋内床、追加機械ブレーキなし。

| D3の変更と確認 | 内容 |
|---|---|
| 天板 | 6061-T6・300×300×4mmの一枚板、継ぎ目なし |
| 高さ・固定 | 床上103mm。下段へM6と溝ナット6組で直付け。P1より38mm低い |
| 拡張性 | 50mm格子・φ4.5の36通し穴。24穴は裏ナット、12穴はフレーム溝のM4ナットを使用 |
| 干渉修正 | 電池受けを7mm下げ、前後トレイ・穴・ベルト経路を修正。地上高25mmを維持 |
| 検査 | 208部品・21,528ペアで公称干渉なし。36穴、工具、天板・電池・タイヤの取外しも確認 |
| 車体重量 | 推計8.246kg、10kgまで1.754kg。電池・電装2.10kg枠込み、未実測 |
| 天板の再見積 | 修正版STEP/PDFで加工28.67＋日本向けUPS9.98＝38.65 USD、参考約6,080円 |
| 全車の途中小計 | 46,212円＋120.90 USD＋未確定分。既知部分はP1より参考約1,784円減 |

![D3直付けアルミ天板のFreeCAD画面](cad/amr07/aluminum-direct-deck/cad-screen-isometric.png)

[側面から見た高さ](cad/amr07/aluminum-direct-deck/cad-screen-low-profile.png) / [格子穴の真上画像](cad/amr07/aluminum-direct-deck/cad-screen-grid-top.png)。画像は組立CADの実画面です。

CAD検査は公称形状による確認で、実機の耐荷重・安全率2を保証するものではありません。自動加工見積は担当者審査前、円表示はECB2026-09-21による参考換算で、税・決済費用などは別です。

- [D3の設計理由・干渉修正・締結・費用](cad/amr07/aluminum-direct-deck/README.ja.md)
- [現行組立FCStd](cad/amr07/aluminum-direct-deck/AMR01_AluminumDirect_D3.FCStd) / [STEP](cad/amr07/aluminum-direct-deck/AMR01_AluminumDirect_D3.step)
- [現行BOM CSV](cad/amr07/aluminum-direct-deck/BOM.csv) / [小計と未確定項目](cad/amr07/aluminum-direct-deck/cost_summary.json)
- [D3加工用STEP](cad/amr07/aluminum-direct-deck/AMR_GridDeck_C45_D3.step) / [図面PDF](cad/amr07/aluminum-direct-deck/AMR_GridDeck_C45_D3.pdf) / [実見積画面](cad/amr07/aluminum-direct-deck/quote-evidence/C45-economic.png)
- [設計要件](cad/amr07/requirements.json) / [検査・質量内訳](cad/amr07/aluminum-direct-deck/validation.json)
- [電池受け・トレイ・ストッパの印刷7部品](cad/amr07/aluminum-direct-deck/D3-print-files.zip)
- [モーター金具の実加工見積](cad/amr07/MACHINING_QUOTE.ja.md) / [キャスター調達](cad/amr07/CASTER_PROCUREMENT.ja.md)
- [電源・停止・回生と試験仕様](cad/amr07/ELECTRICAL_AND_VALIDATION.ja.md)
- [旧P1と継ぎ目レビュー](cad/amr07/printed-deck-frame/README.ja.md) / [旧D2の記録](cad/amr07/aluminum-grid-deck/README.ja.md)

D3の再生成は `cad/amr07/aluminum-direct-deck/build_d3.py` をFreeCAD Pythonで実行し、`python3 cad/amr07/aluminum-direct-deck/build_bom.py` でBOMを更新します。以下は共通駆動計算と旧D2の履歴用コマンドです。

## 再計算

```sh
python3 cad/amr07/calculate_design.py --check-only
python3 cad/amr07/cargo_deck.py
python3 cad/amr07/record_cost.py
python3 cad/amr07/build_bom.py
```

Excelの更新方法は[BOMのデータと更新](cad/amr07/BOM.ja.md#データと更新)、CAD再生成は[A6 README](cad/amr07/README.ja.md)。見積済み図面/STEPを変更するときは別改訂で見積り直します。

## 比較履歴・共通資料

- [A5：5案の実加工費・強度比較](cad/amr06/README.ja.md) / [修正元の設計レビュー](cad/amr06/DESIGN_REVIEW_2026-09-21.ja.md)
- [A4：M0601C_111と専用低背金具](cad/amr05/README.ja.md)
- [メーカーCAD・モーター仕様・タイヤ交換](cad/amr05/M0601C_INTERFACE.ja.md)
- [実加工サイト見積のスキル](skills/cnc-quote/SKILL.md)
- [A3：DDSM115](cad/amr04/README.ja.md) / [A2：FIT0185](cad/amr03/README.ja.md)
- [第二案B・却下したベルト案C](cad/amr02/README.ja.md) / [第一案](cad/amr01/README.ja.md)
- [初期基礎設計書](docs/amr-01/DESIGN.ja.md) / [FreeCAD環境](cad/README.md)
