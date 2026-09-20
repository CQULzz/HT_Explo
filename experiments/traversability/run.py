#!/usr/bin/env python3
"""One command: cached real-C++ scoring, deterministic fixtures, CSV/JSON/report.

Optional real prediction CSV: sample_id,scenario_id,heading_deg,p,label
label=1 passable, label=0 hazardous; blank p means unknown. No LLM needed.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def section(length, p=.95, slope=0., cross=0., step=0., roughness=0., valid=True):
    return dict(length=length, probabilities=[p]*8, slope=slope, cross=cross,
                step=step, roughness=roughness, valid=valid)


def fixtures():
    uphill = section(4, .1, slope=22)
    uphill['probabilities'][0] = .04
    uphill['probabilities'][4] = .85
    obstacles = {
        'flat_control': section(4),
        'directional_ramp': uphill,
        'cross_slope': section(4, .05, cross=18),
        'high_step': section(2, .02, step=.30),
        'rough_ground': section(4, .07, roughness=.20),
        'unknown_patch': section(4, valid=False),
        'danger_only': section(4, .01, slope=30),
        'false_safe_input': section(4, .95, step=.30),
        'false_alarm_input': section(4, .03),
    }
    tasks = []
    for name, obstacle in obstacles.items():
        for rotation in range(8):
            for reverse in (False, True):
                routes = [[section(3), obstacle, section(3)]]
                if name != 'danger_only':
                    routes.append([section(16)])
                routes = json.loads(json.dumps(routes))
                for route in routes:
                    for s in route:
                        original = s['probabilities']
                        s['probabilities'] = [original[(k-rotation)%8] for k in range(8)]
                        s['heading'] = ((rotation + (4 if reverse else 0))*45) % 360
                        if reverse:
                            s['slope'] *= -1
                    if reverse:
                        route.reverse()
                tasks.append(dict(id=f'{name}_rot{rotation}_{"reverse" if reverse else "forward"}',
                                  scenario=name, routes=routes))
    return tasks


def safe(s, limits):
    # Ground truth is defined from geometry, never by thresholding input P.
    return (-limits['downhill_deg'] <= s['slope'] <= limits['uphill_deg']
            and abs(s['cross']) <= limits['cross_slope_deg']
            and s['step'] <= limits['step_m'] and s['roughness'] <= limits['roughness_m'])


def compile_bridge(output):
    files = [HERE/'core_bridge.cpp', ROOT/'src/tare_planner/include/ht_cost/ht_cost_core.h']
    digest = hashlib.sha256(b''.join(p.read_bytes() for p in files)).hexdigest()
    binary = output/f'core_bridge_{digest[:12]}'
    if not binary.exists():
        subprocess.run(['c++', '-std=c++17', '-O2', '-I', str(ROOT/'src/tare_planner/include'),
                        str(files[0]), '-o', str(binary)], check=True)
    return binary, digest


def score(tasks, binary):
    routes = [route for task in tasks for route in task['routes']]
    lines = [str(len(routes))]
    for route in routes:
        lines.append(str(len(route)))
        for s in route:
            lines.append(' '.join(map(str, [s['length'], s['heading'], s['slope'], int(s['valid']),
                                           *s['probabilities']])))
    result = subprocess.run([str(binary)], input='\n'.join(lines)+'\n', text=True,
                            capture_output=True, check=True)
    rows = [list(map(float, line.split())) for line in result.stdout.splitlines()]
    assert len(rows) == len(routes) and all(len(r) == 9 for r in rows)
    iterator = iter(rows)
    for task in tasks:
        task['scores'] = [next(iterator) for _ in task['routes']]


def classification(rows, threshold):
    tp = tn = fp = fn = unknown = 0
    for row in rows:
        label, p = int(row['label']), row['p']
        if label not in (0, 1):
            raise ValueError('label must be 0 or 1')
        if p is None:
            unknown += 1
            continue
        if not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError('probability must be finite and in [0, 1]')
        prediction = p >= threshold
        tp += prediction and label == 1
        fp += prediction and label == 0
        tn += not prediction and label == 0
        fn += not prediction and label == 1
    ratio = lambda a,b: a/b if b else None
    return dict(n=len(rows), unknown=unknown, known_fraction=ratio(len(rows)-unknown,len(rows)),
                tp=tp,tn=tn,fp=fp,fn=fn, unsafe_false_accept_rate=ratio(fp,fp+tn),
                safe_false_reject_rate=ratio(fn,fn+tp), precision=ratio(tp,tp+fp),
                recall=ratio(tp,tp+fn), f1=ratio(2*tp,2*tp+fp+fn))


def real_predictions(path):
    with path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    if not rows or not {'sample_id','scenario_id','heading_deg','p','label'} <= rows[0].keys():
        raise ValueError('CSV requires sample_id,scenario_id,heading_deg,p,label and at least one row')
    seen = set()
    for row in rows:
        key = (row['scenario_id'],row['sample_id'],float(row['heading_deg']))
        if key in seen:
            raise ValueError(f'Duplicate sample/direction: {key}')
        seen.add(key)
        row['p'] = float(row['p']) if row['p'].strip() else None
        row['label'] = int(row['label'])
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'results')
    parser.add_argument('--predictions', type=Path, help='Real labeled prediction CSV; no inference is fabricated')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = json.loads((HERE/'config.json').read_text())
    assert config['weights'] == [0,.5,1,2,5], 'Update C++ total() columns when changing the weight grid'
    binary, digest = compile_bridge(output)
    tasks = fixtures()
    score(tasks, binary)
    decisions, labels = [], []
    for task in tasks:
        truths = [all(safe(s,config['limits']) for s in route) for route in task['routes']]
        safe_lengths = [r[0] for r,ok in zip(task['scores'],truths) if ok]
        for index, route in enumerate(task['routes']):
            for si, s in enumerate(route):
                labels.append(dict(sample_id=f"{task['id']}_{index}_{si}", scenario_id=task['scenario'],
                                   heading_deg=s['heading'], label=int(safe(s,config['limits'])),
                                   p=s['probabilities'][int(s['heading']/45)] if s['valid'] else None))
        for mode, weight_index in [('baseline',None)] + [(f'ht_w{w:g}',i) for i,w in enumerate(config['weights'])]:
            values = [r[0] if weight_index is None else r[4+weight_index] for r in task['scores']]
            chosen = min(range(len(values)), key=values.__getitem__)
            row = task['scores'][chosen]
            known = bool(row[3])
            # Only data availability is checked here. Low P is not a production hard veto.
            permitted = mode == 'baseline' or known
            danger_m = sum(s['length']/math.cos(math.radians(s['slope']))
                           for s in task['routes'][chosen] if not safe(s,config['limits']))
            decisions.append(dict(task=task['id'],scenario=task['scenario'],mode=mode,
                                  selected_route=chosen, selected_length_m=row[0],risk_integral=row[1],
                                  unknown_length_m=row[2], abstract_data_gate_permits=permitted,
                                  unsafe_route_selected=not truths[chosen],
                                  hazardous_route_permitted=permitted and not truths[chosen],
                                  hazardous_exposure_m=danger_m if permitted else 0.,
                                  safe_task_rejected=bool(safe_lengths) and not permitted,
                                  safe_detour_ratio=(row[0]/min(safe_lengths)
                                                     if permitted and truths[chosen] and safe_lengths else None)))
    groups = {}
    for mode in sorted({r['mode'] for r in decisions}):
        selected = [r for r in decisions if r['mode']==mode]
        groups[mode] = dict(tasks=len(selected),
            hazardous_route_permitted=sum(r['hazardous_route_permitted'] for r in selected),
            safe_task_rejected=sum(r['safe_task_rejected'] for r in selected),
            hazardous_exposure_m=sum(r['hazardous_exposure_m'] for r in selected))
    pred_rows = real_predictions(args.predictions) if args.predictions else labels
    classification_results = {str(t):classification(pred_rows,t) for t in config['threshold_sweep']}
    per_scenario = {name:classification([r for r in pred_rows if r['scenario_id']==name],
                                      config['classification_threshold'])
                    for name in sorted({r['scenario_id'] for r in pred_rows})}
    summary = dict(kind=config['label'],config=config,core_sha256=digest,
                   runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   config_sha256=hashlib.sha256((HERE/'config.json').read_bytes()).hexdigest(),
                   prediction_source=str(args.predictions.resolve()) if args.predictions else 'synthetic_fixture_inputs',
                   real_prediction_csv_sha256=(hashlib.sha256(args.predictions.read_bytes()).hexdigest()
                                               if args.predictions else None),
                   routing_source='synthetic_road_sections_only',groups=groups,
                   classification=classification_results,classification_per_scenario=per_scenario)
    for name, value in [('summary.json',summary),('fixtures.json',tasks)]:
        (output/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
    for name, rows in [('decisions.csv',decisions),('classification_samples.csv',pred_rows)]:
        with (output/name).open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    report = ['# 道路通过性固定评测','',
        '**本次路线测试为合成路段上的真实 C++ 代价核心测试，不是车辆物理仿真，也不是实际通过成功率。**',
        '坡度、横坡、台阶与粗糙度定义独立的几何标签；车辆阈值仅为测试假设，见 config.json。',
        '概率是指定输入，包含错误高估、错误低估、未知和只剩危险路的负例。旋转/反向变体是确定性压力测试，不是独立统计样本。','',
        '| 模式 | 决策数 | 已知危险路线被选数 | 抽象整段门控拒绝数 | 危险路段总长度 / m |',
        '|---|---:|---:|---:|---:|']
    for mode,g in groups.items():
        report.append(f"| {mode} | {g['tasks']} | {g['hazardous_route_permitted']} | {g['safe_task_rejected']} | {g['hazardous_exposure_m']:.2f} |")
    report += ['', '整段门控是明确的测试假设：选中路线有未知段就记为不执行。真实节点只检查当前短 waypoint，可能先前进再重规划；因此这里不是实际任务拒绝率。未运行 ROS 的几何碰撞、视线、footprint 或 TSP。',
        '已知危险路线被选数越少越好；同时检查 decisions.csv 的 safe_detour_ratio，防止无限绕路或一律拒绝造成虚假改善。', '',
        '## 输入概率分类能力', '',f"数据来源：`{summary['prediction_source']}`。",
        '以下阈值仅用于离线评分，**没有把这个阈值加入现有规划器**。未知输入单独统计，不当作正确拒绝。', '',
        '| 阈值 | 危险误放行 FP/(FP+TN) | 可通行误拒绝 FN/(FN+TP) | 已知输入占比 | F1 |',
        '|---|---:|---:|---:|---:|']
    fmt=lambda x: 'N/A' if x is None else f'{x:.3f}'
    for t,m in classification_results.items():
        report.append(f"| {t} | {fmt(m['unsafe_false_accept_rate'])} | {fmt(m['safe_false_reject_rate'])} | {fmt(m['known_fraction'])} | {fmt(m['f1'])} |")
    report += ['', '按场景细分见 summary.json 的 classification_per_scenario；生产阈值应在独立标定集选择，再在未参与调参的测试集评价。', '',
        '## 结论边界', '',
        '当前实现是软风险排序。仅有危险路线或输入错误地给出高概率时，提高权重不能保证拒绝通行。',
        '这些数据检验接口、方向和权重行为；只有接入真实预测与独立车辆通过标签后，才可报告真实模型的筛选精度。',
        '后续物理验证应使用陡坡/横坡/台阶地形，记录实际成功率、碰撞/倾覆、危险暴露和绕行代价；本脚本不伪造这些结果。']
    (output/'REPORT.md').write_text('\n'.join(report)+'\n')
    print(json.dumps(groups,ensure_ascii=False,indent=2))
    print(f'Report: {output/"REPORT.md"}')


if __name__ == '__main__':
    main()
