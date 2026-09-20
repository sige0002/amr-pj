# amr-pj — 家庭向け小型AMR / 将来MoMa

現行CADは**第一案改A3：DDSM115一体ホイール二輪＋後方キャスター**。Amazonの3030・300/400mm定尺と低床電池を維持し、FIT0185、継手、長い車軸、外付け軸受を置き換えた。ベルトと長い取付スペーサーは使わない。

走行余裕を優先したCAD採用候補で、**交換タイヤの確実な調達先・摩耗寿命・取付部の実荷重検証は未確認**。設計理由、費用、未解決事項を各レビューに記録する。

- [A3の説明・CAD・実画面](cad/amr04/README.ja.md)
- [部品表](cad/amr04/BOM.csv) / [費用集計](cad/amr04/cost_summary.json) / [費用の根拠](cad/amr04/COST_REVIEW.ja.md)
- [候補モーターの性能・費用・不採用理由](cad/amr04/MOTOR_COMPARISON.ja.md)
- [タイヤ摩耗・交換性](cad/amr04/TIRE_WEAR.ja.md) / [取付寸法の一次資料](cad/amr04/DDSM115_INTERFACE.ja.md)
- [金属マウントの独立レビュー](cad/amr04/MOUNT_REVIEW.ja.md)
- [電池・配線・整備空間](cad/amr04/ELECTRICAL_PACKAGING.ja.md)
- [形状・重量検査](cad/amr04/validation_results.json) / [駆動・静的支持・摩耗感度](cad/amr04/calculation_results.json)

| 設計条件・現行案 | 内容 |
|---|---|
| 主フレーム | MISUMI 3030、300/400mm定尺。組立460×300mm、純正接合HBLFSN6-SET |
| 台車質量 | 電池・電装込み10kg以下。現行推計7.09kg、実測前 |
| 荷物・将来アーム | 荷物2kgとアーム系2kgは別枠、最大構成14kgで選定計算 |
| 駆動 | DDSM115×2、100.7mmタイヤ、輪距349mm、後方50mm自在キャスター |
| 初期速度 | 0.15m/s、角速度0.3rad/s。実機条件の確認前 |
| 高さ | フレーム下面69mm、電池搭載面35mm、固定部最低地上高29mm |
| 骨格外形 | 460×407×109.6mm。完成配置目標500×420×180mm |
| PLA活用 | 低床電池クレードル、前後電装トレイ。主輪支持はt5金属部材 |

| 初期予算 | A3 |
|---|---:|
| 自加工：購入・材料・送料枠 | **47,824円** |
| 外注加工6,000円の未見積追加枠込み | **53,824円** |

モーター二輪・通信インターフェース込み。参考価格と未見積枠を含み、電池・充電器・主計算機・電源保護・非常停止回路・実配線・完成ガード・荷台・アームは別。純正金具の個人購入経路も未確定。タイヤ補修費を無料とは扱わず、適合部品の調達が確認できるまで寿命費用は未見積とする。

![DDSM115のA3・FreeCAD実画面](cad/amr04/cad-screen-isometric.png)

![下面の金属マウントと低床電池・FreeCAD実画面](cad/amr04/cad-screen-underside.png)

茶色の半透明箱は未選定電池の予約空間。CADは公称寸法による設計検討で、実部品の公差・変形・熱・寿命まで認定した完成機ではない。

## 再計算

```sh
python3 cad/amr04/calculate_cost.py
python3 cad/amr04/calculate_design.py
python3 cad/amr04/calculate_maintenance.py
python3 -m unittest discover -s cad/amr02 -p test_calculate_design.py -v
```

FreeCAD内での再生成は[A3 README](cad/amr04/README.ja.md)を参照。

## 比較履歴

- [第一案改A2：FIT0185・スペーサー撤去](cad/amr03/README.ja.md)
- [第二案B・却下したベルト案C](cad/amr02/README.ja.md)
- [元の第一案A](cad/amr01/README.ja.md)
- [第一案の基礎設計書](docs/amr-01/DESIGN.ja.md) / [同資料ZIP](archives/amr_v0_4_1.zip)
- [FreeCAD環境](cad/README.md)
