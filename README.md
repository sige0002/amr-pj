# amr-pj — 家庭向け小型AMR / 将来MoMa

現行CADは**第一案改A4：M0601C_111二輪＋後方キャスター**。Amazonの3030・300/400mm定尺、元のフレーム配置、低床電池を維持する。公開ブラケットのモーター受け形状を基に、3030下面へ直接留める一体の金属金具を設計した。

既製ブラケットは公開SLDPRTの保存メッシュで配置を比較し、現在のレールとの干渉を確認した。専用金具の実STEP・寸法図をJLCCNCへ投入し、2個の自動見積を取得した。加工先の正式審査、購入ロットとのはめあい、実荷重・寿命は未確認。

- [A4の設計・CAD・実画面](cad/amr05/README.ja.md)
- [車体FCStd](cad/amr05/AMR01_M0601C_A4.FCStd) / [車体STEP](cad/amr05/AMR01_M0601C_A4.step)
- [金具の見積用STEP](cad/amr05/M0601C_custom_mount_quote.step) / [寸法図PDF](cad/amr05/M0601C_custom_mount_quote.pdf) / [加工依頼仕様](cad/amr05/MANUFACTURING_RFQ.ja.md)
- [BOM](cad/amr05/BOM.csv) / [費用の根拠と比較](cad/amr05/COST_REVIEW.ja.md) / [費用集計](cad/amr05/cost_summary.json)
- [加工サイトの実見積・画面・条件](cad/amr05/MACHINING_QUOTE.ja.md)
- [同じ方法で加工見積を取得するCodexスキル](skills/cnc-quote/SKILL.md)
- [金具の独立レビュー](cad/amr05/MOUNT_REVIEW.ja.md) / [公開CADの抽出根拠](cad/amr05/BRACKET_SOURCE_REVIEW.ja.md)
- [本体・タイヤ・交換](cad/amr05/M0601C_INTERFACE.ja.md) / [電池・配線・整備空間](cad/amr05/ELECTRICAL_PACKAGING.ja.md)

| 設計条件・現行案 | 内容 |
|---|---|
| 主フレーム | 3030・400mm×4本＋300mm×2本、外形460×300mm、純正接合HBLFSN6-SET |
| 台車質量 | 電池・電装込み10kg以下。推計6.79kg、未実測 |
| 荷物・将来アーム | 荷物2kgとアーム系2kgは別枠、最大構成14kgで選定計算 |
| 駆動 | M0601C_111×2、100.7mm適合タイヤ、後方50mm自在キャスター |
| 取付金具 | A6061-T6候補、90×30×34mm、同形2個。一体CNC加工の見積候補 |
| 高さ | フレーム下面69mm、金具35mm、固定骨格最低32mm。配線予約は約28.35mm |
| 骨格外形 | 仮のタイヤ組付け位置で460×406.6×109.6mm、輪距349mm |
| PLA活用 | 低床電池クレードルと前後トレイ。主輪支持は金属 |
| 配置検査 | 161部品・12,880ペアで公称体積干渉なし。工具軸・配線・整備空間も別検査 |

**費用は途中小計42,282円＋専用金具と送料のサイト自動見積81.73 USD＋残る未確定分。** Taobao本体約7,000円/個、適合タイヤ2個を別購入する仮定。タイヤと必要付属品の同梱を確認できれば円小計33,042円。JLCCNCの製造10日・金具2個74.50 USD＋日本宛OCS送料7.23 USDを原通貨で計上した。図面審査後の価格、税・住所別送料・決済換算、Taobao諸費は未確定。共通板材を自加工する条件で、板材も外注する場合は追加見積。電池・主計算機・電源保護・実配線等は別予算であり、完成機総額ではない。

![M0601C_111のA4・FreeCAD実画面](cad/amr05/cad-screen-underside.png)

![専用金属金具・FreeCAD実画面](cad/amr05/cad-screen-drive-module.png)

茶色の半透明箱は未選定電池の予約空間。本体は販売元案内のSTEP、タイヤとカバーは公開外形の簡略形状。タイヤの軸方向組付け位置が未確認のため全幅・輪距は暫定。公称CADの合格は、製作公差・衝撃・熱・寿命の認定ではない。

## 再計算

```sh
python3 cad/amr05/fetch_vendor_cad.py
python3 cad/amr05/calculate_cost.py --require-cad --self-test
python3 cad/amr05/calculate_design.py
```

FreeCADでの再生成は[A4 README](cad/amr05/README.ja.md)を参照。

## 比較履歴

- [A3：DDSM115・一体ホイール検討](cad/amr04/README.ja.md)
- [A2：FIT0185・スペーサー撤去](cad/amr03/README.ja.md)
- [第二案B・却下したベルト案C](cad/amr02/README.ja.md)
- [元の第一案A](cad/amr01/README.ja.md)
- [第一案の基礎設計書](docs/amr-01/DESIGN.ja.md) / [同資料ZIP](archives/amr_v0_4_1.zip)
- [FreeCAD環境](cad/README.md)
