#!/usr/bin/env python3
"""Five actual CAD solids, quadratic tetrahedra, elastic coupled floor/beam screen.

Four clamped vertical fixing patches per panel. Continuous rail contact is
omitted. Central patches settle according to the separately solved beam's
4x4 flexibility matrix, including panel restoring stiffness. This is not a
contact/preload/creep or printed-material certification model.
"""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,zipfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import meshio
HERE=Path(__file__).resolve().parent
G=9.80665;E=1000.;NU=.35
PANELS=[f'FloorPLA_{x}_{y}' for x in range(2) for y in range(2)]
NAMES=PANELS+['SeamBeamPLA']
JOINTS=[((-1 if x==0 else 1)*15,(-1 if y==0 else 1)*25) for x in range(2) for y in range(2)]
EQUIPMENT=[('battery',.953,(-193,-37.5,-80,37.5)),('computer',.525,(-60,-50,60,50)),
 ('supervisor',.055,(5,65,75,110)),('protection',.2,(135,-110,205,-40)),('power',.2,(155,-25,205,65))]
STRAPS=[('battery',(-193,-37.5,-80,37.5),[(-195,-12.5,-190,12.5),(-80,-12.5,-75,12.5)]),
 ('computer',(-60,-50,60,50),[(-60.25,-7.5,-55.25,7.5),(55.25,-7.5,60.25,7.5)]),
 ('supervisor',(5,65,75,110),[(4.75,82.5,9.75,97.5),(70.25,82.5,75.25,97.5)])]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mesh(name,args,geometry):
 d=args.work/name;d.mkdir(parents=True,exist_ok=True)
 geo=d/'model.geo'
 geo.write_text(f'SetFactory("OpenCASCADE");\nMerge "{HERE/name}.step";\nMesh.MeshSizeMin=0.65;\nMesh.MeshSizeMax={args.size};\nMesh.MeshSizeFromCurvature=16;\nMesh.ElementOrder=2;\nMesh.HighOrderOptimize=1;\nMesh.SaveAll=1;\n')
 if not (d/'model.msh').exists():
  with (d/'mesh.log').open('w') as f:subprocess.run([args.gmsh,str(geo),'-3','-format','msh2','-nt','2','-o',str(d/'model.msh')],stdout=f,stderr=subprocess.STDOUT,check=True)
 m=meshio.read(d/'model.msh');xyz=m.points;tet=m.cells_dict['tetra10'];tri=m.cells_dict['triangle6']
 a=xyz[tri[:,:3]];area=np.linalg.norm(np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]),axis=1)/2
 center=a.mean(axis=1)
 q=xyz[tet[:,:4]];vol=np.abs(np.linalg.det(np.stack([q[:,1]-q[:,0],q[:,2]-q[:,0],q[:,3]-q[:,0]],axis=2)))/6
 assert np.min(vol)>1e-10
 err=abs(vol.sum()/geometry[name]['volume_mm3']-1)
 assert err<.015,(name,err)
 nodes=np.unique(tet);assert len(nodes)==len(xyz)
 out=dict(name=name,d=d,xyz=xyz,tet=tet,tri=tri,area=area,center=center,vol=vol,
  cad_volume=geometry[name]['volume_mm3'],volume_error=err)
 out['gravity']=np.zeros(len(xyz))
 mass=geometry[name]['solid_mass_kg'];weights=vol/vol.sum()*mass*G
 for i in range(10):np.add.at(out['gravity'],tet[:,i],-weights*(-.05 if i<4 else .2))
 patches=[]
 if name in PANELS:
  for x in geometry[name]['fixings']:
   px,py=x['xy_mm'];r=9 if x['thread']=='M6' else 4.5
   sel=(abs(xyz[:,2]-99)<1e-6)&((xyz[:,0]-px)**2+(xyz[:,1]-py)**2<=r*r+1e-8)
   ids=np.flatnonzero(sel);assert len(ids)>=4,(name,x,len(ids));patches.append(ids)
  # Fixing list is generated M6 first, M4 last.
  assert geometry[name]['fixings'][-1]['thread'].startswith('M4')
  support=np.unique(np.concatenate(patches));pin=int(patches[0][0]);slider=int(patches[2][0])
  out.update(patches=patches,support=support,pin=pin,slider=slider)
 else:
  for sy in [-1,1]:
   for x in [-18,18]:
    sel=(abs(xyz[:,1]-sy*50)<1e-6)&((xyz[:,0]-x)**2+(xyz[:,2]-84)**2<=81+1e-8)
    ids=np.flatnonzero(sel);assert len(ids)>=4;patches.append(ids)
  out.update(patches=patches,support=np.unique(np.concatenate(patches)))
 print(name,'mesh',len(xyz),'nodes',len(tet),'C3D10',flush=True)
 return out

def selected_surface(m,rect,z):
 c=m['center'];tri=m['tri'];xyz=m['xyz']
 sel=np.all(abs(xyz[tri,2]-z)<1e-5,axis=1)
 if rect is not None:
  x0,y0,x1,y1=rect;sel&=(c[:,0]>=x0)&(c[:,0]<=x1)&(c[:,1]>=y0)&(c[:,1]<=y1)
 return np.flatnonzero(sel)
def pressure(models,loads,rect,z,force):
 selected=[selected_surface(m,rect,z) for m in models]
 area=sum(m['area'][s].sum() for m,s in zip(models,selected));assert area>1,(rect,z,force,area)
 for m,s,f in zip(models,selected,loads):
  # Consistent nodal load on planar quadratic triangles: midsides only.
  for i in [3,4,5]:np.add.at(f,m['tri'][s,i],m['area'][s]*force/area/3)
 return area

def feet(rect):
 x0,y0,x1,y1=rect
 return [(x-5,y-5,x+5,y+5) for x in [x0+10,x1-10] for y in [y0+10,y1-10]]
def make_loads(models):
 loads=[[m['gravity'].copy() for m in models] for _ in range(2)]+[[np.zeros(len(m['xyz'])) for m in models] for _ in range(2)]
 for kind in range(2):
  for name,mass,rect in EQUIPMENT:
   rects=[rect] if kind==0 else feet(rect)
   for p in rects:pressure(models,loads[kind],p,101.4,-mass*G/len(rects))
  pressure(models,loads[kind],None,101.4,-.467*G) # wiring and equipment allowance to total2.4kg
  for name,rect,up in STRAPS:
   rects=[rect] if kind==0 else feet(rect)
   for p in rects:pressure(models,loads[2+kind],p,101.4,-2/len(rects))
   for p in up:pressure(models,loads[2+kind],p,99,1)
 assert abs(sum(m for _,m,_ in EQUIPMENT)+.467-2.4)<1e-10
 for n in range(2):assert abs(sum(f.sum() for f in loads[2+n]))<1e-9
 for i,m in enumerate(models):m['loads']=[a[i] for a in loads]+[np.zeros(len(m['xyz']))]
 return loads

def setlines(f,name,ids):
 f.write('*NSET,NSET='+name+'\n')
 for i in range(0,len(ids),12):f.write(','.join(str(int(j)+1) for j in ids[i:i+12])+'\n')
def solve(m,args):
 path=m['d']/'model.inp';npnt=len(m['xyz']);beam=m['name']=='SeamBeamPLA'
 old_input_sha=sha(path) if path.exists() else None
 with path.open('w') as f:
  f.write('*HEADING\nD6.3 PLA elastic screen, N mm MPa. E1000 sensitivity.\n*NODE,NSET=ALLN\n')
  for i,p in enumerate(m['xyz'],1):f.write(f'{i},'+','.join(f'{x:.10g}' for x in p)+'\n')
  f.write('*ELEMENT,TYPE=C3D10,ELSET=ALLE\n')
  for i,t in enumerate(m['tet'],1):f.write(f'{i},'+','.join(str(int(x)+1) for x in t)+'\n')
  f.write(f'*MATERIAL,NAME=PLA\n*ELASTIC\n{E},{NU}\n*SOLID SECTION,ELSET=ALLE,MATERIAL=PLA\n')
  setlines(f,'SUPPORT',m['support'])
  for i,p in enumerate(m['patches']):setlines(f,'P'+str(i),p)
  for case,load in enumerate(m['loads']):
   f.write('*STEP\n*STATIC\n*BOUNDARY,OP=NEW\n')
   if beam:f.write('SUPPORT,1,3,0\n')
   else:
    for i in range(4):f.write(f'P{i},3,3,{1 if case==4 and i==3 else 0}\n')
    f.write(f'{m["pin"]+1},1,2,0\n{m["slider"]+1},2,2,0\n')
   f.write('*CLOAD,OP=NEW\n')
   ids=np.flatnonzero(abs(load)>1e-15)
   if len(ids)==0:f.write('1,3,0\n')
   for i in ids:f.write(f'{i+1},3,{load[i]:.12g}\n')
   f.write('*NODE PRINT,NSET=ALLN\nU\n*NODE PRINT,NSET=SUPPORT\nRF\n*EL PRINT,ELSET=ALLE\nS\n*END STEP\n')
 # This packaged CalculiX2.21 showed non-equilibrated results with two threads.
 # Single-thread execution is checked against total reactions in every case.
 env=dict(os.environ,OMP_NUM_THREADS='1',CCX_NPROC_RESULTS='1',
  CCX_NPROC_STIFFNESS='1',CCX_NPROC_EQUATION_SOLVER='1',OPENBLAS_NUM_THREADS='1',LD_LIBRARY_PATH=args.ccx_lib)
 if args.reuse:
  assert old_input_sha==sha(path),'Cached input does not match generated input'
  assert 'Using up to 1 cpu(s)' in (m['d']/'solver.log').read_text()
 else:
  with (m['d']/'solver.log').open('w') as f:subprocess.run([args.ccx,'-i','model'],cwd=m['d'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 steps=[];mode=None;current=None
 for line in (m['d']/'model.dat').read_text().splitlines():
  l=line.lower()
  if 'displacements (' in l:
   current=dict(u=np.zeros((npnt,3)),r=np.zeros((npnt,3)),s=[],ids=[]);steps.append(current);mode='u';continue
  if 'forces (' in l:mode='r';continue
  if 'stresses (' in l:mode='s';continue
  v=line.split()
  if not v or not v[0].isdigit():continue
  if mode in ['u','r'] and len(v)==4:current[mode][int(v[0])-1]=[float(x) for x in v[1:]]
  elif mode=='s' and len(v)>=8:
   current['s'].append([float(x) for x in v[2:8]]);current['ids'].append([int(v[0]),int(v[1])])
 assert len(steps)==5,(m['name'],len(steps))
 for s in steps:
  s['s']=np.array(s['s']);s['ids']=np.array(s['ids']);assert len(s['s'])>=len(m['tet'])
 m['steps']=steps
 for i in range(1,5):assert np.array_equal(steps[0]['ids'],steps[i]['ids'])
 # Force equilibrium for every load/prescribed displacement step.
 residuals=[];moments=[]
 for i,s in enumerate(steps):
  # CalculiX RF means external nodal force, i.e. reaction + applied CLOAD.
  # Remove applied loads at constrained nodes to obtain true reactions.
  s['r'][m['support'],2]-=m['loads'][i][m['support']]
  residual=s['r'][:,2].sum()+m['loads'][i].sum()
  assert abs(residual)<max(.002,abs(m['loads'][i].sum())*.001),(m['name'],i,residual)
  residuals.append(float(residual))
  external=s['r'].copy();external[:,2]+=m['loads'][i]
  moment=np.cross(m['xyz'],external).sum(axis=0)
  assert max(abs(moment))<.03,(m['name'],i,moment)
  moments.append(moment.tolist())
 m['force_residuals']=residuals
 m['moment_residuals']=moments
 print(m['name'],'solved5 elastic basis cases',flush=True)
 return m

def beam_loads(m):
 loads=[m['gravity'].copy()]
 for x,y in JOINTS:
  ids=selected_surface(m,None,99);c=m['center'][ids]
  ids=ids[(c[:,0]-x)**2+(c[:,1]-y)**2<=4.5**2]
  area=m['area'][ids].sum();assert area>5,(x,y,area)
  f=np.zeros(len(m['xyz']))
  for i in [3,4,5]:np.add.at(f,m['tri'][ids,i],m['area'][ids]/area/3)
  assert abs(f.sum()-1)<1e-10;loads.append(f)
 m['loads']=loads

def combine(fields,coeff):
 return {key:sum(a[key]*c for a,c in zip(fields,coeff)) for key in ['u','r','s']}
def couple(panels,beam):
 k=np.array([m['steps'][4]['r'][m['patches'][3],2].sum() for m in panels]);assert np.all(k>0)
 C=np.array([[f@beam['steps'][j+1]['u'][:,2] for j in range(4)] for f in beam['loads'][1:]])
 symmetry=np.max(abs(C-C.T))/np.max(abs(C));assert symmetry<2e-5,symmetry
 assert np.min(np.linalg.eigvalsh((C+C.T)/2))>0
 g=np.array([f@beam['steps'][0]['u'][:,2] for f in beam['loads'][1:]])
 result=[]
 for case in range(4):
  r0=np.array([m['steps'][case]['r'][m['patches'][3],2].sum() for m in panels])
  d=np.linalg.solve(np.eye(4)+C@np.diag(k),(g if case<2 else np.zeros(4))-C@r0)
  r=r0+k*d
  pfields=[combine([m['steps'][case],m['steps'][4]],[1,di]) for m,di in zip(panels,d)]
  bfield=combine(beam['steps'],[1 if case<2 else 0]+list(-r))
  observed=np.array([f@bfield['u'][:,2] for f in beam['loads'][1:]])
  assert np.max(abs(observed-d))<1e-7
  base_rf=sum(a['r'][np.concatenate(m['patches'][:3]),2].sum() for a,m in zip(pfields,panels))+bfield['r'][:,2].sum()
  load=sum(m['loads'][case].sum() for m in panels)+(beam['gravity'].sum() if case<2 else 0)
  assert abs(base_rf+load)<.01,(case,base_rf,load)
  result.append(pfields+[bfield])
 return result,dict(panel_center_stiffness_N_mm=k.tolist(),beam_flexibility_mm_N=C.tolist(),
  reciprocity_relative_error=float(symmetry),coupling='(I+C*K)*d = d_beam_gravity - C*R_floor_fixed; all four seam displacements coupled',
  other_rail_contact_included=False)

def metrics(m,f):
 s=f['s'];T=np.zeros((len(s),3,3));T[:,0,0]=s[:,0];T[:,1,1]=s[:,1];T[:,2,2]=s[:,2]
 T[:,0,1]=T[:,1,0]=s[:,3];T[:,0,2]=T[:,2,0]=s[:,4];T[:,1,2]=T[:,2,1]=s[:,5]
 eig=np.linalg.eigvalsh(T);it=int(np.argmax(eig[:,-1]));ic=int(np.argmin(eig[:,0]));iu=int(np.argmin(f['u'][:,2]))
 it_el=int(m['steps'][0]['ids'][it,0])-1
 return dict(part=m['name'],max_down_mm=max(0,float(-f['u'][iu,2])),max_up_mm=max(0,float(f['u'][:,2].max())),
  max_displacement_norm_mm=float(np.linalg.norm(f['u'],axis=1).max()),
  peak_tensile_principal_MPa=max(0,float(eig[it,-1])),peak_compressive_principal_MPa=max(0,float(-eig[ic,0])),
  tensile_peak_element_IP=m['steps'][0]['ids'][it].tolist(),max_down_node_xyz_mm=m['xyz'][iu].tolist(),
  tensile_peak_element_centroid_mm=m['xyz'][m['tet'][it_el,:4]].mean(axis=0).tolist(),
  rail_fixing_vertical_reactions_N=[float(f['r'][p,2].sum()) for p in m['patches']],
  bulk_tensile_IP_percentile99_MPa=float(np.quantile(eig[:,-1],.99)))

def plot(models,fields,path,title):
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import PolyCollection
 from matplotlib.colors import Normalize
 fig,ax=plt.subplots(figsize=(11,6));maxval=max(np.max(-f['u'][:,2]) for f in fields[:4]);norm=Normalize(0,maxval)
 for m,f in zip(models[:4],fields[:4]):
  ids=selected_surface(m,None,101.4);t=m['tri'][ids,:3]
  coll=PolyCollection(m['xyz'][t,:2],array=(-f['u'][t,2]).mean(axis=1),cmap='viridis',norm=norm,edgecolors='none');ax.add_collection(coll)
  for p in m['patches']:xy=m['xyz'][p,:2].mean(axis=0);ax.plot(*xy,'r+',ms=7)
 ax.autoscale();ax.set(aspect='equal',xlabel='X [mm]',ylabel='Y [mm]',title=title)
 fig.colorbar(coll,ax=ax,label='Downward displacement [mm]; E=1000 MPa')
 fig.tight_layout();fig.savefig(path,dpi=170);plt.close(fig)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--size',type=float,required=True);ap.add_argument('--name',required=True)
 ap.add_argument('--gmsh',required=True);ap.add_argument('--ccx',required=True);ap.add_argument('--ccx-lib',required=True)
 ap.add_argument('--reuse',action='store_true',help='Re-read completed single-thread outputs only if the generated input is identical')
 ap.add_argument('--work',type=Path,required=True);a=ap.parse_args();a.work=a.work.resolve();a.work.mkdir(parents=True,exist_ok=True)
 geometry=json.loads((HERE/'geometry.json').read_text())
 assert geometry['source_cad_sha256']==sha(HERE.parent/'AMR01_TwoStorey_D6.FCStd')
 with ThreadPoolExecutor(max_workers=2) as pool:models=list(pool.map(lambda n:mesh(n,a,geometry['parts']),NAMES))
 make_loads(models[:4]);beam_loads(models[4])
 with ThreadPoolExecutor(max_workers=2) as pool:models=list(pool.map(lambda m:solve(m,a),models))
 bases,coupling=couple(models[:4],models[4]);outdir=HERE/a.name;outdir.mkdir(exist_ok=True)
 cases=[]
 for kind in range(2):
  for tension in [0,10,30]:
   fields=[combine([x,y],[1,tension]) for x,y in zip(bases[kind],bases[kind+2])]
   stats=[metrics(m,f) for m,f in zip(models,fields)]
   cases.append(dict(equipment_contact='full_pads' if kind==0 else 'four_10mm_feet',belt_tension_each_leg_N=tension,
    total_equipment_mass_kg=2.4,total_printed_mass_kg=sum(geometry['parts'][n]['solid_mass_kg'] for n in NAMES),
    parts=stats,max_down_mm=max(s['max_down_mm'] for s in stats),
    max_tensile_MPa=max(s['peak_tensile_principal_MPa'] for s in stats),max_compression_MPa=max(s['peak_compressive_principal_MPa'] for s in stats)))
   if kind==1 and tension in [0,10]:plot(models,fields,outdir/f'floor-deflection-T{tension}.png',f'D6.3 PLA: actual solids, coupled seam beam | four-foot contact, belt {tension} N/leg\n2.4 kg equipment + print self-weight; fixing patches only; no creep/preload model')
 for m in models:
  with zipfile.ZipFile(outdir/(m['name']+'-solver.zip'),'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   for n in ['model.geo','model.msh','model.inp','mesh.log','solver.log']:z.write(m['d']/n,n)
 report=dict(revision='D6.3',source_cad_sha256=geometry['source_cad_sha256'],geometry_sha256=sha(HERE/'geometry.json'),
  solver='CalculiX2.21',mesher='Gmsh4.15.0',element='C3D10 quadratic tetrahedron',E_MPa=E,nu=NU,
  material='Assumed isotropic reduced stiffness. Not a tested print modulus or creep allowable.',
  solver_threads=1,analysis_script_sha256=sha(Path(__file__)),
  maximum_mesh_size_mm=a.size,
  meshes=[dict(part=m['name'],nodes=len(m['xyz']),elements=len(m['tet']),straight_corner_tetra_volume_error=m['volume_error'],support_patch_nodes=[len(x) for x in m['patches']],
   force_balance_residuals_N=m['force_residuals'],moment_balance_residuals_Nmm=m['moment_residuals'],input_sha256=sha(m['d']/'model.inp'),output_dat_sha256=sha(m['d']/'model.dat')) for m in models],
  coupling=coupling,cases=cases,force_balance_passed=True,physical_strength_qualified=False,
  omitted=['rail bearing away from fixing patches','bolt preload and friction/slip','polymer creep and temperature','orthotropic shear constants','impact/fatigue','real equipment foot and belt contact','local contact against metal screw/washer','beam/floor rotational compliance at the small seam fixing patches; translation-only coupling'])
 (outdir/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(name=a.name,cases=[{k:c[k] for k in ['equipment_contact','belt_tension_each_leg_N','max_down_mm','max_tensile_MPa','max_compression_MPa']} for c in cases])),flush=True)
if __name__=='__main__':main()
