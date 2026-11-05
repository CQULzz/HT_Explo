from pathlib import Path
import csv,json,sys,collections,math
R=Path('/home/w_lzz/ht-iterations-20261105/cycle6')
for label in sys.argv[1:]:
 p=R/label;rows=list(csv.DictReader((p/'metrics.csv').open()));completed=[r for r in rows if r['mission_completed']=='1'];r=rows[-1]
 out={'scope':'Read-only telemetry diagnostic, not independent reachable-ground-truth coverage certification. Negative-time startup rows excluded from state counts. Command is requested, not wheel-confirmed.',
 'first_completed_elapsed_s':float(completed[0]['elapsed_sim']) if completed else None,
 'final_execution':r['execution'],'final_runtime_reason':r['runtime_reason'],'final_follower':r['follower'],
 'final_xy_m':[float(r['x']),float(r['y'])],'final_distance_from_scene_origin_xy_m':math.hypot(float(r['x']),float(r['y'])),
 'final_command_vw':[float(r['v_cmd']),float(r['w_cmd'])],
 'nonzero_command_rows_while_completed':sum(abs(float(x['v_cmd']))>1e-3 or abs(float(x['w_cmd']))>1e-3 for x in completed),
 'state_rows':dict(collections.Counter(x['execution'] for x in rows if float(x['elapsed_sim'])>=0)),
 'follower_rows':dict(collections.Counter(x['follower'] for x in rows if float(x['elapsed_sim'])>=0)),
 'final_selection_and_completion_audit':[x for x in (p/'navigation.log').read_text().splitlines() if 'TARE_SELECTION ' in x or 'TARE_COMPLETION ' in x][-4:]}
 (p/'STATE_DIAGNOSTICS.json').write_text(json.dumps(out,indent=2));print(label,json.dumps(out,ensure_ascii=False))
