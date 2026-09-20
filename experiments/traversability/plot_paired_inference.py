#!/usr/bin/env python3
"""Render actual paired inference results and report."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
root=Path(__file__).parent/'paired_results';d=json.loads((root/'summary.json').read_text());m=d['metrics'];font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
plt.rcParams['font.family']=font.get_name();plt.rcParams['axes.unicode_minus']=False
names={'gradient_ht':'梯度 HT（单方向教师）','raw_height_vit':'原始高程 ViT'};colors={'gradient_ht':'#167d9a','raw_height_vit':'#e58635'}
fig,axes=plt.subplots(1,3,figsize=(15,5))
for ax,key,title in zip(axes,['accuracy','unsafe_accepted_rate','safe_rejected_rate'],['分类准确率 ↑','危险误放率 ↓','安全误拒率 ↓']):
    for name in names:
        values=[m[f'{name}:{b}']['all'][key]*100 for b in [-1,0,1]]
        ax.plot([-1,0,1],values,'o-',color=colors[name],label=names[name],linewidth=2.5)
        for x,y in zip([-1,0,1],values):ax.annotate(f'{y:.1f}%',(x,y),xytext=(0,10 if y >= m[f"{next(n for n in names if n != name)}:{x}"]['all'][key]*100 else -18),textcoords='offset points',ha='center',fontsize=10)
    ax.set(title=title,xlabel='整体高程偏移（m）',ylabel='比例（%）',xticks=[-1,0,1],ylim=(-5,105));ax.grid(alpha=.2)
axes[0].legend(loc='lower left',fontsize=9);fig.suptitle('Scout 实际推理对比 · 固定随机测试样本 2,048 条 · 相同样本 / 阈值 0.5',fontsize=16)
fig.text(.5,.015,'已有权重重新推理；训练与测试共享地形；高度偏移不改变坡度；不是学生模型或闭环驾驶结果。',ha='center',fontsize=10)
fig.tight_layout(rect=(0,.05,1,.93));fig.savefig(root/'comparison.png',dpi=180);fig.savefig(root/'comparison.pdf');plt.close(fig)
lines=['# Scout 实际配对推理实验','', '固定 seed=20260921，从 290054 条 test 标签均匀无放回抽取 2048 条。两个归档模型均严格加载原始 best_epoch_weights；不训练、不选样本、不调阈值，阈值固定 0.5。偏移在高程图提取 patch 前加入，patch 为原始 29×29 方向输入。','', '|偏移 m|模型|准确率|危险误放率|安全误拒率|','|---:|---|---:|---:|---:|']
for b in [-1,0,1]:
    for name in names:
        q=m[f'{name}:{b}']['all'];lines.append(f'|{b}|{names[name]}|{q["accuracy"]:.2%}|{q["unsafe_accepted_rate"]:.2%}|{q["safe_rejected_rate"]:.2%}|')
lines+=['','## 局部高差 > 0.2 m 子集（原始标签末列，非安全阈值）','','|偏移 m|模型|样本数|准确率|危险误放率|安全误拒率|','|---:|---|---:|---:|---:|---:|']
for b in [-1,0,1]:
    for name in names:
        q=m[f'{name}:{b}']['height_range_gt_0.2m'];lines.append(f'|{b}|{names[name]}|{q["n"]}|{q["accuracy"]:.2%}|{q["unsafe_accepted_rate"]:.2%}|{q["safe_rejected_rate"]:.2%}|')
lines+=['','## 复现与边界','','```bash',"PYTHONPATH='/home/lzz/my test/validation/evidence-deps' python3 experiments/traversability/run_paired_inference.py",'python3 experiments/traversability/plot_paired_inference.py','```','','推理依赖 torch、numpy、opencv、scikit-image；本次 CPU 运行。原始目录只读。samples.txt 冻结样本，predictions.csv 保存每条模型概率，summary.json 记录权重/输入/代码哈希和各组混淆矩阵。','', '这检验已有两套模型的筛选性能与高度平移鲁棒性，不是仅改变梯度层的严格控制消融，也不是八方向学生的部署成绩。mini_25 共享地形，不能宣称未见地形泛化。未进行统计显著性检验。样本只抽取一次，未因结果不利更换样本。','']
(root/'REPORT.md').write_text('\n'.join(lines))
