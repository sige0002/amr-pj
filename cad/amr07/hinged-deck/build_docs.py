from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
v=json.loads((HERE/'validation.json').read_text());p=json.loads((HERE/'payload_budget.json').read_text());s=json.loads((HERE/'cost_summary.json').read_text());t=v['torque'];m=v['mass']['estimated_base_kg'];a=s['hatch_change']
normal=next(q for q in p['load_cases'] if q['id']=='normal');struct=next(q for q in p['load_cases'] if q['id']=='structure');cast=max(q['max_N'] for q in p['caster_trail_sensitivity'] if q['case']=='normal')
(HERE/'README.ja.md').write_text(f'''# D6.7：開閉するアルミ天板・後方操作部

**アルミ天板を横へ0〜90°開き、工具なしのM6蝶ボルト2本で閉鎖固定する構成へ変更した。非常停止・ARM・主電源は後ろ側。** 天板の300×300×4mm、上面233mm、元の加工形状を維持する。追加フレーム・金属穴加工は不要。

**[BOM概要](BOM.ja.md) ／ [全明細Markdown](BOM-details.ja.md) ／ [CSV](BOM.csv)** — 車体推計**{m:.3f}kg**、途中小計**約{s['full_running_subtotal_JPY_reference']:,.0f}円＋未計上分**。

![FreeCAD実画面：天板を90°開いた状態](cad-screen-open-90.png)

![FreeCAD実画面：天板を閉じ、2か所をロック](cad-screen-closed.png)

[FreeCAD画面による開閉GIF](cad-opening.gif)。これはCADの配置アニメーションで、動力学・強度・実機試験ではない。

## 開閉の構成と設計理由

| 部位 | 採用内容 | 理由 |
|---|---|---|
| 天板 | 既存6061-T6、300×300×4mm | 見積済みの板・格子穴をそのまま使う |
| ヒンジ | スガツネHG-TS15×2、各1.5N·m | 保持トルクと初期公差が公開され、Amazonで単品購入可能 |
| ヒンジ方向 | +Y側、軸X方向、中心X=±126／Y=172.5／Z=249.5mm | 上段側面の溝へ固定でき、前側へ追加する横フレームが不要 |
| 可動側アダプター | PLA、各2本のM4で既存格子穴X=±125／Y=35,85へ固定 | 荷物の200×200mm領域と既存ベルトを避ける。φ4.5の通し穴を維持 |
| 固定側アダプター | PLA、各2本のM6で3030外側溝へ固定 | 左右に離した金属ボルト・溝ナット。既存天板から4組を移して利用 |
| 閉鎖ロック | M6×15蝶ボルト×2、X=±105／Y=−135mm | 金属板を金属レールへ直接締める。1本につきt1鋼製座金3枚で突出8mm、溝底余裕1mm |
| 開き止め | 固定アダプターに90°ストッパーを一体化 | 90°より先へ回して配線や取付部を傷めないため。無理に押し込む用途ではない |

ヒンジは**空の天板を保持する部品**。閉じたときの下向き積載荷重は、従来の2本のアルミレールへ面で伝える。荷物は元の固定ベルトで保持する。PLAのヒンジ取付部だけで荷物15kgの衝撃を支える設計とは扱わない。

中央の200×200mm荷物外形とベルトのCAD干渉は解消済み。格子穴36個のうち、アダプター取付に4個を使い、同じ列の2個を覆う。残る30個の格子穴は形状として残るが、実際の追加機器は工具空間・天板の開閉荷重を再確認する。

![FreeCAD実画面：ヒンジ・アダプター・溝固定](cad-screen-hinge-detail.png)

![FreeCAD実画面：蝶ボルトと3枚の金属座金](cad-screen-lock-detail.png)

## 保持トルクと使い方

メーカーの[HG-TS15仕様](https://www.sugatsune.com/stainless-steel-torque-hinge-hg-ts15/)と[寸法図](https://www.sugatsune.com/content/site-assets/501_PDF/HG-TS_HG-DTA.pdf)は、1個1.5N·m、初期公差−20%〜＋40%、1枚の扉に2個以上を示す。CADはこの寸法から作った公称外形で、ログインが必要なメーカーSTEPは取得していない。

空の天板・ストッパ・可動アダプター・締結材・ヒンジ可動側の推計は**{t['empty_lid_mass_kg']:.3f}kg**。重力モーメントは水平位置で{t['closed_gravity_moment_Nm']:.3f}N·m、重心が軸より低いため開き角{t['maximum_gravity_moment_angle_deg']:.1f}°で最大**{t['maximum_gravity_moment_Nm']:.3f}N·m**となる。ヒンジ2個の初期下限は2.4N·mなので、比較余裕は**{t['minimum_initial_hold_ratio']:.2f}倍**。重い荷物を載せたまま保持できる値ではない。初期上限4.2N·mを含めた端部の開操作力は円弧の接線方向で約{t['max_tangential_opening_hand_force_N']:.0f}N。

1. 平坦な床で停止し、主電源を切る。
2. 荷物と、天板をまたぐ固定ベルトを外す。
3. 蝶ボルト2本と座金を外し、無くさない場所へ置く。現版のロックは脱落防止式・鍵式ではない。
4. 天板の−Y側を持ち、0〜90°で開く。取付ストッパーより先へ押し込まない。
5. 閉じて金属レールへ着座したことを確認し、2本を締め、荷物とベルトを戻す。

ヒンジは速度を抑えるダンパーではなく摩擦保持用。経年・温度・造形のクリープを実機で確認する。理論上の追加固定物の余裕は中心位置で約{t['extra_mass_at_center_limit_kg']:.2f}kgしかないため、天板へ計算機や重い機構を常設して開く場合は再選定する。開放状態で走行しない。蓋開検知の電気インターロックは未実装。

## 後ろ側の操作と整備

非常停止XA1E-BV302Rはパネル中心`[-213,-119,206]`、黒ARM3212は`[-213,-71,206]`、主電源3214は`[-203,+120,237]`。前進は+X、後ろは−X。後ろの中央は電池口として残す。[ケース固定・配線経路](../control-layout/README.ja.md)。

![FreeCAD実画面：後方の操作部・配線経路](cad-screen-rear-controls.png)

![FreeCAD実画面：電池交換](cad-screen-battery-service.png)

![FreeCAD実画面：計算機の引き抜き](cad-screen-computer-service.png)

電池は8mm上げて後方220mm、計算機は8mm上げて側方230mm抜く既存経路を維持。電池の通常交換は天板を閉じたままでも行える。1階の計算機・回路に上から触るときに開閉天板が役立つ。

## 追加費用

| 開閉天板化による追加 | 金額 |
|---|---:|
| HG-TS15×2 | {a['hinges_JPY']:,}円 |
| M6蝶ボルト18個パック（使用2） | {a['locks_pack_JPY']:,}円 |
| M4ナットの追加20個パック | {a['extra_M4_nut_pack_JPY']:,}円 |
| M4座金の追加20枚パック | {a['extra_M4_washer_pack_JPY']:,}円 |
| PLA材料消費参考 | {a['PLA_material_delta_JPY']:,}円 |
| **D6.6からの小計増** | **{a['subtotal_increase_JPY']:,.0f}円** |

M4×16は予定60本、M6座金は予定30枚の余りを使い、ヒンジ用M6ボルト4本・溝ナット4個は旧天板固定から移す。購入パック全額を計上し、使用数で安く見せる按分をしない。新しいヒンジ部PLAは中実CADで約{v['mass']['new_PLA_kg']*1000:.0f}g。印刷の支持材・失敗・電力・工賃は別。

[Amazon送料込み比較・証拠](../control-layout/PROCUREMENT.ja.md)。Pico流用と購入先変更による1,313円減は別に反映済み。モーター14,000円等の旧仮予算、未計上の計算機・専用基板・配線などは残るため、102,882円を完成車の確定価格とは扱わない。

## 検証範囲

[CAD検査](validation.json)は新旧の実体干渉、機器・荷物・ベルト、電池交換、0〜90°の連続した開閉包絡、操作工具、ロックに触れる空間を確認する。新たな形状に関係する組み合わせを再検査し、既存物は元の検証済みCADとの全BRepトークン比較で継承を確認した（数値丸め許容1e−10）。軸付近は回転半径の解析も使い、単なる数コマの画像確認とは分けた。

購入品の実寸、印刷強度・クリープ、ねじ緩み、過大な開操作力、回路実装・停止動作の確認は残る。**印刷ファイルは試作版**。旧D6.5床FEMは床の検討として残すが、旧6点締結の天板FEMを新しい2ロックの強度証明には使わない。[重量・荷重・天板の計算範囲](PAYLOAD_REVIEW.ja.md)。

[FCStd](AMR01_HingedDeck_D67.FCStd)／[機器外形付きSTEP](AMR01_HingedDeck_D67.step)／[構造STEP](AMR01_HingedDeck_D67-structure.step)／[印刷部品一式ZIP](D67-print-prototypes.zip)／[保存物再検査](saved_artifact_validation.json)。

## 再生成

FreeCADの独立プロセスで`../control-layout/build_controls.py`→`build_hatch.py`を実行する。元のD6.5組立は変更しない。FreeCAD GUIで`capture_screens.py`を実行すると、実画面8枚・開閉用10コマを保存し、閉鎖状態へ戻してFCStdを保存する。未保存の編集がある文書は上書きせず、退避してから実行する。

通常Pythonで`make_animation.py`、`check_design.py`、`sync_electrical.py`、`build_bom.py`、`../two-story/build_bom_view.py cad/amr07/hinged-deck`、`build_docs.py`を実行する。`build_bom_view.py`の引数はリポジトリルートからのパス。D6.6側BOMの変更時は、そのフォルダの`build_bom.py`も先に実行する。

最後にFreeCAD独立プロセスで`validate_saved.py`、通常Pythonで`../two-story/release.py`→`release.py`を実行する。[成果物のSHA-256一覧](release_manifest.json)で、ネイティブCAD、STEP、18個の印刷部品、検査・価格証拠・BOMの対応を確認できる。スライス済みデータや完成ハーネスは含まない。
''')
(HERE/'PAYLOAD_REVIEW.ja.md').write_text(f'''# D6.7：重量・積載・開閉部の計算

**車体推計{m:.3f}kg、通常積載目標10kgを維持する。** 車体10kgはユーザー指定の厳密上限ではない。D6.5約10.068kgへ、後方操作部約0.341kg、天板開閉部の正味約{v['mass']['added_kg']-v['mass']['removed_kg']:.3f}kgを追加した。中実CAD・メーカー質量・機器予約枠の混在で、実測ではない。

今回の比較範囲は車体11.5kg、通常総21.5kg、構造比較総26.5kgまで。11.5kgは新しい使用者指定上限ではなく、今回の計算範囲。車体重心はX±25／Y±20／Z160mm以下、荷物重心はX/Y±30／Z330mm以下。ヒンジ側へ質量が増えたため、以前のY±15mmをそのまま使わず±20mmへ広げて輪荷重を再計算した。

| 比較項目 | 現行値 | 比較先 |
|---|---:|---:|
| 通常10kg、余裕1.5込み必要トルク/輪 | {p['torque']['with_margin_Nm_each']:.3f}N·m | 定格0.96N·m |
| 通常条件の保守的モーターラジアル荷重 | {normal['conservative_radial_comparison_N']:.2f}N | メーカー表示120N |
| 通常条件の軸方向荷重 | {normal['conservative_axial_comparison_N']:.2f}N | 表示60N |
| 通常キャスター最大（トレール公差込み） | {cast:.2f}N | 表示300N |
| 静的15kg比較のモーターラジアル荷重 | {struct['conservative_radial_comparison_N']:.2f}N | 表示120N |

平坦屋内、加減速度0.2m/s²、転がり抵抗0.03、車輪径100.7mmを仮定。15kg比較はモーターの表示荷重にかなり近く、走行積載を15kgへ増やす根拠にしない。通常10kgを維持し、低速の熱・停止・衝撃を実機検証する。[メーカー仕様](https://shop.directdrive.com/pages/m0601c-111-specs)。

閉鎖状態の条件付き重心はX約−14.85〜0.25、Y約0.18〜15.27、Z約129.04〜147.91mm。電装質量枠・取付位置の仮定付きであり、完成車の実測重心ではない。天板を開いた状態は空車・停止時専用。開いた重心を走行許容と扱わない。

## 天板の支持変更

閉じた板は上段アルミレールへ直接着座し、2本のM6ロックで保持する。ヒンジを追加しても積載荷重をPLAアダプターに吊らない。追加の天板穴・加工はない。

旧FEMの6点締結境界は今回の2ロックと異なるため、その結果だけを流用しない。まず単純支持の梁として、支間240mm、板厚4mm、仮の有効幅150mm（全幅の50%）、弾性率69GPa、15kg×2の中央集中荷重294.2Nを置いた。曲げ応力{p['plate_simply_supported_sensitivity']['bending_stress_MPa']:.1f}MPa、中央たわみ{p['plate_simply_supported_sensitivity']['central_deflection_mm']:.2f}mmとなる。

これは有効幅を仮定した感度計算。穴・ベルトスリット付近の局所応力、面接触、ロックの締付け、実物の支持剛性を認定するものではない。板の6061-T6比較降伏値240MPaより小さいというだけで、全組立が安全率2を達成したとは結論しない。

## PLAヒンジアダプター

可動アダプターは10mm厚、ねじ周辺の座ぐり底は6mm。1個のヒンジ初期上限2.1N·mを、有効幅30mm・厚さ6mmの断面へ置く孤立した曲げ比較では11.67MPa。安全率2を材料強度に適用するなら、同じ印刷条件の試験片で少なくとも23.34MPa相当が必要になる。**この材料強度や長期クリープは未測定**であり、PLA一般のカタログ強度をそのまま許容値にしない。ねじ穴局所、固定側リブ、開き止めへの過大操作力までのFEMは未実施。

試作では可動板をXY面、固定アダプターをX側面に寝かせて荷重経路を層内へ置く。荷重経路を中実として、取付・繰返し開閉・温度・保持力・緩みを確認する。ヒンジは初期下限2.4N·mに対し空天板最大{t['maximum_gravity_moment_Nm']:.3f}N·m、比較{t['minimum_initial_hold_ratio']:.2f}倍。これは15kg積載の安全率2とは別の、空の蓋を保持できるかの選定条件である。

## 電装試験条件への反映

旧D6.5の20.5kg・0.383N·mに代えて、今回の上限21.5kg・0.401N·mで負荷・停止試験を行う。平地・追加機械ブレーキなし、初期0.15m/s、後期0.3m/s、再始動には手動ARMという方針を維持。21.5kgの並進エネルギーは0.15m/sで0.242J、0.3m/sで0.968J。実回生は回転体等を含むため、この値だけで保護回路を省かない。

[要求と計算上限](requirements.json)／[質量・輪荷重・トルク・感度計算JSON](payload_budget.json)／[再計算コード](check_design.py)／[旧床FEM](../two-story/pla-strength/README.ja.md)。実物の積載・強度・走行の認定は未完了。
''')
print('D6.7 README andloadreview written')
