# AMR-01：D6 1階電装・2階荷台

**電池・計算機・電源回路を基礎フレーム上の1階へ、格子穴アルミ荷台を2階へ配置しました。** 計算機を床下へ吊る案を撤回。RoboMaster、学生ロボコン、公開ロボットの設計資料を参照し、4支柱支持と部品ごとの交換経路を設計しています。

![FreeCAD実画面：D6組立](cad/amr07/two-story/cad-screen-assembled.png)

![FreeCAD実画面：1階の電池・計算機・回路](cad/amr07/two-story/cad-screen-first-floor.png)

荷台は300×300×4mm・上面233mm。100mm溝付き支柱4本と、購入予定4本セットに含まれる300mmレール2本を使います。電池は8mm持上げ後に後方へ220mm、計算機は側方へ230mm抜き出せます。荷台を残した交換経路と干渉をCADで検査しました。接続金具の拡大画面も保存しています。

車体は**推計9.728kg**。通常荷物10kg、構造比較15kg・静的安全率2は設計目標で、実物の固定・剛性・電源保護・走行試験前です。電池はBL1860B6Ah＋接続アダプターを選定済み、PCは120×100×60mmの予約モデルです。

D5からの小計増は**4,066円**（追加金物3,968円＋PLA材料参考98円）。追加M6ねじ・送料差額等は別。全車の途中小計は73,699円＋120.90USD＋未確定分、既存参考為替では約92,713円です。電池・充電器・アダプター23,380円を含みますが、完成車購入総額ではありません。

- [現行D6：配置・固定・交換・費用・検証範囲](cad/amr07/two-story/README.ja.md)
- [参照したロボコン機体と設計理由](cad/amr07/two-story/REFERENCE_DESIGNS.ja.md)
- [組立FCStd](cad/amr07/two-story/AMR01_TwoStorey_D6.FCStd)／[機器外形付きSTEP](cad/amr07/two-story/AMR01_TwoStorey_D6-with-equipment-envelopes.step)
- [全車BOM](cad/amr07/two-story/BOM.csv)／[費用・未確定分](cad/amr07/two-story/cost_summary.json)
- [電装床4枚の印刷ZIP](cad/amr07/two-story/D6-first-floor-print-files.zip)／[保存物再検査](cad/amr07/two-story/saved_artifact_validation.json)
- [設計要件](cad/amr07/requirements.json)／[電源・停止・回生と試験仕様](cad/amr07/ELECTRICAL_AND_VALIDATION.ja.md)
- [同じ天板の実加工見積](cad/amr07/aluminum-direct-deck/README.ja.md)／[モーター金具の実見積](cad/amr07/MACHINING_QUOTE.ja.md)
- [電源選定と旧D5配置](cad/amr07/makita-power/README.ja.md)／[旧D4：薄型電池の横引出し](cad/amr07/battery-drawer/README.ja.md)

## 比較履歴・共通資料

- [A5：5案の実加工費・強度比較](cad/amr06/README.ja.md) / [修正元の設計レビュー](cad/amr06/DESIGN_REVIEW_2026-09-21.ja.md)
- [A4：M0601C_111と専用低背金具](cad/amr05/README.ja.md)
- [メーカーCAD・モーター仕様・タイヤ交換](cad/amr05/M0601C_INTERFACE.ja.md)
- [実加工サイト見積のスキル](skills/cnc-quote/SKILL.md)
- [A3：DDSM115](cad/amr04/README.ja.md) / [A2：FIT0185](cad/amr03/README.ja.md)
- [第二案B・却下したベルト案C](cad/amr02/README.ja.md) / [第一案](cad/amr01/README.ja.md)
- [初期基礎設計書](docs/amr-01/DESIGN.ja.md) / [FreeCAD環境](cad/README.md)
