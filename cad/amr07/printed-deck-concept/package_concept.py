"""Refresh the comparison cost table and downloadable concept package."""
from pathlib import Path
import csv
import json
import zipfile

HERE=Path(__file__).resolve().parent
d=json.loads((HERE/'validation.json').read_text())
grams=d['mass']['solid_PLA_panels_kg']*1000
rows=[
    ['P01','PLA上板4枚',f'4枚／約{grams:.0f}g',round(d['cost_comparison']['PLA_consumption_reference_JPY']),'既存仮枠2円/g×CAD固体体積。スライス未実施'],
    ['P02','追加支持棒15角×300を2本','995mm定尺×1',1507,'既存販売記録。切断2回とφ6.6穴4か所は自加工'],
    ['P03','圧縮スリーブOD10 ID6.6 L4','10個','','購入品／切断加工の選定・価格未確定'],
    ['P04','支持棒用M6×30＋φ12座金','ボルト4本＋座金8枚','','追加購入単位未確定'],
    ['P05','HNTT6-6','追加支持部で4個使用',0,'外す電装トレイの8個から4個を転用する条件。新規購入増分なし'],
    ['P06','M4×30ストッパ固定','8本','','既存M4×25×8を置換。販売パック・差額未確定'],
    ['P07','拡張部品固定用M4ねじ・六角ナット','必要な穴だけ','','格子36穴すべてに常設する必要なし。取付相手と長さ未定'],
    ['P08','送料・工具・電力・印刷失敗・作業費','未確定','','完成価格には未算入'],
    ['R01','A5052荷台板を取りやめる場合','1枚',-4521,'元BOM DECK_plateの参考額。P0採用前は元BOMから除かない']]
with (HERE/'comparison_bom.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f,lineterminator='\n');w.writerow(['ID','品目','数量','参考増減JPY','根拠']);w.writerows(rows)
archive=HERE/'printed-deck-P0.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(HERE.iterdir()):
        if p.is_file() and p.suffix in ('.stl','.FCStd','.step','.md','.csv','.json','.png','.py'):
            z.write(p,p.name)
print(archive.name,archive.stat().st_size,'bytes')
