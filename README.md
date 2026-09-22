# AMR-01：D5 マキタ18V電源・後端交換

**純正BL1860B（18V6Ah）＋DC18RF充電器を選定し、電池とアダプターを後端から上へ取り出す構成へ変更しました。** 電池の36mm厚制約は撤回。工具を使わず、保持ベルト1本とコネクタを外して交換します。計算機は天板下へ下げ、300×300×4mmの格子穴アルミ天板は床上103mmです。

![FreeCAD実画面：D5組立](cad/amr07/makita-power/cad-screen-assembled.png)

![FreeCAD実画面：天板と荷物を残した電池交換](cad/amr07/makita-power/cad-screen-battery-exchange.png)

電池・充電器とも新規購入として、セット20,400円＋アダプター2,980円＝**23,380円**（税込・東京都の表示送料込み）を計上。電池・アダプターは公開寸法の外形包絡モデルで、現物の嵌合位置・保護動作は未検証です。

車体重量見込みは**約8.55kg**。208物理部品と電源等の包絡、電池の上方140mm交換経路、格子穴、キャスター・タイヤの公称干渉検査を通過。重心の受入れ範囲を前後±25mm・左右±10mm・高さ115mm以下へ更新し、輪荷重を再計算しました。通常積載10kg、構造検証15kg・静的安全率2は設計目標で、実機認定前です。平坦な屋内床で使用し、追加機械ブレーキは採用しません。

全車の途中小計は**69,633円＋120.90USD＋未確定分**。参考円換算で約88,650円。既存の予算枠を含み、保護回路・計算機・配線・税等が残るため完成車総額ではありません。

- [現行D5：選定理由、配置比較、固定・交換、費用、残る検証](cad/amr07/makita-power/README.ja.md)
- [組立FCStd](cad/amr07/makita-power/AMR01_MakitaPower_D5.FCStd)／[電源外形入りSTEP](cad/amr07/makita-power/AMR01_MakitaPower_D5-with-power-envelopes.step)
- [全車BOM](cad/amr07/makita-power/BOM.csv)／[価格・未確定品](cad/amr07/makita-power/cost_summary.json)
- [交換する印刷2部品ZIP](cad/amr07/makita-power/D5-power-print-files.zip)／[保存物の再検査](cad/amr07/makita-power/saved_artifact_validation.json)
- [設計要件](cad/amr07/requirements.json)／[電源・停止・回生と試験仕様](cad/amr07/ELECTRICAL_AND_VALIDATION.ja.md)
- [D3から継承する天板と実加工見積](cad/amr07/aluminum-direct-deck/README.ja.md)／[モーター金具の実見積](cad/amr07/MACHINING_QUOTE.ja.md)
- [旧D4：薄型電池の横引出し試作](cad/amr07/battery-drawer/README.ja.md)

## 比較履歴・共通資料

- [A5：5案の実加工費・強度比較](cad/amr06/README.ja.md) / [修正元の設計レビュー](cad/amr06/DESIGN_REVIEW_2026-09-21.ja.md)
- [A4：M0601C_111と専用低背金具](cad/amr05/README.ja.md)
- [メーカーCAD・モーター仕様・タイヤ交換](cad/amr05/M0601C_INTERFACE.ja.md)
- [実加工サイト見積のスキル](skills/cnc-quote/SKILL.md)
- [A3：DDSM115](cad/amr04/README.ja.md) / [A2：FIT0185](cad/amr03/README.ja.md)
- [第二案B・却下したベルト案C](cad/amr02/README.ja.md) / [第一案](cad/amr01/README.ja.md)
- [初期基礎設計書](docs/amr-01/DESIGN.ja.md) / [FreeCAD環境](cad/README.md)
