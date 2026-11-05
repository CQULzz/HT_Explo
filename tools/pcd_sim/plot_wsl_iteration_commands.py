from pathlib import Path
import csv,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path('/home/w_lzz/ht-iterations-20261105');labels=['adapter_120_r04','worker_120_r06','worker_repeat120_r07'];fig,axs=plt.subplots(3,1,figsize=(12,9),sharex=True)
for label in labels:
 rows=[x for x in csv.DictReader((R/label/'metrics.csv').open()) if float(x['elapsed_sim'])>=0];t=np.array([float(x['elapsed_sim']) for x in rows]);dist=np.array([float(x['distance_m']) for x in rows]);axs[0].plot(t,np.gradient(dist,t),label=label,alpha=.75);axs[1].plot(t,[float(x['v_cmd']) for x in rows],label=label,alpha=.75);axs[2].plot(t,[float(x['w_cmd']) for x in rows],label=label,alpha=.75)
for ax,title in zip(axs,['Ground-truth XY path speed, includes settling/slip (m/s)','Command linear X (m/s)','Command angular Z (rad/s)']):ax.set_title(title);ax.grid(alpha=.3);ax.legend(fontsize=8)
axs[-1].set_xlabel('Elapsed simulation seconds');fig.tight_layout();out=R/'reports/worker_repeat120_r07/commands.png';fig.savefig(out,dpi=160);print(out)
