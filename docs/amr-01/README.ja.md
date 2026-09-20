# AMR-01 v0.4.1

家庭向けの小型AMRから将来MoMaへ進むための概念設計。Amazonで購入するミスミNFSL6-3030の300mm・400mm材を採用。組立案460×300mm、車輪込み外形500×400mmは配置目標。材料代は各4本入り1組ずつで税込3,419円（確認時点、金具・送料等別）。台車自重の上限は10kg、運搬物2kg（アーム自重とは別）。アーム系は合計2kg以内を仮の拡張枠とする。アームが持ち上げる物体質量は未確定。

**外観を整えるための外装は不要。内部構造と実装を優先し、安全上必要な局所カバーは残す。生成概念画像は不正確なため公開・同梱しない。最新の依頼による実CAD画面はリポジトリへ保存する。**

まず`DESIGN.ja.md`を読む。このZIPは設計書と計算のみ。第一案CAD、部品表、実CAD画面は[GitHubのcad/amr01](https://github.com/sige0002/amr-pj/tree/main/cad/amr01)に別置。実機制御コードは含まない。

機械骨格の支出目安は自加工34,159円／外注加工枠込み40,159円。電装等は別。骨格約4.73kg＋電装等予算2.05kg＝約6.78kgで、上限10kgまで約3.22kgの余裕がある。FIT0185の連続定格は未確認で、低速試験用の第一案とする。

## 再計算

Python 3.10以降。追加パッケージは不要。

```bash
cd amr_v0_4_1
python3 check_design.py
python3 -m unittest -v test_check_design.py
```

`check_design.py`は同じフォルダーの`design_parameters.json`を読み、同じフォルダーの`calculation_results.json`を更新する。任意の作業ディレクトリからも実行できる。

```bash
python3 check_design.py --config design_parameters.json --output results_trial.json
```

入力の寸法はキーの`_mm`、内部の重心計算はmで扱う。荷物の上限とアーム系の重量は別管理する。`arm_object_lifting_limit_kg: null`は未確定を示し、0kgという意味ではない。

定尺・本数から組立外寸と購入数量を照合し、予備材込みの購入費と実使用材の機体質量を分けて出力する。3030と4040の梁単体の比較も含む。

静的計算の`operation_approved`は常に`false`。支持余裕が正でも、強度・制動・全姿勢・動力学を検証したことにはならない。`static_moment_ratio: null`はその計算姿勢で転倒側モーメントがゼロであることを示し、安全認定ではない。

テストは計算と入力制約の確認のみ。物理機体の安全性、部品の入手性、家庭での運用可否は保証しない。変更後は設計書・変更履歴も更新する。
