"""Bound a fixed, expanded URDF's visual AND collision geometry in base_link.

Mesh bounds use the pinned mesh files, not the URDF's often incomplete collision
tags. Supported source assets: binary STL, metre/Z_UP COLLADA with identity scene
instances. Unsupported geometry/scene transforms fail instead of underbounding.
"""
from pathlib import Path
import argparse, hashlib, itertools, json, struct, xml.etree.ElementTree as ET
import numpy as np

def transform(origin):
    xyz=np.fromstring(origin.get('xyz','0 0 0'),sep=' ') if origin is not None else np.zeros(3)
    r,p,y=np.fromstring(origin.get('rpy','0 0 0'),sep=' ') if origin is not None else np.zeros(3)
    cr,sr,cp,sp,cy,sy=np.cos(r),np.sin(r),np.cos(p),np.sin(p),np.cos(y),np.sin(y)
    t=np.eye(4);t[:3,:3]=[[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr],[sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr],[-sp,cp*sr,cp*cr]];t[:3,3]=xyz
    return t

def mesh_vertices(path):
    data=path.read_bytes()
    if path.suffix.lower()=='.stl':
        count=struct.unpack_from('<I',data,80)[0]
        if len(data)!=84+50*count:raise ValueError('Expected binary STL: '+str(path))
        records=np.frombuffer(data,offset=84,dtype=np.dtype([('normal','<f4',(3,)),('v','<f4',(3,3)),('attr','<u2')]))
        return records['v'].reshape(-1,3).astype(float)
    if path.suffix.lower()!='.dae':raise ValueError('Unsupported mesh: '+str(path))
    doc=ET.fromstring(data);ns={'c':doc.tag.split('}')[0][1:]}
    if float(doc.find('c:asset/c:unit',ns).get('meter'))!=1 or doc.findtext('c:asset/c:up_axis',namespaces=ns)!='Z_UP':raise ValueError('Expected metre/Z_UP mesh')
    for node in doc.findall('.//c:visual_scene//c:node',ns):
        for child in node:
            kind=child.tag.split('}')[-1]
            if kind=='matrix':
                if not np.allclose(np.fromstring(child.text,sep=' ').reshape(4,4),np.eye(4),atol=1e-9):raise ValueError('Nonidentity COLLADA scene matrix')
            elif kind in ('translate','rotate','scale','lookat','skew'):raise ValueError('Unsupported COLLADA scene transform')
    vertices=[]
    for mesh in doc.findall('.//c:geometry/c:mesh',ns):
        for vi in mesh.findall('c:vertices/c:input',ns):
            if vi.get('semantic')!='POSITION':continue
            source=mesh.find("c:source[@id='%s']"%vi.get('source')[1:],ns)
            accessor=source.find('c:technique_common/c:accessor',ns)
            stride=int(accessor.get('stride','1'));offset=int(accessor.get('offset','0'));count=int(accessor.get('count'))
            a=np.fromstring(source.find('c:float_array',ns).text,sep=' ')
            if stride<3:raise ValueError('Position accessor lacks XYZ')
            vertices.append(a[offset:offset+count*stride].reshape(count,stride)[:,:3])
    if not vertices:raise ValueError('No POSITION data')
    return np.concatenate(vertices)

def derive(urdf,package_dir,base='base_link'):
    tree=ET.parse(urdf).getroot();links={l.get('name'):l for l in tree.findall('link')};parents={}
    for j in tree.findall('joint'):
        if j.get('type')!='fixed':raise ValueError('Only fixed joints supported: '+j.get('name'))
        parents[j.find('child').get('link')]=(j.find('parent').get('link'),transform(j.find('origin')))
    def absolute(name):
        if name not in parents:return np.eye(4)
        parent,t=parents[name];return absolute(parent)@t
    tobase=np.linalg.inv(absolute(base));parts=[];files={str(urdf):hashlib.sha256(urdf.read_bytes()).hexdigest()}
    for name,link in links.items():
        for tag in ('visual','collision'):
            for item in link.findall(tag):
                t=tobase@absolute(name)@transform(item.find('origin'));geometry=item.find('geometry');kind=list(geometry)[0];meshfile=None
                if kind.tag=='mesh':
                    uri=kind.get('filename');prefix='package://ele_scout_kit/'
                    if not uri.startswith(prefix):raise ValueError('Unresolved package URI: '+uri)
                    meshfile=package_dir/uri[len(prefix):];v=mesh_vertices(meshfile)*np.fromstring(kind.get('scale','1 1 1'),sep=' ')
                    files[str(meshfile)]=hashlib.sha256(meshfile.read_bytes()).hexdigest()
                    v=v@t[:3,:3].T+t[:3,3];lo,hi=v.min(0),v.max(0)
                elif kind.tag=='box':
                    half=np.fromstring(kind.get('size'),sep=' ')/2;extent=np.abs(t[:3,:3])@half;lo,hi=t[:3,3]-extent,t[:3,3]+extent
                elif kind.tag=='cylinder':
                    radius=float(kind.get('radius'));half=float(kind.get('length'))/2
                    extent=radius*np.sqrt(t[:3,0]**2+t[:3,1]**2)+half*np.abs(t[:3,2]);lo,hi=t[:3,3]-extent,t[:3,3]+extent
                else:raise ValueError('Unsupported geometry: '+kind.tag)
                if not np.isfinite([lo,hi]).all():raise ValueError('Nonfinite mesh')
                parts.append({'link':name,'kind':tag,'mesh':str(meshfile) if meshfile else None,'min_xyz':lo.tolist(),'max_xyz':hi.tolist()})
    lo=np.min([p['min_xyz'] for p in parts],0);hi=np.max([p['max_xyz'] for p in parts],0)
    return {'base_frame':base,'min_xyz':lo.tolist(),'max_xyz':hi.tolist(),'size_xyz':(hi-lo).tolist(),'center_xyz':((hi+lo)/2).tolist(),
            'required_support_radius':float(np.hypot(np.maximum(abs(lo[0]),abs(hi[0])),np.maximum(abs(lo[1]),abs(hi[1])))),
            'parts':parts,'source_sha256':files,'scope':'Union of all pinned URDF visual and collision geometry, fixed transforms applied; no guessed attachment dimensions or padding.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('urdf',type=Path);p.add_argument('--package-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=derive(a.urdf,a.package_dir);a.output.write_text(json.dumps(result,indent=2));print(json.dumps({k:result[k] for k in ('min_xyz','max_xyz','size_xyz','required_support_radius')},indent=2))
