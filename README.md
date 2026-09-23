# AMR-01：D6.8 フレーム直付けヒンジ・床支持の操作箱

**HG-TP20トルクヒンジを3030へ直接固定し、天板側は金属L金具で接続しました。開き止めはありません。** 非常停止箱・主電源箱はPLA床へ載せ、各4本のM4で上から固定します。

**BOM：[費用割合・購入リスト](cad/amr07/direct-hinge/BOM.ja.md) ／ [全明細Markdown](cad/amr07/direct-hinge/BOM-details.ja.md) ／ [CSV](cad/amr07/direct-hinge/BOM.csv)**

![FreeCAD実画面：全体](cad/amr07/direct-hinge/cad-screen-closed.png)

![FreeCAD実画面：フレームへ直接固定するヒンジ](cad/amr07/direct-hinge/cad-screen-hinge-detail.png)

| 項目 | 現行構成 |
|---|---|
| 荷台 | アルミ300×300×4mm、上面233mm。36格子穴＋ヒンジ用穴4個。取付空間検査で格子34か所が空く |
| 開閉 | HG-TP20×2、固定葉は3030外側溝に金属接触で直付け。左右共通の50×50×22mm・壁4mmのL金具 |
| 保持 | 空の天板1.201kg、最大モーメント1.621N·m。初期下限保持3.0N·m、比1.85。0〜90°を検査、開き止めなし |
| 閉鎖 | M6蝶ボルト2本。下向き積載荷重は上段アルミレールへ流す |
| 操作部 | 後方のPLA箱を床の一体座へ各4本のM4で固定。蓋裏リブで押下力を分散 |
| 組立 | 金具は左右共通・通し穴のみ。天板とヒンジを机上で組み、最後にフレーム溝へ固定 |
| 重量・積載 | 車体推計10.615kg。通常荷物10kg、静的構造比較15kg。実機試験前 |
| 加工見積 | 新天板1枚＋L金具2個＋日本送料102.13 USD、参考約16,062円。担当者審査前の実自動見積 |
| 費用 | 途中小計85,203円＋184.38 USD、記録済み参考為替で約114,200円＋未計上分 |

![FreeCAD実画面の開閉GIF](cad/amr07/direct-hinge/cad-opening.gif)

空天板での保持、開閉、電池・計算機の取り出し、工具と操作する手の経路をCADで検査。開閉の近接部は1°刻みの検査で、実品公差を含む連続運動や実強度の認定ではありません。14個の試作STL、保存CADとSTEPも照合済み。GIFはCAD配置のアニメーションで、物理シミュレーションではありません。

金属L金具2個の加工表示は63.38 USD（参考約9,968円）。費用増を含めてBOMに反映し、旧D6.7との差は約11,318円増です。PC・専用基板・配線などは未計上、モーター価格は仮予算を含むため完成車の確定額ではありません。Primeの最終配送条件は未確認です。

- [設計理由・ヒンジ保持計算・組立順序・CAD画像](cad/amr07/direct-hinge/README.ja.md)
- [重量・輪荷重・L金具とPLA箱の比較計算](cad/amr07/direct-hinge/PAYLOAD_REVIEW.ja.md)
- [実加工見積・投入STEP・証拠画面](cad/amr07/direct-hinge/MACHINING_QUOTE.ja.md)
- [FCStd](cad/amr07/direct-hinge/AMR01_DirectHinge_D68.FCStd) ／ [機器外形付きSTEP](cad/amr07/direct-hinge/AMR01_DirectHinge_D68.step) ／ [試作STL14個ZIP](cad/amr07/direct-hinge/D68-print-prototypes.zip)
- [要件](cad/amr07/direct-hinge/requirements.json) ／ [干渉検査](cad/amr07/direct-hinge/validation.json) ／ [保存物検査](cad/amr07/direct-hinge/saved_artifact_validation.json)
- [制御・電源保護・停止試験](cad/amr07/ELECTRICAL_AND_VALIDATION.ja.md) ／ [製造・既製モジュール比較](cad/amr07/control-layout/ELECTRONICS_OPTIONS.ja.md)
- [旧D6.7：不採用の樹脂ヒンジ支持を含む履歴](cad/amr07/hinged-deck/README.ja.md)

## 継承した機械構成とシミュレーション

D6.5の各床4点固定、中央支持梁、四隅の連続したPLA床、計算機下の絶縁用カバーは維持しています。[床の設計](cad/amr07/two-story/README.ja.md)／[PLA床解析と限界](cad/amr07/two-story/pla-strength/README.ja.md)／[ロボコン等の参考設計](cad/amr07/two-story/REFERENCE_DESIGNS.ja.md)。

[Isaac Sim 5向けURDF・取込手順](sim/isaac_sim/README.ja.md)と[データZIP](sim/isaac_sim/amr_d65_isaac5.zip)は**D6.5時点**のモデルです。今回の後方操作部・ヒンジ・重量増は未反映。URDF検査とMuJoCo補助走行は実施済み、Isaac Sim本体での実行は未確認です。

![旧D6.5の走行シミュレーション（MuJoCo）](sim/isaac_sim/amr_d65_motion_mujoco.gif)

## 比較履歴・共通資料


- [A5：5案の実加工費・強度比較](cad/amr06/README.ja.md) / [修正元の設計レビュー](cad/amr06/DESIGN_REVIEW_2026-09-21.ja.md)
- [A4：M0601C_111と専用低背金具](cad/amr05/README.ja.md)
- [メーカーCAD・モーター仕様・タイヤ交換](cad/amr05/M0601C_INTERFACE.ja.md)
- [実加工サイト見積のスキル](skills/cnc-quote/SKILL.md)
- [A3：DDSM115](cad/amr04/README.ja.md) / [A2：FIT0185](cad/amr03/README.ja.md)
- [第二案B・却下したベルト案C](cad/amr02/README.ja.md) / [第一案](cad/amr01/README.ja.md)
- [初期基礎設計書](docs/amr-01/DESIGN.ja.md) / [FreeCAD環境](cad/README.md)
