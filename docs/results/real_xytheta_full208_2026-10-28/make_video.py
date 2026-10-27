"""Render a labelled video subset; all full208/probe results remain archived."""
from pathlib import Path
import argparse,json,subprocess,sys,hashlib,shutil
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--ffmpeg',required=True);a=p.parse_args();d=a.data.resolve();v=d/'video_source';v.mkdir(exist_ok=False);(v/'input').mkdir()
 exclusions={}
 for role in ['before','after']:
  source=d/(role+'.json');obj=json.loads(source.read_text());allrows=obj['queries'];obj['queries']=[row for row in allrows if not row['label'].startswith('counterfactual_heading_')]
  exclusions[role]={'source_sha256':sha(source),'full_queries':len(allrows),'video_queries':len(obj['queries']),'omitted_queries':len(allrows)-len(obj['queries'])}
  (v/(role+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
 shutil.copy2(d/'input/metadata.json',v/'input/metadata.json')
 (v/'VIDEO_SOURCE.json').write_text(json.dumps({'scope':'Display only recorded-yaw and explicitly synthetic scenes. Hypothetical heading queries are excluded from video and plotted separately. Synthetic directional probabilities/obstacles are manually constructed, not model predictions. No vehicle or RViz footage.','source_results':exclusions},indent=2)+'\n')
 subprocess.run([sys.executable,str(ROOT/'docs/results/real_xytheta_2026-10-28/render.py'),'--data',str(v),'--output',str(d/'video'),'--ffmpeg',a.ffmpeg],check=True)
if __name__=='__main__':main()
