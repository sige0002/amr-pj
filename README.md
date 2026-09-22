# amr-pj — 家庭向け小型AMR / 将来MoMa

現行案は **D4：低いアルミ天板を維持し、電池を側面から交換する構成**。D3で悪化した電池アクセスを修正し、電池を受け皿に固定するベルト・当て材と、受け皿を車体に固定するガイド・抜け止めねじを追加しました。

**電池そのものは未選定です。** 旧120×80×65mmは寸法予約でした。D4は薄型5Sの公開寸法を使った機械試作で、設置時の本体上限は50×112×36mm。容量・保護・充電器・総費用の選定は残ります。

![天板・荷物例を残して電池を取り出すFreeCAD実画面](cad/amr07/battery-drawer/cad-screen-battery-exchange.png)

| D4の構成 | 内容 |
|---|---|
| 天板 | D3の6061-T6一枚板300×300×4mmを継承。上面103mm、下段3030へ直付け |
| 電池の固定 | 底のパッド・四辺の当て面・15mm幅ベルト2本。ベルトを受け皿の専用溝へ通す |
| 受け皿の固定 | 印刷ガイド2個、M4抜け止め2本。フレームへの既存M6固定4組を再使用 |
| 交換方法 | 電源を切り、外側のコネクタを切離し、M4を2本外して横へ220mm抜く。最後は手で支える |
| 高さ | 地上高25mmを維持。天板・荷物を降ろさず交換する経路を確認 |
| CAD確認 | 216物理部品の公称干渉0件。電池・ベルト・受け皿の連続移動、工具、指の空間を確認 |
| 車体重量 | 推計約8.34kg。未選定の電池・電装2.10kg枠を維持、未実測 |
| 費用 | 新たな金属加工なし。追加印刷材料はD3比参考約150円。小ねじ・パッド・電池等の未価格品はBOMに明示 |

M0601C_111二輪、100.7mmタイヤ、TYG-50、下段460×300mmの骨格は従来どおり。通常積載10kg、構造検証15kg・静的安全率2、電池・電装込み車体10kg以下を設計目標とします。運用範囲は平坦な屋内床、追加機械ブレーキなし。CADの公称干渉検査は、PLAの保持力・温度・耐久や車体全体の実機耐荷重の保証ではありません。

- [D4の固定具・交換手順・電池候補・残る検証](cad/amr07/battery-drawer/README.ja.md)
- [電池固定具の接写](cad/amr07/battery-drawer/cad-screen-pack-retention.png) / [ガイドとフレーム締結](cad/amr07/battery-drawer/cad-screen-guide-mounting.png)
- [現行組立FCStd](cad/amr07/battery-drawer/AMR01_BatteryDrawer_D4.FCStd) / [STEP](cad/amr07/battery-drawer/AMR01_BatteryDrawer_D4.step)
- [現行BOM CSV](cad/amr07/battery-drawer/BOM.csv) / [小計と未確定項目](cad/amr07/battery-drawer/cost_summary.json)
- [電池用の交換印刷3部品](cad/amr07/battery-drawer/D4-battery-print-files.zip) / [検査・質量内訳](cad/amr07/battery-drawer/validation.json)
- [D3から継承する天板・加工図面・実見積](cad/amr07/aluminum-direct-deck/README.ja.md)
- [設計要件](cad/amr07/requirements.json) / [電源・停止・回生と試験仕様](cad/amr07/ELECTRICAL_AND_VALIDATION.ja.md)
- [モーター金具の実加工見積](cad/amr07/MACHINING_QUOTE.ja.md) / [キャスター調達](cad/amr07/CASTER_PROCUREMENT.ja.md)

再生成はFreeCAD Pythonで`cad/amr07/battery-drawer/build_d4.py`、通常のPythonで同フォルダの`build_bom.py`、FreeCAD GUIで`capture_screens.py`。保存後にFreeCAD Pythonで`validate_saved.py`、通常のPythonで`release.py`を実行します。旧D3の見積済み天板STEP/PDFは変更しません。電装設計と未選定品の留保は引き続き上記資料を参照してください。

## 比較履歴・共通資料

- [A5：5案の実加工費・強度比較](cad/amr06/README.ja.md) / [修正元の設計レビュー](cad/amr06/DESIGN_REVIEW_2026-09-21.ja.md)
- [A4：M0601C_111と専用低背金具](cad/amr05/README.ja.md)
- [メーカーCAD・モーター仕様・タイヤ交換](cad/amr05/M0601C_INTERFACE.ja.md)
- [実加工サイト見積のスキル](skills/cnc-quote/SKILL.md)
- [A3：DDSM115](cad/amr04/README.ja.md) / [A2：FIT0185](cad/amr03/README.ja.md)
- [第二案B・却下したベルト案C](cad/amr02/README.ja.md) / [第一案](cad/amr01/README.ja.md)
- [初期基礎設計書](docs/amr-01/DESIGN.ja.md) / [FreeCAD環境](cad/README.md)
