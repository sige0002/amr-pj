"""Short-term strip comparison only; never turn typical PLA data into a rating."""
from pathlib import Path
import json
import math

HERE = Path(__file__).resolve().parent


def overhang(thickness, modulus, cargo):
    # Largest panel: x/y=-150..37.3. Two simple supports at y=-135/-65.
    # Uniform equivalent cargo, dead mass and four strap legs over200x200.
    # Each panel is independent; no bending transfer is credited at the seam.
    loaded_width = 137.3
    # Conservatively delete full-thickness strips for three nut pockets and
    # the26mm underside belt channel at every beam section.
    net_width = loaded_width-3*7.3/math.cos(math.pi/6)-26
    s1,s2,a,b=-135,-65,-100,37.3
    force=(cargo+1.6)*9.80665+80
    q=force/(200*200)*loaded_width
    total=q*(b-a)
    r2=total*((a+b)/2-s1)/(s2-s1); r1=total-r2
    inertia=net_width*thickness**3/12
    section=net_width*thickness**2/6
    pos=lambda x,n:max(0,x)**n
    primitive=lambda y:r1*pos(y-s1,3)/6+r2*pos(y-s2,3)/6-q*(pos(y-a,4)-pos(y-b,4))/24
    c1=-(primitive(s2)-primitive(s1))/(s2-s1)
    c2=-primitive(s1)-c1*s1
    positions=[-150+(b+150)*i/2000 for i in range(2001)]
    moments=[r1*pos(y-s1,1)+r2*pos(y-s2,1)-q*(pos(y-a,2)-pos(y-b,2))/2 for y in positions]
    deflections=[(primitive(y)+c1*y+c2)/(modulus*inertia) for y in positions]
    return {'thickness_mm':thickness,'comparison_E_MPa':modulus,'cargo_kg':cargo,
            'net_width_mm':net_width,'outer_support_reaction_N':r1,'inner_support_reaction_N':r2,
            'factored_nominal_bending_stress_MPa':2*max(abs(m) for m in moments)/section,
            'short_term_service_deflection_mm':max(abs(d) for d in deflections),
            'conditional_on_hold_down_fasteners':True,'safety_factor_achieved':None}


def main():
    rows=[overhang(t,e,c) for t in (8,10) for e in (2750,2000) for c in (10,15)]
    p=json.loads((HERE/'parameters.json').read_text())
    result={'method':'Independent split-panel Euler-Bernoulli overhang strip, simple supports with bolt hold-down; sampling0.094mm or finer. No joint stiffness claim.',
            'source':p['material_source'],'comparison_only':True,'same_geometry_Al_to_PLA_deflection_ratio':70000/2750,
            'PLA_E_2000_status':'Engineering sensitivity, not a measured lower material bound',
            'manufacturer_conditions':p['manufacturer_specimens'], 'cases':rows,
            'not_in_model':['Creep/time/temperature','Full2D pressure redistribution','Local nut-hole and slot stress concentration','Plate fastener/sleeve fit/preload','Belt-anchor local forces','Drop/impact/fatigue'],
            'conclusion':'10mm is a trial candidate with lower short-term deflection than8mm. No PLA deck SF2 or10kg operating rating has been established.'}
    (HERE/'screening.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(rows,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
