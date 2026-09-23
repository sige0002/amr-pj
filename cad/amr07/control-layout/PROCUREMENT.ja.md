# Amazon優先・送料込みの調達比較

2026-09-23確認。**Amazon発送品を中心に、同じ仕様で送料込みが下がるものを採用する。** 個別Prime会員・指定配送先での決済画面は未確認。商品ページにある「Amazon発送品3,500円以上の通常配送料無料」というまとめ買い条件を、今回のAmazon発送品合計が満たす前提で送料0を比較に用いた。Prime表示のない出品をPrime対応と断定しない。

| 対象 | 比較した価格（税込） | 選択と理由 |
|---|---:|---|
| 手持ちPico | 旧購入920円→0円 | 本体を流用。型番・ピン・付属線は未確認 |
| 同じIDEC非常停止 | 旧3,298円→[Amazon3,153円](https://www.amazon.co.jp/dp/B077Y8DN8G) | 同一XA1E-BV302R、145円減 |
| M4 OD12×t1座金 | 旧288＋送料390＝678円→[Amazon20枚430円](https://www.amazon.co.jp/dp/B0H8RT271F) | 248円減。内径・公差は受入確認 |
| 同じM4×16、60本 | [直販770＋385＝1,155円](https://store.onokatsu.co.jp/products/133-00-04)、[Amazon1,180円](https://www.amazon.co.jp/dp/B07BQDGT32) | 直販を維持、送料込みで25円安い |
| 純正BL1860B＋DC18RF | 既選定19,800＋送料600＝20,400円、Amazon単品15,190＋6,566＝21,756円 | 電池・充電器は既選定先を維持。互換電池との価格差で置換しない |
| ARMボタン | [赤3211 658円](https://www.amazon.co.jp/dp/B075SVHZBW)、[黒3212 835円](https://www.amazon.co.jp/dp/B075SQ41JN) | 停止操作との識別を優先し黒を選ぶ。差177円 |
| 主電源 | [amon3214 621円](https://www.amazon.co.jp/dp/B075SW22KP) | DC24V10Aの表示を確認。DC12V専用品は選ばない |
| M6×12、35本 | [Onokatsu1,180円/35本](https://www.amazon.co.jp/dp/B01N3BIIMO) | 2パック2,360円。旧BOMで未計上だった50本も含め計上 |
| M4ナット、20個 | [TRUSCO273円](https://www.amazon.co.jp/dp/B0BVQJS1D2) | 床・ストッパ・ケースで共用し、パック数を現行BOMで集計 |
| M6 OD18×t1、30枚 | [Onokatsu968円](https://www.amazon.co.jp/dp/B0DZVCSRXG) | ケース、追加ヒンジ取付、蝶ボルト座金へ共用。床梁のt1.6と混同しない |
| トルクヒンジ HG-TS15 | [Amazon1,172円×2＝2,344円](https://www.amazon.co.jp/dp/B007628W3W) | メーカーが保持トルク・公差を公開するものを選定 |
| 蝶ボルトM6×15、18個 | [TRUSCO B36-0615、527円](https://www.amazon.co.jp/dp/B002A5PVN4) | 使用2個。3mmの金属座金で溝への突出を調整。M6×12の別出品より購入額が低い |

同じ機能・仕様の変更で確定した節約は**920＋145＋248＝1,313円**。新設スイッチ、ケース、ヒンジ、ロックや、以前空欄だったねじ代の追加とは分ける。今回の小計増額をそのまま部品単価の値上がりとは扱わない。

直販送料は[Onokatsu利用ガイド](https://store.onokatsu.co.jp/pages/user-guide)の3,300円未満385円、北海道・沖縄900円を参照。指定配送先を入れた発注見積ではない。追加直販品をまとめる場合は送料を一度だけ再計上する。

## 記録と未確定分

- [操作部・締結材の価格記録](amazon_observations.json)と[evidenceフォルダ](evidence/)に、実商品ページの品名・価格部分を保存した。配送先やアカウント情報は保存していない。
- [ヒンジ価格](hinge_amazon_observations.json)／[ロック価格](lock_amazon_observations.json)。数量は使用数で按分せず、購入パック全額で比較する。
- 現行の使用数と購入数は[開閉天板版BOM](../hinged-deck/BOM.ja.md)。[CSV](../hinged-deck/BOM.csv)と[全明細Markdown](../hinged-deck/BOM-details.ja.md)を同じデータから生成する。
- [既製モジュール／実装外注比較](ELECTRONICS_OPTIONS.ja.md)。保護回路基板や端子、主計算機は未選定・未見積であり、空欄は0円を意味しない。
