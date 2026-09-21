# amr-pj — 家庭向け小型AMR / 将来MoMa

最新の設計変更は **P1：分割PLA荷台を、切断済み3030と既製ブラケットで支持する構成**。中実角棒の切断・穴あけを廃止しました。300mm材4本パックのうち、下段2本・上段2本を使用します。

M0601C_111二輪、100.7mmタイヤ、TYG-50キャスター、下段460×300mmの骨格を継承。通常積載10kg、構造検証15kg・静的安全率2、電池・電装込み車体10kg以下を設計目標とします。追加機械ブレーキは採用せず、運用範囲は平坦な屋内床です。

| P1の変更と確認 | 内容 |
|---|---|
| 荷台支持 | 上段3030×300mmを2本、HBLFSN6を8個追加。溝ナットとM6で固定 |
| PLA荷台 | 300×300×12mm、4分割、50mmピッチ・φ4.5の36穴 |
| 荷台高さ | 床上141mm。旧PLA P0の124mmから17mm上昇 |
| 車体重量 | 推計9.419kg、10kgまで0.581kg。電装2.10kg枠込み、未実測 |
| 干渉 | 273部品・37,128ペアで公称体積干渉なし。36穴、工具、荷台・電池抜出しも確認 |
| 製作 | 荷台支持の金属追加工なし。前後電装トレイと4個のストッパも印刷 |
| 費用 | P1専用BOMに更新。Amazonの実表示価格・購入パックと未確定項目を区別 |

**P1は組付け確認済みの試作設計です。PLAの強度・クリープ・実機の安全率2と停止性能は未確認です。** 旧D2アルミ荷台の解析結果をP1の耐荷重として流用しません。荷物CG上限220mm、車体CG上限目標110mmは実機で確認します。

![格子穴付き上板を載せたP1のFreeCAD画面](cad/amr07/printed-deck-frame/cad-screen-isometric.png)

拡張用の格子板は4分割PLAで組付け済み。50mmピッチ・φ4.5の36穴と、M4用の裏ナットポケットを備えます。[真上から見た格子穴](cad/amr07/printed-deck-frame/cad-screen-grid-top.png)。締結説明に使う骨格だけの画像は、支持部分を見せるため一時的に上板を非表示にしています。

- [P1の設計理由・締結拡大画像・費用・検査](cad/amr07/printed-deck-frame/README.ja.md)
- [P1組立FCStd](cad/amr07/printed-deck-frame/AMR01_PrintedDeck_P1.FCStd) / [STEP](cad/amr07/printed-deck-frame/AMR01_PrintedDeck_P1.step)
- [P1全車BOM CSV](cad/amr07/printed-deck-frame/BOM.csv) / [途中小計と未確定分](cad/amr07/printed-deck-frame/cost_summary.json)
- [P1印刷STL一覧](cad/amr07/printed-deck-frame/print_manifest.json)
- [設計要件](cad/amr07/requirements.json) / [共通の駆動・取付金具設計とD2履歴](cad/amr07/README.ja.md)
- [モーター金具の実加工見積](cad/amr07/MACHINING_QUOTE.ja.md) / [金具STEP](cad/amr07/M0601C_mount_A6_R1.step)
- [キャスターのAmazon／コーナン調達](cad/amr07/CASTER_PROCUREMENT.ja.md)
- [電源・停止・回生と試験仕様](cad/amr07/ELECTRICAL_AND_VALIDATION.ja.md)
- [旧アルミD2の実見積・解析記録](cad/amr07/aluminum-grid-deck/README.ja.md) / [不採用の旧PLA P0](cad/amr07/printed-deck-concept/README.ja.md)

P1は `cad/amr07/printed-deck-frame/build_p1.py` をFreeCAD Pythonで実行して再生成します。続いて `python3 cad/amr07/printed-deck-frame/build_bom.py` で部品表を作成します。以下の既存コマンドは駆動計算や旧D2等の履歴用です。

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
