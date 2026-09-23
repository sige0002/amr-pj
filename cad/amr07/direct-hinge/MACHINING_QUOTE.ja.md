# D6.8 天板・ヒンジ金具の実自動見積

変更後のSTEPを[JLCCNC見積画面](https://jlccnc.com/jp/cnc-machining-quote)へ投入し、2026-09-23に確認。**天板1枚＋同形L金具2個＋日本宛送料＝102.13 USD**です。記録済みの2026-09-21参考換算1 USD＝157.26718886円では**約16,062円**。現在の為替・カード請求額ではありません。

| 対象 | 数量 | 外形 | 加工表示・数量全体 | 円換算参考 |
|---|---:|---|---:|---:|
| 格子穴天板D68C | 1枚 | 300×300×4mm | 28.67 USD | 約4,509円 |
| 左右共通L金具D68C | 2個 | 50×50×22mm、壁4mm | **63.38 USD／2個一式** | 約9,968円 |
| 共通配送UPS Worldwide Express Saver | 1便 | サイト重量1.54kg | 10.08 USD | 約1,585円 |
| 合計 | | | **102.13 USD** | **約16,062円** |

金具の価格をさらに2倍していません。材料は加工費に含み、板素材費を加算しません。既存の専用モーター金具A6-R1は別見積のため、こちらの合計には含めず、BOMの別行に残します。

材質はサイトのAluminum6061（説明にT6、降伏240MPa以上）。表面仕上げなし、外観標準、タップなし、組立なし。公差欄±0.10mm、図面の指定箇所に適用、その他ISO2768-mを要求。天板にヒンジ穴4個追加、金具の内隅Rは1本のR3、全4穴をD4.5通し穴に統一。特殊な開き止め形状はありません。

標準製造5日では天板30.69＋金具71.78＝102.47 USD。最終採用は**経済的10日**で28.67＋63.38＝92.05 USD。変更後に配送を再確認し、日本宛の通常配送で最安だったUPS10.08 USDを選択しました。OCS11.52、DHL24.26等も表示。自己契約運送口座の2.02 USDは通常配送として使っていません。UPSの配送表示は2〜4営業日、国単位の見積で郵便番号別検証はしていません。製造日数と合わせた納期保証ではありません。

[自動見積画面](quote-evidence/final-quote.png) ／ [日本宛配送](quote-evidence/shipping-Japan.png) ／ [材質・金具条件](quote-evidence/AMR_LidAngle_D68C-settings.png) ／ [天板条件](quote-evidence/AMR_GridDeck_D68C-settings.png) ／ [集計JSON](quote-evidence/observed.json)。最終画面はチェック付きのD68C天板・金具の2行だけを選択。再投入で生じた重複行と以前の比較形状は未選択で、今回の合計へ入っていません。

**サイトの自動見積であり、担当者の図面審査後の確定額ではありません。** 公差・R3の加工可否、直角・平面度の検査、材料条件の最終確認が残ります。クーポン・初回割引なし、輸入税・カード費用は未計上。注文・決済・製造依頼は行っていません。[公式注文ガイド](https://jlccnc.com/help/article/cnc-machining-ordering-guidelines)／[審査の流れ](https://jlccnc.com/help/article/how-to-place-cnc-orders)。

図面はメインのモデルアップロード欄へSTEPと同じベース名のPDFを投入し、各モデルの3D/2D関連付けを確認しました。[関連付け記録](quote-evidence/drawing-association-check.json)。公差±0.10mmでは編集欄の図面追加ボタンが出ないため、非表示のファイル入力を使った送信を添付完了とは扱っていません。

投入ファイルは[quote-input](quote-input)に固定し、[SHA256一覧](quote-evidence/final-upload-files.json)にSTEP/PDFを記録。公開CADの製造部品と、投入STEPの形状一致は[保存物検査](saved_artifact_validation.json)で確認しました。末尾Cはこのセッションで旧比較モデルと区別するためのアップロード名で、D6.8最終形状です。各PDFは対応STEPのハッシュを記載しています。

この見積取得は[cnc-quoteスキル](../../../skills/cnc-quote/SKILL.md)の手順に沿っています。BOMは[Markdown](BOM.ja.md)と[CSV](BOM.csv)の両方を用意しました。
