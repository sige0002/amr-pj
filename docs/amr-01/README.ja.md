# AMR-01 v0.2.1

家庭向けの小型AMRから将来MoMaへ進むための概念設計。外形350×280mm、台車目標5kg・上限6kg、運搬物2kg（アーム自重とは別）。アーム系は合計2kg以内を仮の拡張枠とする。アームが持ち上げる物体質量は未確定。

**外装の意匠・化粧カバー・装飾は不要。内部構造を優先する。** 巻き込み防止・電装接触保護等の機能ガードは別扱いで残す。

まず[設計書](DESIGN.ja.md)を読む。内部構造図は概念イメージであり、本文と入力パラメータを優先する。製作CAD、確定部品表、実機制御コードは含まない。

## 再計算

Python 3.10以降。追加パッケージは不要。

```bash
cd docs/amr-01  # ZIP展開後は cd amr_v0_2_1
python3 check_design.py
python3 -m unittest -v test_check_design.py
```

`check_design.py`は同じフォルダーの`design_parameters.json`を読み、同じフォルダーの`calculation_results.json`を更新する。任意の作業ディレクトリからも実行できる。

```bash
python3 check_design.py --config design_parameters.json --output results_trial.json
```

入力の寸法はキーの`_mm`、内部の重心計算はmで扱う。荷物の上限とアーム系の重量は別管理する。`arm_object_lifting_limit_kg: null`は未確定を示し、0kgという意味ではない。

静的計算の`operation_approved`は常に`false`。支持余裕が正でも、強度・制動・全姿勢・動力学を検証したことにはならない。`static_moment_ratio: null`はその計算姿勢で転倒側モーメントがゼロであることを示し、安全認定ではない。

テストは計算と入力制約の確認のみ。物理機体の安全性、部品の入手性、家庭での運用可否は保証しない。変更後は設計書・変更履歴も更新する。
