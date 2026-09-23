# AMR-01：E3 Pico＋2CH RS485構成

**車載LinuxミニPCからUSBで手持ちPicoへ指令し、完成済み2CH RS485基板で左右M0601C_111を動かす設計へ更新しました。** 後方の非常停止は2NC接点で左右のモーター電源をそれぞれ遮断する案とし、ケースを変更。PicoケースはPLA床へ四隅固定、専用ARMボタンは撤去しました。計算機も切れる主電源スイッチは残します。

**[設計・CAD画像](cad/amr07/pico-control/README.ja.md) ／ [配線構成](cad/amr07/pico-control/WIRING.ja.md) ／ [BOM・費用割合](cad/amr07/fixed-deck/BOM.ja.md) ／ [全明細Markdown](cad/amr07/fixed-deck/BOM-details.ja.md) ／ [CSV](cad/amr07/fixed-deck/BOM.csv)**

![FreeCAD実画面：E3全体](cad/amr07/pico-control/cad-screen-overall.png)

| 項目 | 現行構成 |
|---|---|
| 荷台 | アルミ300×300×4mm、36格子穴。上段3030へM6で左右3点ずつ直接固定 |
| 電池交換 | 天板を残して8mm持ち上げ、後方へ220mm抜く |
| 電装 | 1階に電池・Linux計算機・Pico/HAT。後方に非常停止と主電源 |
| 重量・積載 | 車体推計10.456kg。通常積載10kg、静的比較15kg／安全率2。実機確認前 |
| 計上済み費用 | 75,452円＋120.90 USD＝参考94,466円＋未計上分 |
| 未計上 | Linux計算機・給電部材・HAT・一部締結材・最終ヒューズと配線等 |
| 確認済み範囲 | 変更部17,125組と電池取り出し経路で新規干渉なし。16個のPLA試作STLを用意 |

![FreeCAD実画面：天板を非表示にした電装配置](cad/amr07/pico-control/cad-screen-electronics.png)

HAT/Pico積層寸法は仮合わせ前。非常停止のDC定格を確認していますが、モータードライバー入力の突入適合は未確認です。ファームウェアは動作仕様のみで未実装、実配線・走行試験も未実施です。費用は既存の2026-09-21参考為替を継承した途中小計で、完成車価格ではありません。

- [FreeCAD](cad/amr07/pico-control/AMR01_PicoControl_E3.FCStd) ／ [機器外形付きSTEP](cad/amr07/pico-control/AMR01_PicoControl_E3.step) ／ [PLA試作16部品ZIP](cad/amr07/pico-control/E3-print-prototypes.zip)
- [干渉検査](cad/amr07/pico-control/validation.json) ／ [電装要件](cad/amr07/electrical-buildability/requirements.json)
- [継承したD6.9天板設計](cad/amr07/fixed-deck/README.ja.md) ／ [荷重計算](cad/amr07/fixed-deck/PAYLOAD_REVIEW.ja.md) ／ [既存の実加工見積](cad/amr07/fixed-deck/MACHINING_QUOTE.ja.md)

## 継承した機械構成とシミュレーション

D6.5の各床4点固定、中央支持梁、四隅の連続したPLA床、計算機下の絶縁用カバーは維持しています。[床の設計](cad/amr07/two-story/README.ja.md)／[PLA床解析と限界](cad/amr07/two-story/pla-strength/README.ja.md)／[ロボコン等の参考設計](cad/amr07/two-story/REFERENCE_DESIGNS.ja.md)。

[Isaac Sim 5向けURDF・取込手順](sim/isaac_sim/README.ja.md)と[データZIP](sim/isaac_sim/amr_d65_isaac5.zip)は**D6.5時点**のモデルです。E3の後方操作部・Picoケース・最新重量は未反映。URDF検査とMuJoCo補助走行は実施済み、Isaac Sim本体での実行は未確認です。

![旧D6.5の走行シミュレーション（MuJoCo）](sim/isaac_sim/amr_d65_motion_mujoco.gif)

## 比較履歴・共通資料


- [A5：5案の実加工費・強度比較](cad/amr06/README.ja.md) / [修正元の設計レビュー](cad/amr06/DESIGN_REVIEW_2026-09-21.ja.md)
- [A4：M0601C_111と専用低背金具](cad/amr05/README.ja.md)
- [メーカーCAD・モーター仕様・タイヤ交換](cad/amr05/M0601C_INTERFACE.ja.md)
- [実加工サイト見積のスキル](skills/cnc-quote/SKILL.md)
- [A3：DDSM115](cad/amr04/README.ja.md) / [A2：FIT0185](cad/amr03/README.ja.md)
- [第二案B・却下したベルト案C](cad/amr02/README.ja.md) / [第一案](cad/amr01/README.ja.md)
- [初期基礎設計書](docs/amr-01/DESIGN.ja.md) / [FreeCAD環境](cad/README.md)
