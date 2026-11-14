"""Use verified recorded-map meshes as a CMU Classic world; add no ground."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,shutil,xml.etree.ElementTree as E
import numpy as np

ROOT=Path('/home/lzz/pcd_test_20261110');SOURCE=ROOT/'source';OUT=ROOT/'runtime'

def height_at(points,triangles):
    a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
    u=b[:,:2]-a[:,:2];v=c[:,:2]-a[:,:2];den=u[:,0]*v[:,1]-u[:,1]*v[:,0]
    heights=[]
    for p in points:
        w=p-a[:,:2];s=(w[:,0]*v[:,1]-w[:,1]*v[:,0])/den
        t=(u[:,0]*w[:,1]-u[:,1]*w[:,0])/den
        hit=(s>=-1e-7)&(t>=-1e-7)&(s+t<=1+1e-7)
        heights.append(float(np.median((a[:,2]+s*(b[:,2]-a[:,2])+t*(c[:,2]-a[:,2]))[hit])) if hit.any() else None)
    return heights

def main():
    if OUT.exists():raise FileExistsError(OUT)
    OUT.mkdir();(OUT/'assets').mkdir()
    recovery=json.loads((SOURCE/'RECOVERY.json').read_text())
    for f in recovery['files']:
        assert hashlib.sha256((SOURCE/f['path']).read_bytes()).hexdigest()==f['sha256']
    raw=np.load(SOURCE/'runtime/local_map.npy')
    if raw.ndim!=2 or raw.shape[1]!=3 or not np.isfinite(raw).all():raise ValueError('Invalid recorded XYZ map')
    # This is an explicit format export of the recovered array, not the lost original PCD file.
    header=('# .PCD v0.7\nVERSION 0.7\nFIELDS x y z\nSIZE 4 4 4\nTYPE F F F\nCOUNT 1 1 1\n'
            f'WIDTH {len(raw)}\nHEIGHT 1\nVIEWPOINT 0 0 0 1 0 0 0\nPOINTS {len(raw)}\nDATA binary\n')
    (OUT/'recovered_recorded_map.pcd').write_bytes(header.encode()+raw.astype('<f4').tobytes())
    mesh=np.load(SOURCE/'runtime/scene_meshes.npz');spawn=mesh['spawn'];top=mesh['ground_top']
    z=height_at([spawn[:2]],top)[0]
    if z is None:raise ValueError('Original spawn has no measured ground triangle')
    d=np.arange(-.5,.501,.025);xx,yy=np.meshgrid(d,d);disk=np.c_[xx.ravel(),yy.ravel()]
    disk=disk[np.linalg.norm(disk,axis=1)<=.45+np.sqrt(2)*.0409356725146]
    support=height_at(disk+spawn[:2],top)
    if any(h is None for h in support):raise ValueError('Spawn footprint crosses a measured mesh gap')
    original=E.parse(SOURCE/'runtime/scene.sdf')
    world=E.parse('/home/lzz/cmu_test_20261110/common_sensor/indoor.world');w=world.getroot().find('world')
    for include in list(w.findall('include')):
        if include.findtext('uri')!='model://sun':w.remove(include)
    for name in ['ground','obstacles']:
        model=deepcopy(original.find(f".//world/model[@name='{name}']"))
        dest=OUT/'assets'/(name+'.dae');shutil.copy2(SOURCE/'model_assets/environment'/dest.name,dest)
        for uri in model.findall('.//mesh/uri'):uri.text=dest.as_uri()
        w.append(model)
    world.write(OUT/'recorded_map.world',encoding='unicode')
    local=Path('/home/lzz/cmu_sim_20261110/src/local_planner/launch/local_planner.launch').read_text()
    local=local.replace('pkg="local_planner"','pkg="cmu_local_planner_ht"')
    local=local.replace('<param name="sensorOffsetX"','<param name="ht_enabled" value="true"/>\n    <param name="ht_validity_radius" value="0.45"/>\n    <param name="sensorOffsetX"')
    (OUT/'local_planner.launch.xml').write_text(local)
    manifest={'source_release':recovery['release'],'source_array_sha256':hashlib.sha256((SOURCE/'runtime/local_map.npy').read_bytes()).hexdigest(),
      'source_point_count':len(raw),'source_xyz_min':raw.min(0).tolist(),'source_xyz_max':raw.max(0).tolist(),
      'world_bounds_xy_m':[-15,15,-15,15],'mission_bounds_xy_m':[-13.5,13.5,-13.5,13.5],
      'spawn_xy':spawn[:2].tolist(),'ground_z_at_spawn':z,'sensor_spawn_z':z+.75,
      'historical_scout_base_spawn':spawn.tolist(),'spawn_ground_support_samples':len(support),
      'ground_triangles':len(top),'obstacle_triangles':len(mesh['obstacles']),
      'geometry_policy':'Exact archived meshes; measured ground edge <=0.8m, obstacle voxels 0.16m; holes remain holes. CMU kinematic vehicle replaces archived Scout dynamics.',
      'pcd_export':'Recovered 56849-point XYZ NPY converted losslessly to binary PCD; original standalone PCD not found.',
      'files':{str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file()}}
    (OUT/'SCENE_MANIFEST.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
