#!/usr/bin/env python3
"""Actual paired checkpoint inference on a frozen Scout test subset, no training."""
import argparse,csv,hashlib,importlib.util,json,sys,time
from pathlib import Path
import numpy as np
import torch

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def metrics(y,p):
    a=p>=.5; y=y.astype(bool); tn=int((~y&~a).sum());fp=int((~y&a).sum());fn=int((y&~a).sum());tp=int((y&a).sum())
    return dict(n=len(y),tn=tn,fp=fp,fn=fn,tp=tp,accuracy=(tn+tp)/len(y),unsafe_accepted_rate=fp/(tn+fp) if tn+fp else None,safe_rejected_rate=fn/(fn+tp) if fn+tp else None)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path('/home/lzz/下载'));ap.add_argument('--samples',type=int,default=2048);ap.add_argument('--output',type=Path,default=Path(__file__).parent/'paired_results');args=ap.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(4);torch.manual_seed(20260921);sys.path.insert(0,str(args.root/'original_scout'))
    from mtramap.patches import HeightMapSource,extract_rotated_patch,parse_head_manifest_line
    source=args.root/'ht_tra_classification_scout_mapping/nets/vision_transformer.py';spec=importlib.util.spec_from_file_location('archived_vit',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    manifest=args.root/'data_scout/traversability_sim_label/split_train_val_mini_25/test.txt';lines=manifest.read_text().splitlines();rng=np.random.default_rng(20260921);indices=np.sort(rng.choice(len(lines),size=min(args.samples,len(lines)),replace=False)); chosen=[lines[i] for i in indices];(out/'samples.txt').write_text('\n'.join(chosen)+'\n')
    records=[parse_head_manifest_line(s) for s in chosen];y=np.array([r[0] for r in records]);ranges=np.array([r[7] for r in records]);maps=HeightMapSource(args.root/'data_scout/traversability_sim_data_train_height',cache_size=1600)
    models={};weights={}
    for name,tag,ctor in [('gradient_ht','nonoiseht_vit_b_16_grad_1_scout_optimizer',module.ht_vit_b_16_grad_1_scout),('raw_height_vit','nonoiseht_vit_b_16_optimizer',module.ht_vit_b_16)]:
        candidates=sorted(p for p in (args.root/'train_data/sum_train_scout').rglob('best_epoch_weights.pth') if tag in p.parent.name)
        hashes={digest(p) for p in candidates}
        if len(hashes)!=1:raise ValueError(f'ambiguous weights {name}: {candidates}')
        p=candidates[0];model=ctor(input_shape=[29,29],num_classes=2);model.load_state_dict(torch.load(p,map_location='cpu',weights_only=True),strict=True);model.eval();models[name]=model;weights[name]={'path':str(p),'sha256':digest(p)}
    result={'protocol':{'seed':20260921,'sampling':'uniform without replacement from test; no selection by outcome','manifest_sha256':digest(manifest),'samples_sha256':digest(out/'samples.txt'),'source_sha256':digest(source),'runner_sha256':digest(Path(__file__)),'torch':torch.__version__,'device':'cpu','threshold':.5,'offsets_m':[-1,0,1],'note':'Existing best-validation checkpoints. Same samples, full batches including remainder. Shared-terrain test, not unseen-terrain generalization or closed-loop driving.'},'weights':weights,'metrics':{}}
    started=time.time()
    with (out/'predictions.csv').open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['test_line','terrain','yaw_rad','height_range_m','label','offset_m','model','p_passable'])
        for offset in [-1,0,1]:
            patches=np.stack([extract_rotated_patch(maps.get(r[1])+offset,r[2],r[3],r[4],29) for r in records])[:,None]
            for name,model in models.items():
                predictions=[]
                with torch.inference_mode():
                    for start in range(0,len(y),16):
                        predictions.extend(torch.softmax(model(torch.from_numpy(patches[start:start+16])),dim=-1)[:,1].tolist())
                p=np.array(predictions);groups={'all':np.ones(len(y),bool),'height_range_gt_0.2m':ranges>.2,'height_range_le_0.2m':(ranges>=0)&(ranges<=.2),'static_marker':ranges<0};result['metrics'][f'{name}:{offset}']={g:metrics(y[mask],p[mask]) for g,mask in groups.items() if mask.any()}
                for idx,r,prob in zip(indices,records,p):w.writerow([int(idx)+1,r[1],r[4],r[7],r[0],offset,name,prob])
                f.flush(); print(name,offset,result['metrics'][f'{name}:{offset}']['all'],f'elapsed={time.time()-started:.1f}s',flush=True)
                (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    result['elapsed_seconds']=time.time()-started;(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
