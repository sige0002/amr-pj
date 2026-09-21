# A5：加工サイトへ実ファイルを投入した比較見積

2026-09-21、[JLCCNC日本語見積画面](https://jlccnc.com/jp/cnc-machining-quote)で取得。D1〜D5それぞれのSTEPと対応する2頁の寸法図PDFをアップロードし、同条件で比較した。**今回の最安は旧A4で、新5案による値下げは確認できなかった。**

## 価格と証拠

価格は同形2個のロット合計。送料7.23 USDは各案を個別に日本へ送る画面表示で、全案まとめ買いの送料ではない。

| 案 | 標準5日 USD | 経済的10日 USD | OCS送料 USD | 経済的＋表示送料 USD | 証拠 |
|---|---:|---:|---:|---:|---|
| A4 | 84.06 | 74.50 | 7.23 | **81.73** | [今回の価格再確認](quote-evidence/A4-control-economic.png)、[元の全条件](../amr05/MACHINING_QUOTE.ja.md) |
| D1 | 92.16 | 81.40 | 7.23 | 88.63 | [標準](quote-evidence/D1-standard.png)、[経済的](quote-evidence/D1-economic.png)、[設定](quote-evidence/D1-settings.png)、[備考](quote-evidence/D1-settings-notes.png)、[送料](quote-evidence/D1-shipping.png) |
| D2 | 92.80 | 81.92 | 7.23 | 89.15 | [標準](quote-evidence/D2-standard.png)、[経済的](quote-evidence/D2-economic.png)、[設定](quote-evidence/D2-settings.png)、[備考](quote-evidence/D2-settings-notes.png)、[送料](quote-evidence/D2-shipping.png) |
| D3 | 90.94 | 80.36 | 7.23 | 87.59 | [標準](quote-evidence/D3-standard.png)、[経済的](quote-evidence/D3-economic.png)、[設定](quote-evidence/D3-settings.png)、[備考](quote-evidence/D3-settings-notes.png)、[送料](quote-evidence/D3-shipping.png) |
| D4 | 84.66 | 75.02 | 7.23 | 82.25 | [標準](quote-evidence/D4-standard.png)、[経済的](quote-evidence/D4-economic.png)、[設定](quote-evidence/D4-settings.png)、[備考](quote-evidence/D4-settings-notes.png)、[送料](quote-evidence/D4-shipping.png) |
| D5 | 90.84 | 80.08 | 7.23 | 87.31 | [標準](quote-evidence/D5-standard.png)、[経済的](quote-evidence/D5-economic.png)、[設定](quote-evidence/D5-settings.png)、[備考](quote-evidence/D5-settings-notes.png)、[送料](quote-evidence/D5-shipping.png) |

D5はA4より2個で5.58 USD高い。D4は0.52 USD高い。自動見積エンジンの費用内訳は公開されていないため、差額を工具交換・材料・段取り等の特定要因へ配賦しない。

## 揃えた条件

- 数量2個、左右は同じ部品を反転して使用。表示通貨USD、クーポンなし。
- Aluminum 6061、材質説明の調質T6、表面処理なし、外観Standard、組立なし。
- 全5穴は通し穴。ねじ加工なし。
- 最も厳しい公差は±0.05mm。対象は受け平面の軸距離8.25mmだけと図面・備考で限定し、その他はISO2768-mの見積条件。
- 各案の専用STEPと対応PDFを添付し、形状変更は協議が必要と記載。
- 日本宛OCS Express、配送表示4〜6営業日。国単位の送料計算で、住所別確認や最終チェックアウトは未実施。

[machining_quotes.json](machining_quotes.json)に観測時刻、実ファイル名、形状体積、STEP/PDFと画面・画面テキストのSHA-256を保存した。見積条件とモデルを結び付け、後から形状を変えたファイルへ同じ価格を流用しない。

これらは実サイトの**自動見積**であり、手動の図面審査を通った正式製造価格ではない。発注・決済は行っていない。税、輸入諸費、住所による追加送料、決済時の円換算は未確認。寸法公差とは別に、購入するモーターとの適合、材料保証、荷重・寿命の確認が残る。[業者の注文ガイド](https://jlccnc.com/help/article/cnc-machining-ordering-guidelines)

## 費用表への反映

[BOM_cost_comparison.csv](BOM_cost_comparison.csv)と[cost_comparison.json](cost_comparison.json)は、A4のBOMを複製した比較計算上で、専用金具2個の見積Q01と送料S08だけを置換した。2個分の見積に再度数量2を掛けていない。未確定分が残るため完成機の円総額は `null` とした。

旧案の最低価格を残し、D5は比較CADと印刷モックに限定する判断を[selection.json](selection.json)へ記録した。低価格なA4を、そのまま可搬15kg・安全率2の合格案と扱うものでもない。
