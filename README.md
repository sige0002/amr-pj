# AMR-01：E4 レビュー反映版

**機構設計とロボット・電装の独立AIレビューを受け、天板とスイッチ取付部を修正しました。** 天板は中央対称25穴、外周6点の極低頭固定、荷物止めは標準から撤去。スイッチはナット・工具・端末空間と配線保持を追加しました。

[設計・CAD画像](cad/amr07/reviewed-design/README.ja.md) ／ [標準BOM](cad/amr07/reviewed-design/BOM.ja.md) ／ [明細Markdown](cad/amr07/reviewed-design/BOM-details.ja.md) ／ [CSV](cad/amr07/reviewed-design/BOM.csv) ／ [配線](cad/amr07/reviewed-design/WIRING.ja.md) ／ [レビュー・対応表](cad/amr07/design-review-e3/README.ja.md)

![FreeCAD実画面：E4標準](cad/amr07/reviewed-design/cad-screen-overall.png)

標準車体推計10.363kg、通常積載10kgの設計条件。実機荷重・走行試験は未実施です。変更部8,697組で新規干渉なし。格子穴の下面工具作業とスイッチ蓋の整備は電池を外す条件です。

**計上済み小計約88,560円＋新天板・送料・PC・給電・HAT・最終配線等の未計上分。** 天板形状の変更により旧見積を外しているため、以前との差は完成車の節約額ではありません。

[モニター付きO1は別オプション](cad/amr07/monitor-option/README.ja.md)。後ろ向きの7型を左右の3030で支持する取付モックで、標準CAD・BOMには含めません。モニター機種・価格は未確定です。

![FreeCAD実画面：モニターは別オプション](cad/amr07/monitor-option/cad-screen-overall.png)

- [標準FreeCAD](cad/amr07/reviewed-design/AMR01_Reviewed_E4.FCStd) ／ [標準STEP](cad/amr07/reviewed-design/AMR01_Reviewed_E4.step) ／ [標準PLA試作12個ZIP](cad/amr07/reviewed-design/E4-print-prototypes.zip)
- [モニター付きFreeCAD](cad/amr07/monitor-option/AMR01_OptionalMonitor_O1.FCStd) ／ [オプション専用BOM](cad/amr07/monitor-option/BOM.ja.md)
- [天板の再計算](cad/amr07/design-review-e3/DECK_REVISION_CHECK.ja.md) ／ [干渉確認](cad/amr07/reviewed-design/validation.json)

非常停止の実負荷適合、主電源ナット/端子の実寸、PLAの長期締付保持、完成ハーネス、ファームウェア実装と試験は残っています。CADで公称配置が成立したことと、製作・通電の確定は区別しています。

## 継承した機械構成とシミュレーション

D6.5の各床4点固定、中央支持梁、四隅の連続したPLA床、計算機下の絶縁用カバーは維持しています。[床の設計](cad/amr07/two-story/README.ja.md)／[PLA床解析と限界](cad/amr07/two-story/pla-strength/README.ja.md)／[ロボコン等の参考設計](cad/amr07/two-story/REFERENCE_DESIGNS.ja.md)。

[Isaac Sim 5向けURDF・取込手順](sim/isaac_sim/README.ja.md)と[データZIP](sim/isaac_sim/amr_d65_isaac5.zip)は**D6.5時点**のモデルです。E4とモニターオプションは未反映。URDF検査とMuJoCo補助走行は実施済み、Isaac Sim本体での実行は未確認です。

![旧D6.5の走行シミュレーション（MuJoCo）](sim/isaac_sim/amr_d65_motion_mujoco.gif)

## 比較履歴・共通資料


- [A5：5案の実加工費・強度比較](cad/amr06/README.ja.md) / [修正元の設計レビュー](cad/amr06/DESIGN_REVIEW_2026-09-21.ja.md)
- [A4：M0601C_111と専用低背金具](cad/amr05/README.ja.md)
- [メーカーCAD・モーター仕様・タイヤ交換](cad/amr05/M0601C_INTERFACE.ja.md)
- [実加工サイト見積のスキル](skills/cnc-quote/SKILL.md)
- [A3：DDSM115](cad/amr04/README.ja.md) / [A2：FIT0185](cad/amr03/README.ja.md)
- [第二案B・却下したベルト案C](cad/amr02/README.ja.md) / [第一案](cad/amr01/README.ja.md)
- [初期基礎設計書](docs/amr-01/DESIGN.ja.md) / [FreeCAD環境](cad/README.md)
