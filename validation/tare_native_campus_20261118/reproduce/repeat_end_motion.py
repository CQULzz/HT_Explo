from pathlib import Path
import json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path('/home/lzz/tare_native_campus_repeat_20261118/runs/native_campus_02');rows=list(csv.DictReader((r/'observations/metrics.csv').open()));a=lambda k:np.array([float(v[k]) for v in rows]);t=a('elapsed_s');x=a('x')-0.0*np.cos(a('yaw'));y=a('y')-0.0*np.sin(a('yaw'));speed=np.hypot(np.diff(x),np.diff(y))/np.diff(t);i=np.argmin(abs(t-(t[-1]-120)));j=np.argmin(abs(t-(t[-1]-30)));result={'actual_acquisition_last_sample_s':float(t[-1]),'last120s_recorded_distance_m':float(a('distance_m')[-1]-a('distance_m')[i]),'last30s_recorded_distance_m':float(a('distance_m')[-1]-a('distance_m')[j]),'last_sample_velocity_command_linear':float(a('cmd_linear')[-1]),'last_sample_velocity_command_angular':float(a('cmd_angular')[-1]),'last_sample_finish':rows[-1]['finish'],'scope':'Original sampled data only, no repeated video frames or synthetic terminal pause'};(r/'END_MOTION_CHECK.json').write_text(json.dumps(result,indent=2))
fig,axes=plt.subplots(3,1,figsize=(12,8),sharex=True);mask=t>=t[-1]-120;axes[0].plot(t[1:][mask[1:]],speed[mask[1:]],label='Measured base XY speed');axes[0].set_ylabel('m/s');axes[0].legend();axes[1].plot(t[mask],a('cmd_linear')[mask],label='Command linear');axes[1].plot(t[mask],a('cmd_angular')[mask],label='Command angular');axes[1].legend();axes[2].plot(t[mask],a('distance_m')[mask]-a('distance_m')[i],label='Distance since window start');axes[2].set_ylabel('m');axes[2].legend();axes[2].set_xlabel('Actual acquisition wall time (s)')
for ax in axes:ax.grid(alpha=.2);ax.axvline(t[-1],color='red',ls='--')
fig.suptitle('Last120s of actual acquisition; red line is data boundary, no video padding');fig.tight_layout();fig.savefig(r/'end_motion.png',dpi=150);plt.close(fig);print(json.dumps(result))
