# amr-pj — 家庭向け小型AMR / 将来MoMa

最新は **A6：通常積載10kg、5°登坂時8kg、構造検証は荷物15kg・静的安全率2**。車体は電池・電装・荷台込み10kg以下を目標とし、現在の推計は**8.73kg**です。25kgは構造計算時の総重量で、積載量ではありません。

レビューを受け、金具の機能公差・ねじ座面・溝ナットと3030溝の寸法、荷台と荷物固定、重心範囲、停止回路の構成と実機試験仕様を修正しました。M0601C_111二輪、Amazon3030の300/400mm定尺、モーター支持スペーサーなしの低床構成を維持しています。

**実機での安全率2、低速連続駆動、坂道保持は未確認です。** CAD検査・条件付き計算の完了を製作・運用の承認とはしていません。

- [A6の設計・変更理由・CAD画面](cad/amr07/README.ja.md)
- [レビュー8項目への対応と残る確認](cad/amr07/REVIEW_RESPONSE.ja.md)
- [車体FCStd](cad/amr07/AMR01_M0601C_A6.FCStd) / [車体STEP](cad/amr07/AMR01_M0601C_A6.step)
- [金具STEP](cad/amr07/M0601C_mount_A6_R1.step) / [機能公差付き図面PDF](cad/amr07/M0601C_mount_A6_R1.pdf)
- [荷台の設計・固定・費用](cad/amr07/DECK_REVIEW.ja.md) / [金具・締結と公差](cad/amr07/MOUNT_INTERFACE_REVIEW.ja.md)
- [加工サイトの実見積と証拠](cad/amr07/MACHINING_QUOTE.ja.md) / [BOM](cad/amr07/BOM.csv)
- [電源・停止・回生の構成と試験仕様](cad/amr07/ELECTRICAL_AND_VALIDATION.ja.md)
- [P1S用PLA仮合わせモックZIP](cad/amr07/print-mock/M0601C_A6_PLA_mock_files.zip) / [使い方](cad/amr07/print-mock/PRINT_GUIDE.ja.md)

| 現行条件 | 内容 |
|---|---|
| フレーム | 3030・400mm×4本＋300mm×2本、外形460×300mm、純正接合HBLFSN6-SET |
| 駆動 | M0601C_111×2、100.7mm適合タイヤ、後方50mm自在キャスター |
| 金具 | A6061-T6、同形2個、幅90・厚5・ピッチ75。受け着座、穴・座金・機能公差を修正 |
| 荷台 | 300×300×4mm A5052、上面118mm、金属支持・4ストッパ・2ベルト |
| 荷物条件 | 中央200×200mm連続平底、CG前後/左右±30mm・高さ220mm以下。容器込み10kg/5°時8kg |
| 質量 | 電装2.10kg枠・荷台固定具込み推計8.733kg、未実測 |
| CAD検査 | 222物理部品・24,531ペアで公称体積干渉なし。タイヤ/キャスター接地z=0、工具・電池整備空間を確認 |
| 金具実見積 | 2個75.02 USD＋日本宛表示送料7.23 USD＝82.25 USD、図面審査前の自動見積 |
| 費用途中小計 | 54,910円＋82.25 USD＋未確定分。完成車総額ではない |

費用はTaobaoモーター約7,000円/個という仮枠、タイヤ別購入、荷台等の板材は自加工する条件です。追加の荷台と停止回路候補を計上し、使わなくなったUSB-RS485Bとその送料を除きました。電池・主計算機・基板/配線・保持機構・各店送料・輸入諸費、外注へ切り替える板材加工等は未確定。円とUSDを推定レートで合算していません。

![A6荷台付き車体・FreeCAD実画面](cad/amr07/cad-screen-isometric.png)

![A6下面・FreeCAD実画面](cad/amr07/cad-screen-underside.png)

購入モーターは販売元案内のSTEPを使用。タイヤとカバーは公開外形からの簡略形状で、軸方向組付け位置と全幅・輪距は現物照合が必要です。半透明形状は電池・電装等の予約です。

## 再計算

```sh
python3 cad/amr07/calculate_design.py --check-only
python3 cad/amr07/cargo_deck.py
python3 cad/amr07/record_cost.py
```

再生成は[A6 README](cad/amr07/README.ja.md)。見積済み図面/STEPを変更するときは別改訂で見積り直します。

## 比較履歴・共通資料

- [A5：5案の実加工費・強度比較](cad/amr06/README.ja.md) / [修正元の設計レビュー](cad/amr06/DESIGN_REVIEW_2026-09-21.ja.md)
- [A4：M0601C_111と専用低背金具](cad/amr05/README.ja.md)
- [メーカーCAD・モーター仕様・タイヤ交換](cad/amr05/M0601C_INTERFACE.ja.md)
- [実加工サイト見積のスキル](skills/cnc-quote/SKILL.md)
- [A3：DDSM115](cad/amr04/README.ja.md) / [A2：FIT0185](cad/amr03/README.ja.md)
- [第二案B・却下したベルト案C](cad/amr02/README.ja.md) / [第一案](cad/amr01/README.ja.md)
- [初期基礎設計書](docs/amr-01/DESIGN.ja.md) / [FreeCAD環境](cad/README.md)
