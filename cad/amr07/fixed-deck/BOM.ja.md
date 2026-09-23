# D6.9 BOM（最小手動走行構成E2.1）

**まず手動で走る・止める・非常停止で給電を切る構成。通信・非常停止部品の型番と配線は未確定です。** [最小構成](../electrical-buildability/README.ja.md)。

**途中小計 90,562円相当＋未計上分**。原通貨：71,548円＋120.90 USD。

[全明細Markdown](BOM-details.ja.md) ／ [CSV](BOM.csv) ／ [加工見積の証拠](MACHINING_QUOTE.ja.md)

旧専用回路部品とはんだ端子の非常停止、計6,519円を[価格履歴](../electrical-buildability/withdrawn-parts.ja.md)へ移しました。代替完成品・ハーネス等は未計上なので、この減額は節約ではありません。割合も完成車の費用割合ではありません。

E2ではARM・別の主スイッチ計1,456円と、追加監視等を初回必須から外しました。[条件付き・後工程の部品](../electrical-buildability/deferred-parts.ja.md)は下の必須未計上品へ混ぜていません。

円換算は記録済みの2026-09-21参考値1 USD＝157.2672円。現在の決済額ではありません。購入パック全額を計上し、余りを按分していません。車載LinuxミニPC・給電部材・USB–RS485変換器・非常停止・配線などは未計上、モーター14,000円とUSB線500円は仮予算、PLAは材料消費の参考です。計算機は初回から車載するLinuxミニPCを想定し、Raspberry Pi 5には固定していません。

機械部分はヒンジ案D6.8から約15,663円減。ヒンジ・専用L金具・蝶ボルト等の購入を削除。M6固定6点は既計上パックの余りを使い、新規パック購入なし。天板は同一形状のD3実自動見積を再使用し、今回の価格再取得はしていません。

| 部位 | 円換算参考 | 計上済み分の割合 |
|---|---:|---:|
| 電池・充電器・アダプター | 23,380円 | 25.8% |
| フレーム・締結材・共通送料 | 20,000円 | 22.1% |
| モーター | 14,000円 | 15.5% |
| モーター専用金具 | 12,935円 | 14.3% |
| タイヤ・キャスター | 10,413円 | 11.5% |
| 天板（固定ボルトは共通締結材） | 6,078円 | 6.7% |
| PLA・ベルト | 3,255円 | 3.6% |
| 操作部・USB線（電装主要部は未計上） | 500円 | 0.6% |

Amazonを優先。Prime会員としての最終配送条件は未確認です。既存価格は確認日と仮枠の区別を各明細に残しています。6点固定はM6×12・HNTT6-6を各6個使い、両側から荷台を保持します。

## 電池・充電器・アダプター

| 部品 | 使用／購入 | 原通貨金額 |
|---|---|---:|
| [純正電池＋急速充電器](BOM-details.ja.md#item-power_kit) | 1／1 式 | 19800 JPY |
| [電池・充電器セット送料](BOM-details.ja.md#item-power_kit_ship) | 1／1 式 | 600 JPY |
| [電池出力アダプター](BOM-details.ja.md#item-power_adapter) | 1／1 式 | 2180 JPY |
| [アダプター送料](BOM-details.ja.md#item-power_adapter_ship) | 1／1 式 | 800 JPY |

## フレーム・締結材・共通送料

| 部品 | 使用／購入 | 原通貨金額 |
|---|---|---:|
| [3030フレーム 400mm](BOM-details.ja.md#item-f01) | 4／4 本 | 1952 JPY |
| [3030フレーム 300mm](BOM-details.ja.md#item-f02) | 4／4 本 | 1467 JPY |
| [基礎部の追加ねじ・ナット・座金](BOM-details.ja.md#item-h01) | 1／未定 式 | 2300 JPY |
| [モーター座面用小径平座金](BOM-details.ja.md#item-mw) | 6／10 枚 | 319.0 JPY |
| [フレーム・残存素材の追加送料枠](BOM-details.ja.md#item-s03) | 1／未定 式 | 1000 JPY |
| [純正接合部・溝ナットの送料枠](BOM-details.ja.md#item-s04) | 1／未定 式 | 未計上 |
| [Taobao送料・輸入諸費](BOM-details.ja.md#item-s07) | 1／未定 式 | 未計上 |
| [純正反転ブラケット本体](BOM-details.ja.md#item-f03) | 20／20 個 | 1834 JPY |
| [車体全体の先入れ溝ナット](BOM-details.ja.md#item-f04) | 70／100 個 | 5112 JPY |
| [ブラケット・天板固定ボルト](BOM-details.ja.md#item-d3_m6) | 50／70 個 | 2360 JPY |
| [印刷ストッパ固定ねじ](BOM-details.ja.md#item-d3_stop_bolts) | 8／未定 個 | 未計上 |
| [ストッパ・床継ぎ目用ナット](BOM-details.ja.md#item-d3_stop_nuts) | 28／40 個 | 546 JPY |
| [ストッパ用座金](BOM-details.ja.md#item-d3_stop_washers) | 8／未定 枚 | 未計上 |
| [荷物固定ベルト送料参考](BOM-details.ja.md#item-d3_strap_ship) | 1／未定 個 | 600 JPY |
| [100mm溝付き支柱4本](BOM-details.ja.md#item-d6_posts) | 4／4 本 | 495 JPY |
| [床・ケース用M4×16](BOM-details.ja.md#item-d62_floor_screws) | 20／60 個 | 770 JPY |
| [継ぎ目支持梁端の大径平座金](BOM-details.ja.md#item-d62_beam_washers) | 4／未定 個 | 未計上 |
| [床・ケース用M4 OD12×t1座金](BOM-details.ja.md#item-d64_floor_washers) | 24／40 枚 | 860 JPY |
| [中央ねじ・座金の別店舗送料](BOM-details.ja.md#item-d64_fastener_ship) | 1／1 式 | 385 JPY |

## モーター

| 部品 | 使用／購入 | 原通貨金額 |
|---|---|---:|
| [ダイレクトドライブモーター](BOM-details.ja.md#item-d01) | 2／2 個 | 14000 JPY |

## モーター専用金具

| 部品 | 使用／購入 | 原通貨金額 |
|---|---|---:|
| [A6-R1専用モーター金具](BOM-details.ja.md#item-q01) | 2／2 個 | 75.02 USD |
| [CNC日本宛送料](BOM-details.ja.md#item-s08) | 1／未定 式 | 7.23 USD |

## タイヤ・キャスター

| 部品 | 使用／購入 | 原通貨金額 |
|---|---|---:|
| [タイヤ・カバーキット](BOM-details.ja.md#item-d02) | 2／2 キット | 9240 JPY |
| [自在キャスター](BOM-details.ja.md#item-c01) | 1／1 個 | 273 JPY |
| [キャスター取付板の素材](BOM-details.ja.md#item-p01) | 1／未定 枚 | 900 JPY |
| [キャスター送料](BOM-details.ja.md#item-s02) | 1／未定 式 | 0 JPY |
| [タイヤ国内通常送料](BOM-details.ja.md#item-s06) | 1／未定 式 | 0 JPY |

## 天板（固定ボルトは共通締結材）

| 部品 | 使用／購入 | 原通貨金額 |
|---|---|---:|
| [固定式格子穴アルミ天板](BOM-details.ja.md#item-deck_plate) | 1／1 枚 | 28.67 USD |
| [アルミ天板1枚の日本宛送料](BOM-details.ja.md#item-deck_cnc_ship) | 1／未定 個 | 9.98 USD |

## PLA・ベルト

| 部品 | 使用／購入 | 原通貨金額 |
|---|---|---:|
| [床・PCカバー・荷物止め・操作ケース](BOM-details.ja.md#item-p04) | 888／0 g | 1776 JPY |
| [電池モジュール保持ベルト](BOM-details.ja.md#item-h02) | 1／1 本 | 393 JPY |
| [荷物固定ベルト](BOM-details.ja.md#item-deck_cargo_straps) | 2／2 本 | 786 JPY |
| [ベルト接触部の保護材・余長固定](BOM-details.ja.md#item-deck_edge_protection_and_slack_retention) | 1／未定 式 | 300 JPY |
| [電池・電装の軟質当て材](BOM-details.ja.md#item-power_pads) | 1／1 式 | 未計上 |
| [1階計算機・監視回路の保持ベルト](BOM-details.ja.md#item-power_low_straps) | 2／未定 本 | 未計上 |

## 操作部・USB線（電装主要部は未計上）

| 部品 | 使用／購入 | 原通貨金額 |
|---|---|---:|
| [通信変換器用USBデータケーブル](BOM-details.ja.md#item-e02) | 1／未定 本 | 500 JPY |

## 未計上品

| 部品 | 状態 |
|---|---|
| 純正接合部・溝ナットの送料枠 | 送料未確定 |
| Taobao送料・輸入諸費 | 未見積 |
| 印刷ストッパ固定ねじ | 寸法選定済・実機検証前 |
| ストッパ用座金 | 寸法選定済・実機検証前 |
| 電池・電装の軟質当て材 | 型式選定・現物／電気検証前 |
| 1階計算機・監視回路の保持ベルト | 型式選定・現物／電気検証前 |
| 継ぎ目支持梁端の大径平座金 | 寸法選定済・購入パック未確定 |
| 車載LinuxミニPC・記憶媒体・必要な冷却 | 車載Linux機を使用、機種と価格は未確定 |
| 車載LinuxミニPC用の給電部材 | 初回必須、型番・価格未確定 |
| 電源着脱・分岐コネクタ | 走行台車／未選定 |
| ヒューズ・ホルダー | 走行台車／未選定 |
| 完成済みUSB–RS485変換器 | 完成品構成へ再選定・未計上 |
| 端末加工済み電源・信号ハーネス | 完成品構成へ再選定・未計上 |
| 電装固定板・ケース・スタンドオフ | 走行台車／未選定 |
| 未確定送料・税・決済換算 | 走行台車／未選定 |
| 加工工具・作業費・残る自加工品の外注費 | 走行台車／未選定 |
| PLA仮合わせモックの材料消費 | 製作補助／未選定 |
| 荷物容器・敷板 | 積載物／未選定 |
| 非常停止スイッチ（配線加工不要品） | 完成品構成へ再選定・未計上 |

[設計と組立手順](README.ja.md) ／ [重量・強度の比較計算](PAYLOAD_REVIEW.ja.md)
