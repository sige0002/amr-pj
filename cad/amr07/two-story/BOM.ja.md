# D6.5 BOM：費用の内訳と購入リスト

**[全明細をMarkdownで読む](BOM-details.ja.md) ／ [CSVを開く・保存する](BOM.csv)**

**途中小計 約93,249円 ＋ 未計上分**。通常積載目標10kg、車体推計10.068kg（10kgは目安）の現行構成。

**主計算機・その電源・配線／基板／ケース・追加ねじなどは未計上。LiDARやカメラ等の将来センサーも含まない。** 完成車の総額ではない。

## どこに費用がかかるか

| 部位 | 金額の目安 | 割合 |
|---|---:|---:|
| 電池・充電器・アダプター | 23,380円 | 25.1% |
| フレーム・締結材 | 14,679円 | 15.7% |
| モーター2個 | 14,000円 | 15.0% |
| 専用モーター金具2個 | 12,935円 | 13.9% |
| タイヤ・キャスター | 10,413円 | 11.2% |
| 制御・電源保護 | 7,019円 | 7.5% |
| アルミ天板 | 6,078円 | 6.5% |
| PLA・ベルト・保護材 | 2,759円 | 3.0% |
| その他送料 | 1,985円 | 2.1% |
| **途中小計** | **93,249円** | **100%** |

割合の分母は計上済み小計。未計上品を0円とは扱わない。円換算は記録済みの1 USD＝157.2672円（2026-09-21参考値）で、現在の決済レートではない。元の小計は74,235円＋120.90 USD。行ごとの四捨五入で端数差が出る。

電池・モーター金具・天板の欄には、それぞれ記録された送料を含む。共通送料は「その他送料」へ置き、二重計上しない。購入パック全額で集計し、使用数による按分はしていない。

## 金額の確かさ

| 根拠 | 計上額 |
|---|---:|
| 価格記録 | 53,955円 |
| 自動見積 | 19,014円 |
| 仮予算 | 19,000円 |
| 材料消費 | 1,280円 |
| 手持ち流用 | 0円 |

価格記録は既存の販売ページ確認・引継価格。自動見積はJLCCNCの実サイト記録で、未発注・担当者審査前。**モーター14,000円は仮予算**。PLA1280円は材料消費参考で、新規スプールの購入額ではない。

Pico本体はユーザー所有のため購入0円。型番・ピン有無・USB線の所有までは未確認。[既製モジュールと専用基板の比較](../control-layout/ELECTRONICS_OPTIONS.ja.md)／[Amazonと送料込み比較](../control-layout/PROCUREMENT.ja.md)。

## 購入リスト

「使用／購入」は使用数と買う数で、購入予定数が未確定の項目は未定と表示する。品名から購入先、各品目の「仕様・備考」から型番・購入単位・価格根拠などの[全明細Markdown](BOM-details.ja.md)を開ける。同じ内容の[CSV](BOM.csv)も用意している。

### 電池・充電器・アダプター — 23,380円

| 品目 | 使用／購入 | 金額 | 根拠 |
|---|---|---:|---|
| [BL1860B電池＋DC18RF充電器](https://store.shopping.yahoo.co.jp/takahashihonsha/0088381464031-0088381523394-s.html)<br>[POWER_KIT・仕様・備考](BOM-details.ja.md#item-power_kit) | 1式／1式 | 19,800円 | 価格記録 |
| [電池・充電器セット送料](https://store.shopping.yahoo.co.jp/takahashihonsha/0088381464031-0088381523394-s.html)<br>[POWER_KIT_SHIP・仕様・備考](BOM-details.ja.md#item-power_kit_ship) | 送料1式 | 600円 | 価格記録 |
| [電池アダプター diy-adapter03](https://store.shopping.yahoo.co.jp/netkey-store/diy-adapter03.html)<br>[POWER_ADAPTER・仕様・備考](BOM-details.ja.md#item-power_adapter) | 1式／1式 | 2,180円 | 価格記録 |
| [アダプター送料](https://store.shopping.yahoo.co.jp/netkey-store/diy-adapter03.html)<br>[POWER_ADAPTER_SHIP・仕様・備考](BOM-details.ja.md#item-power_adapter_ship) | 送料1式 | 800円 | 価格記録 |

### フレーム・締結材 — 14,679円

| 品目 | 使用／購入 | 金額 | 根拠 |
|---|---|---:|---|
| [3030フレーム 400mm](https://www.amazon.co.jp/dp/B0DKF2CCW3)<br>[F01・仕様・備考](BOM-details.ja.md#item-f01) | 4本／4本 | 1,952円 | 価格記録 |
| [3030フレーム 300mm](https://www.amazon.co.jp/dp/B0DKDZ8G9G)<br>[F02・仕様・備考](BOM-details.ja.md#item-f02) | 4本／4本 | 1,467円 | 価格記録 |
| [3030支柱 100mm](https://www.amazon.co.jp/dp/B0CB5N6ZJJ)<br>[D6_POSTS・仕様・備考](BOM-details.ja.md#item-d6_posts) | 4本／4本 | 495円 | 価格記録 |
| [接合金具 HBLFSN6](https://www.amazon.co.jp/dp/B0DKF1FCD6)<br>[F03・仕様・備考](BOM-details.ja.md#item-f03) | 20個／20個 | 1,834円 | 価格記録 |
| [溝ナット HNTT6-6](https://www.amazon.co.jp/dp/B0DK9C99YH)<br>[F04・仕様・備考](BOM-details.ja.md#item-f04) | 70個／100個 | 5,112円 | 価格記録 |
| 基礎部の追加ねじ・ナット・座金<br>[H01・仕様・備考](BOM-details.ja.md#item-h01) | 1式／未定 | 2,300円 | 仮予算 |
| [モーター座面用小径平座金](https://wilco.jp/products/F/FW-EB.html)<br>[MW・仕様・備考](BOM-details.ja.md#item-mw) | 6枚／10枚 | 319円 | 価格記録 |
| ブラケット・天板固定ボルト<br>[D3_M6・仕様・備考](BOM-details.ja.md#item-d3_m6) | 50個／未定 | 未計上 | 未計上 |
| 印刷ストッパ固定ねじ<br>[D3_STOP_BOLTS・仕様・備考](BOM-details.ja.md#item-d3_stop_bolts) | 8個／未定 | 未計上 | 未計上 |
| ストッパ・床継ぎ目用ナット<br>[D3_STOP_NUTS・仕様・備考](BOM-details.ja.md#item-d3_stop_nuts) | 12個／未定 | 未計上 | 未計上 |
| ストッパ用座金<br>[D3_STOP_WASHERS・仕様・備考](BOM-details.ja.md#item-d3_stop_washers) | 8枚／未定 | 未計上 | 未計上 |
| [床継ぎ目の通常六角穴付きねじ](https://store.onokatsu.co.jp/products/133-00-04)<br>[D62_FLOOR_SCREWS・仕様・備考](BOM-details.ja.md#item-d62_floor_screws) | 4個／60個 | 770円 | 価格記録 |
| 継ぎ目支持梁端の大径平座金<br>[D62_BEAM_WASHERS・仕様・備考](BOM-details.ja.md#item-d62_beam_washers) | 4個／未定 | 未計上 | 未計上 |
| [床継ぎ目の上下大径平座金](https://www.amazon.co.jp/dp/B0H8RT271F)<br>[D64_FLOOR_WASHERS・仕様・備考](BOM-details.ja.md#item-d64_floor_washers) | 8枚／20枚 | 430円 | 価格記録 |

### モーター2個 — 14,000円

| 品目 | 使用／購入 | 金額 | 根拠 |
|---|---|---:|---|
| M0601C_111 モーター<br>[D01・仕様・備考](BOM-details.ja.md#item-d01) | 2個／2個 | 14,000円 | 仮予算 |

### 専用モーター金具2個 — 12,935円

| 品目 | 使用／購入 | 金額 | 根拠 |
|---|---|---:|---|
| [専用モーター金具 A6-R1](https://jlccnc.com/jp/cnc-machining-quote)<br>[Q01・仕様・備考](BOM-details.ja.md#item-q01) | 2個／2個 | 11,798円（$75.02） | 自動見積 |
| [CNC日本宛送料](https://jlccnc.com/jp/cnc-machining-quote)<br>[S08・仕様・備考](BOM-details.ja.md#item-s08) | 送料1式 | 1,137円（$7.23） | 自動見積 |

### タイヤ・キャスター — 10,413円

| 品目 | 使用／購入 | 金額 | 根拠 |
|---|---|---:|---|
| [タイヤキット DDT-M0601C-TIRE](https://www.switch-science.com/products/9203)<br>[D02・仕様・備考](BOM-details.ja.md#item-d02) | 2キット／2キット | 9,240円 | 価格記録 |
| [キャスター TYG-50](https://www.amazon.co.jp/dp/B0795CNFLR)<br>[C01・仕様・備考](BOM-details.ja.md#item-c01) | 1個／1個 | 273円 | 価格記録 |
| キャスター取付板の素材<br>[P01・仕様・備考](BOM-details.ja.md#item-p01) | 1枚／未定 | 900円 | 仮予算 |
| [キャスター送料](https://www.aboutamazon.jp/news/guide/answer-to-7-questions-about-shopping-at-amazon)<br>[S02・仕様・備考](BOM-details.ja.md#item-s02) | 送料1式 | 0円 | 価格記録 |
| [タイヤ国内通常送料](https://www.switch-science.com/policies/shipping-policy)<br>[S06・仕様・備考](BOM-details.ja.md#item-s06) | 送料1式 | 0円 | 価格記録 |

### 制御・電源保護 — 7,019円

| 品目 | 使用／購入 | 金額 | 根拠 |
|---|---|---:|---|
| Pico接続用USBデータケーブル<br>[E02・仕様・備考](BOM-details.ja.md#item-e02) | 1本／未定 | 500円 | 仮予算 |
| [非常停止スイッチ](https://www.amazon.co.jp/dp/B077Y8DN8G)<br>[ELEC_S1・仕様・備考](BOM-details.ja.md#item-elec_s1) | 1個／1個 | 3,153円 | 価格記録 |
| [駆動電源遮断リレー](https://jp.rs-online.com/web/p/power-relays/0369466)<br>[ELEC_K1_K2・仕様・備考](BOM-details.ja.md#item-elec_k1_k2) | 2個／2個 | 770円 | 価格記録 |
| 手持ちRaspberry Pi Pico<br>[ELEC_U1・仕様・備考](BOM-details.ja.md#item-elec_u1) | 1個／0個 | 0円 | 手持ち流用 |
| [外部ウォッチドッグIC](https://eleshop.jp/shop/g/gT11488/)<br>[ELEC_U2・仕様・備考](BOM-details.ja.md#item-elec_u2) | 1個／1個 | 140円 | 価格記録 |
| [手動再始動ラッチIC](https://eleshop.jp/shop/g/gT11476/)<br>[ELEC_U3・仕様・備考](BOM-details.ja.md#item-elec_u3) | 1個／1個 | 33円 | 価格記録 |
| [監視回路用DC/DC](https://akizukidenshi.com/catalog/g/g113536/)<br>[ELEC_PS1・仕様・備考](BOM-details.ja.md#item-elec_ps1) | 1個／1個 | 850円 | 価格記録 |
| [RS485トランシーバIC](https://akizukidenshi.com/catalog/g/g116211/)<br>[ELEC_U4・仕様・備考](BOM-details.ja.md#item-elec_u4) | 1個／1個 | 70円 | 価格記録 |
| [回生吸収抵抗](https://www.monotaro.com/g/02255191/)<br>[ELEC_RDUMP・仕様・備考](BOM-details.ja.md#item-elec_rdump) | 1個／1個 | 1,033円 | 価格記録 |
| [クランプ比較器](https://akizukidenshi.com/catalog/g/g116987/)<br>[ELEC_U5・仕様・備考](BOM-details.ja.md#item-elec_u5) | 1個／1個 | 30円 | 価格記録 |
| [クランプ基準電圧IC](https://akizukidenshi.com/catalog/g/g112018/)<br>[ELEC_U6・仕様・備考](BOM-details.ja.md#item-elec_u6) | 1個／1個 | 20円 | 価格記録 |
| [クランプMOSFET](https://akizukidenshi.com/catalog/g/g102414/)<br>[ELEC_QCLAMP・仕様・備考](BOM-details.ja.md#item-elec_qclamp) | 1個／1個 | 100円 | 価格記録 |
| [クランプ制御用レギュレータ](https://akizukidenshi.com/catalog/g/g113464/)<br>[ELEC_PS2・仕様・備考](BOM-details.ja.md#item-elec_ps2) | 1個／1個 | 20円 | 価格記録 |
| [電池への逆流防止ダイオード](https://akizukidenshi.com/catalog/g/g116378/)<br>[ELEC_D0・仕様・備考](BOM-details.ja.md#item-elec_d0) | 1個／10個 | 300円 | 価格記録 |

### アルミ天板 — 6,078円

| 品目 | 使用／購入 | 金額 | 根拠 |
|---|---|---:|---|
| [格子穴天板 300×300×4mm](https://jlccnc.com/jp/cnc-machining-quote)<br>[DECK_plate・仕様・備考](BOM-details.ja.md#item-deck_plate) | 1枚／1枚 | 4,509円（$28.67） | 自動見積 |
| [D3天板 日本宛UPS表示送料](https://jlccnc.com/jp/cnc-machining-quote)<br>[DECK_CNC_SHIP・仕様・備考](BOM-details.ja.md#item-deck_cnc_ship) | 送料1式 | 1,570円（$9.98） | 自動見積 |

### PLA・ベルト・保護材 — 2,759円

| 品目 | 使用／購入 | 金額 | 根拠 |
|---|---|---:|---|
| 四隅まで覆うリブ付き床4枚・継ぎ目支持梁1個・PC金属接触防止カバー1個・荷物ストッパ4個<br>[P04・仕様・備考](BOM-details.ja.md#item-p04) | 消費640g | 1,280円 | 材料消費 |
| [電池モジュール保持ベルト](https://store.shopping.yahoo.co.jp/hcbrico/4977292226752.html)<br>[H02・仕様・備考](BOM-details.ja.md#item-h02) | 1本／1本 | 393円 | 価格記録 |
| [荷物固定ベルト](https://store.shopping.yahoo.co.jp/hcbrico/4977292226752.html)<br>[DECK_cargo_straps・仕様・備考](BOM-details.ja.md#item-deck_cargo_straps) | 2本／2本 | 786円 | 価格記録 |
| ベルト接触部の保護材・余長固定<br>[DECK_edge_protection_and_slack_retention・仕様・備考](BOM-details.ja.md#item-deck_edge_protection_and_slack_retention) | 1式／未定 | 300円 | 仮予算 |
| 電池・電装の軟質当て材<br>[POWER_PADS・仕様・備考](BOM-details.ja.md#item-power_pads) | 1式／1式 | 未計上 | 未計上 |
| 1階計算機・監視回路の保持ベルト<br>[POWER_LOW_STRAPS・仕様・備考](BOM-details.ja.md#item-power_low_straps) | 2本／未定 | 未計上 | 未計上 |

### その他送料 — 1,985円

| 品目 | 使用／購入 | 金額 | 根拠 |
|---|---|---:|---|
| フレーム・残存素材の追加送料枠<br>[S03・仕様・備考](BOM-details.ja.md#item-s03) | 送料1式 | 1,000円 | 仮予算 |
| 荷物固定ベルト送料参考<br>[D3_STRAP_SHIP・仕様・備考](BOM-details.ja.md#item-d3_strap_ship) | 送料1式 | 600円 | 価格記録 |
| 純正接合部・溝ナットの送料枠<br>[S04・仕様・備考](BOM-details.ja.md#item-s04) | 送料1式 | 未計上 | 未計上 |
| Taobao送料・輸入諸費<br>[S07・仕様・備考](BOM-details.ja.md#item-s07) | 送料1式 | 未計上 | 未計上 |
| [中央ねじ・座金の別店舗送料](https://store.onokatsu.co.jp/pages/user-guide)<br>[D64_FASTENER_SHIP・仕様・備考](BOM-details.ja.md#item-d64_fastener_ship) | 送料1式 | 385円 | 価格記録 |

**機械基礎D6.5では、金属接触を防ぐPLAカバー1個を追加。追加金属部品・加工なし、PLA材料消費参考は76円増。** 機種別の基板ケース／絶縁スペーサーは未選定・未計上。[カバーと取付条件](../two-story/COMPUTER_BARRIER.ja.md)。

**履歴：D6.4では中央4本を通常のM4×16に変更し、上下のOD12座金を計8枚にした。** 新たな物理部品は上側座金4枚、下側4枚は交換。ねじ60本770円・座金50枚288円・2店舗送料参考775円、合計1833円を購入パック全額で計上した。使用する4本＋8枚の按分参考は約97円だが、購入額には使わない。従来の中央ねじ代は未計上だったため、旧ねじ代を差し引いた節約額は作らない。PLA材料消費参考は前版より6円増。

D6.4の上記価格は変更履歴。現行の購入先・金額・パック数は上表と明細を参照。上記送料は北海道・沖縄を除く掲載条件の参考で、まとめ買い・店頭小袋購入では再計上する。[販売ページ確認記録](../two-story/plain_hole_fastener_observations.json)。各床4点固定と支柱根元両側補強は継続する。追加金属加工は不要。

## これから金額が増える項目

主計算機の0.5kgは重量の予約であり、購入費の計上ではない。未計上品は次のとおり。

| 未計上品 | 状態 |
|---|---|
| [純正接合部・溝ナットの送料枠](BOM-details.ja.md#item-s04) | 送料未確定 |
| [Taobao送料・輸入諸費](BOM-details.ja.md#item-s07) | 未見積 |
| [ブラケット・天板固定ボルト](BOM-details.ja.md#item-d3_m6) | 寸法選定済・実機検証前 |
| [印刷ストッパ固定ねじ](BOM-details.ja.md#item-d3_stop_bolts) | 寸法選定済・実機検証前 |
| [ストッパ・床継ぎ目用ナット](BOM-details.ja.md#item-d3_stop_nuts) | 寸法選定済・実機検証前 |
| [ストッパ用座金](BOM-details.ja.md#item-d3_stop_washers) | 寸法選定済・実機検証前 |
| [電池・電装の軟質当て材](BOM-details.ja.md#item-power_pads) | 型式選定・現物／電気検証前 |
| [1階計算機・監視回路の保持ベルト](BOM-details.ja.md#item-power_low_straps) | 型式選定・現物／電気検証前 |
| [継ぎ目支持梁端の大径平座金](BOM-details.ja.md#item-d62_beam_washers) | 寸法選定済・購入パック未確定 |
| [独立した電池低電圧保護回路](BOM-details.ja.md#item-u01) | 走行台車／未選定 |
| [上位計算機・記憶媒体・冷却](BOM-details.ja.md#item-u03) | 走行台車／未選定 |
| [上位計算機用DC/DC](BOM-details.ja.md#item-u04) | 走行台車／未選定 |
| [ARM押ボタン](BOM-details.ja.md#item-u05) | 走行台車／未選定 |
| [主電源スイッチ・主コネクタ](BOM-details.ja.md#item-u06) | 走行台車／未選定 |
| [ヒューズ・ホルダー](BOM-details.ja.md#item-u07) | 走行台車／未選定 |
| [制御・分配基板とコネクタ](BOM-details.ja.md#item-u08) | 走行台車／未選定 |
| [リレーコイル駆動・保護部品](BOM-details.ja.md#item-u09) | 走行台車／未選定 |
| [レベル変換・デバウンス・電源投入リセット](BOM-details.ja.md#item-u10) | 走行台車／未選定 |
| [抵抗・コンデンサ・終端抵抗](BOM-details.ja.md#item-u11) | 走行台車／未選定 |
| [電圧・電流計測部品](BOM-details.ja.md#item-u12) | 走行台車／未選定 |
| [電源線・信号線・圧着端子・結束材](BOM-details.ja.md#item-u13) | 走行台車／未選定 |
| [放熱固定具・ガード・絶縁材](BOM-details.ja.md#item-u14) | 走行台車／未選定 |
| [電装固定板・ケース・スタンドオフ](BOM-details.ja.md#item-u15) | 走行台車／未選定 |
| [未確定送料・税・決済換算](BOM-details.ja.md#item-u16) | 走行台車／未選定 |
| [加工工具・作業費・残る自加工品の外注費](BOM-details.ja.md#item-u17) | 走行台車／未選定 |
| [PLA仮合わせモックの材料消費](BOM-details.ja.md#item-u18) | 製作補助／未選定 |
| [自律移動用LiDAR・IMU・カメラ等](BOM-details.ja.md#item-u19) | 将来自律移動／未選定 |
| [荷物容器・敷板](BOM-details.ja.md#item-u20) | 積載物／未選定 |

## 見直すと効果の大きい費用

- 電池・充電器・アダプター：約23,380円。未所有のため充電器も含む。
- 専用モーター金具2個：約12,935円（送料込みの実自動見積）。形状や加工条件を変更する場合は実見積を取り直す。
- タイヤキット2個：9,240円。Taobaoのモーターに同じキットが付くと確認できた場合のみ、別購入を外せる。
- 溝ナット100個：5,112円、使用70個。20個の接合金具本体1,834円より大きい。安価な互換品へ置換する場合は寸法・締結条件を照合する。

[CADと設計の説明](README.ja.md)／[重量と積載](../two-story/PAYLOAD_REVIEW.ja.md)／[全明細Markdown](BOM-details.ja.md)／[全明細CSV](BOM.csv)／[費用集計CSV](BOM-summary.csv)／[計算値JSON](BOM-costs.json)
