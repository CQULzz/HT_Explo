#!/usr/bin/env python3
"""Read-only audit of supplied HT archives; no training, torch or API calls."""
import argparse, collections, csv, hashlib, json
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,default=Path('/home/lzz/下载')); ap.add_argument('--output',type=Path,default=Path(__file__).parent/'evidence'); a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
    base=a.root/'original_scout/mini_25_training'; protocol=json.loads((base/'protocol.json').read_text()); result={'sources_root':str(a.root),'splits':{},'historical_curves':[]}; names={}
    for split in ['train','val','test']:
        p=a.root/'data_scout/traversability_sim_label/split_train_val_mini_25'/f'{split}.txt'; labels=collections.Counter(); strata=collections.Counter(); terrains=set(); rows=0
        with p.open() as f:
            for line in f:
                v=line.strip().split(';')
                if len(v)!=8 or v[0] not in ['0','1']: raise ValueError(f'{p}:{rows+1}: invalid schema')
                rows+=1; labels[v[0]]+=1; terrains.add(v[1]); delta=float(v[7]); strata['static_marker' if delta<0 else ('height_range_gt_0.2m' if delta>0.2 else 'height_range_le_0.2m')]+=1
        names[split]=terrains; digest=sha(p)
        result['splits'][split]={'rows':rows,'labels':dict(labels),'height_strata':dict(strata),'terrain_names':len(terrains),'sha256':digest,'matches_archived_protocol':digest==protocol['data']['manifest_sha256'][split]}
    result['terrain_intersection_all_splits']=len(set.intersection(*names.values()))
    pngs={p.stem for p in (a.root/'data_scout/traversability_sim_data_train_height').glob('*.png')}; result['png_count']=len(pngs); result['missing_png_references']=sorted(set.union(*names.values())-pngs)
    result['models']={}
    for model in ['teacher','student']:
        run=base/'runs/formal'/model; data=json.loads((run/'test_metrics.json').read_text()); m=data.get('metrics',data)
        tn,fp,fn,tp=(m['confusion_matrix'][0]+m['confusion_matrix'][1]) if 'confusion_matrix' in m else [m[x] for x in ['tn','fp','fn','tp']]
        result['models'][model]={'source':str(run/'test_metrics.json'),'source_sha256':sha(run/'test_metrics.json'),'weights_sha256':sha(run/'best_epoch_weights.pth'),'n':tn+fp+fn+tp,'accuracy':(tn+tp)/(tn+fp+fn+tp),'unsafe_accepted_rate':fp/(tn+fp),'safe_rejected_rate':fn/(tp+fn),'tn':tn,'fp':fp,'fn':fn,'tp':tp}
    curves=[]
    for f in sorted((a.root/'train_data').rglob('ht_result_dict.txt')):
        if '.ipynb_checkpoints' in f.parts: continue
        try:
            d=json.loads(f.read_text()); points=sorted((float(k),float(v)) for k,v in d.items())
        except (ValueError, AttributeError) as exc:
            result.setdefault('unusable_curve_files',[]).append({'source':str(f.relative_to(a.root)),'reason':str(exc)})
            continue
        if not points:continue
        source=str(f.relative_to(a.root)); result['historical_curves'].append({'source':source,'sha256':sha(f),'points':len(points),'min_accuracy':min(v for k,v in points),'max_accuracy':max(v for k,v in points)})
        curves.extend({'source':source,'height_bias':k,'accuracy':v} for k,v in points)
    with (a.output/'historical_curves.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['source','height_bias','accuracy'],lineterminator='\n');w.writeheader();w.writerows(curves)
    (a.output/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    selected=[r for r in curves if '/sum_train_scout_infer_new1/' in '/'+r['source'] and r['height_bias'] in [-10,0,10]]
    lines=['# 本地通过性证据审计','', '本报告读取已有数据与结果；没有重新训练或重新推理。历史结果不是本次机器人闭环实验。','', '## 已有高度偏移对照','', '|网络（归档名称）|高度偏移|准确率|','|---|---:|---:|']
    for r in selected:
        name=r['source'].split('/')[2].split('_optimizer')[0].replace('train_scout_backbone_nonoise','');lines.append(f'|{name}|{r["height_bias"]:g}|{r["accuracy"]:.4%}|')
    lines+=['','完整来源及 SHA-256 见 audit.json；全部归档曲线见 historical_curves.csv。','', '## Scout 全量测试混淆矩阵','', '|模型|样本数|准确率|危险误放率 FP/(TN+FP)|安全误拒率 FN/(TP+FN)|','|---|---:|---:|---:|---:|']
    for n,m in result['models'].items():lines.append(f'|{n}|{m["n"]}|{m["accuracy"]:.4%}|{m["unsafe_accepted_rate"]:.4%}|{m["safe_rejected_rate"]:.4%}|')
    lines+=['','教师与学生并非改进前后基线；学生使用方向选择/蒸馏协议，不能用教师分数代表八方向部署效果。','', '## 数据核对','']
    for n,s in result['splits'].items():lines.append(f'- {n}: {s["rows"]} 行，类别 {s["labels"]}，与归档协议 SHA-256 一致：{s["matches_archived_protocol"]}；高差分层 {s["height_strata"]}。')
    lines += [f'- PNG {len(pngs)} 张，缺失引用 {len(result["missing_png_references"])}；三个 split 共享 {result["terrain_intersection_all_splits"]} 个地形名称。', '', '## 可支持的结论与边界','', '- 高度偏移实验支持梯度 HT 对整体高程平移的鲁棒性。它不是坡度增大实验，也没有直接给出危险误放率。','- 归档 Scout 三组脚本都指向 mini_25/test.txt，但 shuffle=True、drop_last=True，batch=64 时每轮舍弃 6 行；没有逐样本预测和当年输入哈希，不能当作严格配对的新复现实验。','- 标签文件保留通过/失败、位置、yaw、耗时、横向偏差与局部高差，可直接设计危险误放率、复杂地形分层、方向性评估。标签生成源码含运动到达、姿态安全与耗时/偏差条件；现有包未提供足够原始轨迹来独立重建全部标签。','- mini_25 训练/验证/测试共享地形，不能宣称未见地形泛化；PNG 字节相同也可能因文件名高度比例不同而对应不同物理高程。','- Hunter SE 是另一车辆域，其结果不能直接当作 Scout 的改进结果。','- Untitled.ipynb 无单元格，不提供证据。','', '## 最有价值的下一步','', '冻结相同测试样本，对当前八方向学生、原始高程网络、几何坡度/高差筛选分别输出概率及最终筛选结果；阈值仅在验证集选择。以危险误放率为主指标，同时报告安全误拒率、覆盖率、复杂地形与方向分层。检验未见地形需要重划分地形组并重新训练，不能拿已经看过这些地形的权重冒充独立测试。','']
    (a.output/'REPORT.md').write_text('\n'.join(lines)); print(json.dumps({k:v for k,v in result.items() if k not in ['historical_curves','sources_root']},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
