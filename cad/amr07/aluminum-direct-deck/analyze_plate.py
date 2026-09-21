#!/usr/bin/env python3
"""Reproducible linear S6 shell screen of D3, six fastening patches only, using Triangle and CalculiX.
Additional3030 contact strips are omitted; not a local-contact stress bound.

Tools are supplied as command line arguments; no downloads or installation.
Not a vehicle rating: ideal bolted support patches, prescribed distributed
load and minimum received material properties are explicit assumptions.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import numpy as np

HERE=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def generate(directory,area,ncircle,triangle):
    cfg=json.loads((HERE/'analysis_parameters.json').read_text())
    g=cfg['geometry'];s=cfg['structural_screening']
    assert s['minimum_thickness_for_screening_mm']==3.9 and s['youngs_modulus_MPa']==69000
    assert g['plate_LWT_mm']==[300,300,4] and g['support_block_LWT_mm']==[20,15,0]
    (directory/'input_parameters.json').write_bytes((HERE/'analysis_parameters.json').read_bytes())
    points=[];segments=[];holes=[]
    def loop(coords,hole=None):
        start=len(points);points.extend(coords)
        segments.extend((start+i+1,start+(i+1)%len(coords)+1) for i in range(len(coords)))
        if hole is not None:holes.append(hole)
    def rect(x0,y0,x1,y1):loop([(x0,y0),(x1,y0),(x1,y1),(x0,y1)])
    def circle(x,y,r):loop([(x+r*math.cos(2*math.pi*i/ncircle),y+r*math.sin(2*math.pi*i/ncircle)) for i in range(ncircle)],(x,y))
    rect(-150,-150,150,150)
    for x in g['grid_x_mm']:
        for y in g['grid_y_mm']:circle(x,y,2.25)
    for x,y in g['frame_holes_xy_mm']:circle(x,y,3.3)
    for x,y in g['stop_holes_xy_mm']:circle(x,y,2.25)
    for slot in g['strap_slots']:
        x,y=slot['center_xy_mm'];coords=[]
        for center,start in [(12,-math.pi/2),(-12,math.pi/2)]:
            for i in range(ncircle//2+1):
                a=start+math.pi*i/(ncircle//2)
                xx,yy=center+3*math.cos(a),3*math.sin(a)
                if slot['long_axis']=='y':xx,yy=-yy,xx
                coords.append((x+xx,y+yy))
        loop(coords,(x,y))
    rect(-100,-100,100,100)
    for x,y in g['frame_holes_xy_mm']:rect(x-10,y-7.5,x+10,y+7.5)
    poly=directory/'plate.poly'
    with poly.open('w') as f:
        f.write(f'{len(points)} 2 0 0\n')
        for i,(x,y) in enumerate(points,1):f.write(f'{i} {x:.12f} {y:.12f}\n')
        f.write(f'{len(segments)} 0\n')
        for i,(a,b) in enumerate(segments,1):f.write(f'{i} {a} {b}\n')
        f.write(f'{len(holes)}\n')
        for i,(x,y) in enumerate(holes,1):f.write(f'{i} {x} {y}\n')
    log=subprocess.run([triangle,f'-pq25a{area}o2',poly.name],cwd=directory,capture_output=True,text=True,check=True)
    (directory/'mesh.log').write_text(log.stdout+log.stderr)
    def data(path):
        return [l.split('#')[0].split() for l in path.read_text().splitlines() if l.split('#')[0].strip()]
    rows=data(directory/'plate.1.node');n=int(rows[0][0]);xy=np.zeros((n,2))
    for r in rows[1:]:xy[int(r[0])-1]=[float(r[1]),float(r[2])]
    elems=[]
    for r in data(directory/'plate.1.ele')[1:]:
        corners=[int(i)-1 for i in r[1:4]];mids=[int(i)-1 for i in r[4:7]]
        a,b,c=xy[corners]
        if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:corners[1],corners[2]=corners[2],corners[1]
        ordered=[]
        for u,v in zip(corners,corners[1:]+corners[:1]):
            mid=min(mids,key=lambda m:np.linalg.norm(xy[m]-(xy[u]+xy[v])/2))
            assert np.linalg.norm(xy[mid]-(xy[u]+xy[v])/2)<1e-7
            ordered.append(mid)
        elems.append(corners+ordered)
    elems=np.asarray(elems)
    xyz=xy[elems[:,:3]]
    areas=np.abs((xyz[:,1,0]-xyz[:,0,0])*(xyz[:,2,1]-xyz[:,0,1])-(xyz[:,1,1]-xyz[:,0,1])*(xyz[:,2,0]-xyz[:,0,0]))/2
    centers=xyz.mean(axis=1)
    loaded=(np.abs(centers[:,0])<100)&(np.abs(centers[:,1])<100)
    assert len(holes)==54 and np.all(areas>0)
    force=s['payload_kg']*9.80665+s['plate_borne_dead_mass_allowance_kg']*9.80665+s['strap_vertical_legs']*s['strap_pretension_N_each']
    nodal=np.zeros(n)
    for element,a in zip(elems[loaded],areas[loaded]):
        # Integral of quadratic triangle vertex shape functions is zero;
        # each midside shape integrates to one third of the element area.
        nodal[element[3:]]-=force*a/areas[loaded].sum()/3
    pads=[]
    for x,y in g['frame_holes_xy_mm']:
        pads.append(np.flatnonzero((np.abs(xy[:,0]-x)<=10+1e-7)&(np.abs(xy[:,1]-y)<=7.5+1e-7)))
    support=np.concatenate(pads);assert len(set(support))==len(support)
    pin=int(np.argmin(np.linalg.norm(xy-[-105,-140],axis=1)))
    slider=int(np.argmin(np.linalg.norm(xy-[105,-140],axis=1)))
    inp=directory/'plate.inp'
    with inp.open('w') as f:
        f.write('*HEADING\nD3 minimum3.9mm,15kg cargo+1.6kg dead+80N strap equivalent,linear\n*NODE,NSET=ALLN\n')
        for i,(x,y) in enumerate(xy,1):f.write(f'{i},{x:.10f},{y:.10f},0\n')
        f.write('*ELEMENT,TYPE=S6,ELSET=ALLE\n')
        for i,e in enumerate(elems,1):f.write(f'{i},'+','.join(str(int(n)+1) for n in e)+'\n')
        f.write('*MATERIAL,NAME=AL\n*ELASTIC\n69000,0.33\n*SHELL SECTION,ELSET=ALLE,MATERIAL=AL\n3.9\n')
        f.write('*NSET,NSET=SUPPORT\n')
        for start in range(0,len(support),12):f.write(','.join(str(int(i)+1) for i in support[start:start+12])+'\n')
        f.write(f'*BOUNDARY\nSUPPORT,3,3\n{pin+1},1,2\n{slider+1},2,2\n*STEP\n*STATIC\n*CLOAD\n')
        for i in np.flatnonzero(nodal):f.write(f'{i+1},3,{nodal[i]:.12g}\n')
        f.write('*NODE PRINT,NSET=ALLN\nU\n*NODE PRINT,NSET=SUPPORT\nRF\n*EL PRINT,ELSET=ALLE\nS\n*NODE FILE\nU\n*EL FILE\nS\n*END STEP\n')
    meta={'nodes':n,'S6_elements':len(elems),'maximum_triangle_area_mm2':area,'circle_segments':ncircle,
          'mesh_plan_area_mm2':float(areas.sum()),'CAD_plan_area_mm2':json.loads((HERE/'geometry.json').read_text())['volume_mm3']/4,
          'loaded_actual_material_area_mm2':float(areas[loaded].sum()),'service_force_N':force,
          'nodal_force_sum_N':float(nodal.sum()),'minimum_thickness_mm':3.9,'E_MPa':69000,'nu':.33,
          'support_node_counts':[len(p) for p in pads],'input_sha256':sha(inp),
          'deck_parameters_sha256':sha(HERE/'analysis_parameters.json')}
    np.savez_compressed(directory/'mesh.npz',xy=xy,elems=elems,areas=areas,centers=centers,nodal=nodal,support=support)
    (directory/'model.json').write_text(json.dumps(meta,indent=2)+'\n')
    return meta,xy,elems,pads


def post(directory,meta,xy,elems,pads):
    mode=None;u={};reaction={};stress=[]
    for line in (directory/'plate.dat').read_text().splitlines():
        low=line.lower()
        if 'displacements (' in low:mode='u';continue
        if 'forces (' in low:mode='r';continue
        if 'stresses (' in low:mode='s';continue
        r=line.split()
        if not r or not r[0].isdigit():continue
        if mode in ('u','r') and len(r)==4:
            (u if mode=='u' else reaction)[int(r[0])-1]=[float(v) for v in r[1:]]
        elif mode=='s' and len(r)>=8:
            xx,yy,zz,xyv,xz,yz=map(float,r[2:8])
            vm=math.sqrt(.5*((xx-yy)**2+(yy-zz)**2+(zz-xx)**2)+3*(xyv*xyv+xz*xz+yz*yz))
            stress.append((int(r[0]),int(r[1]),vm))
    assert len(u)==len(xy) and stress,(len(u),len(xy),len(stress))
    uz=np.array([u[i][2] for i in range(len(xy))]);stress.sort(key=lambda s:s[2],reverse=True)
    reactions=[sum(reaction[int(i)][2] for i in pad) for pad in pads]
    balance=abs(sum(reactions)-meta['service_force_N'])/meta['service_force_N']
    assert balance<.005,(reactions,balance)
    assert uz.min()<0 and abs(uz.max())<.05
    # S6 expands to a quadratic wedge. Integration points lie inside the
    # thickness; use1.3 surface extrapolation allowance rather than treating
    # Gauss stresses as exact surface peaks (sqrt(3/5)^-1 ~=1.291).
    surface_factor=1.3
    raw=stress[0][2];screen=raw*surface_factor
    result=dict(meta,support_scope='six ideal clamped patches; all other rail contacts omitted; reference only, no local-contact stress bound',max_downward_deflection_mm=float(-uz.min()),max_upward_deflection_mm=float(uz.max()),
        max_integration_point_von_Mises_MPa=raw,surface_extrapolation_allowance=surface_factor,
        service_surface_stress_screen_MPa=screen,factored_surface_stress_screen_MPa=screen*2,
        conditional_proof_stress_MPa=240,conditional_elastic_safety_factor=240/screen,
        pad_vertical_reactions_N=reactions,vertical_force_balance_relative_error=balance,
        max_stress_element=stress[0][0],max_stress_integration_point=stress[0][1],
        normal10kg_uniform_equivalent_force_N=10*9.80665+1.6*9.80665+80,
        whole_vehicle_SF2_certified=False,loaded_operation_released=False,
        input_sha256=sha(directory/'plate.inp'),dat_sha256=sha(directory/'plate.dat'))
    (directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8,7))
    im=ax.tripcolor(xy[:,0],xy[:,1],elems[:,:3],-uz,shading='gouraud',cmap='viridis')
    ax.set(aspect='equal',xlabel='X [mm]',ylabel='Y [mm]',title='D3 linear shell: downward displacement [mm]\n15 kg + 1.6 kg + 80 N; t = 3.9 mm; six ideal support patches')
    fig.colorbar(im,ax=ax,label='Downward displacement [mm]')
    fig.tight_layout();fig.savefig(directory/'deflection.png',dpi=160);plt.close(fig)
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--triangle',required=True);ap.add_argument('--ccx',required=True)
    ap.add_argument('--area',type=float,required=True);ap.add_argument('--segments',type=int,required=True);ap.add_argument('--name',required=True)
    args=ap.parse_args();out=HERE/'fea'/args.name;out.mkdir(parents=True,exist_ok=True)
    meta,xy,elems,pads=generate(out,args.area,args.segments,args.triangle)
    print(json.dumps(meta),flush=True)
    env=dict(os.environ,OMP_NUM_THREADS='2')
    with (out/'solver.log').open('w') as log:
        subprocess.run([args.ccx,'-i','plate'],cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    print(json.dumps(post(out,meta,xy,elems,pads)),flush=True)


if __name__=='__main__':main()
