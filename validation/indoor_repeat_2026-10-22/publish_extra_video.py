"""Add and verify the derived comparison video without changing sealed data."""
import sys,json,datetime,tempfile,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from archive_legacy_ht_data import release,matches,sha,write

def main():
    tag='ht-sim-20261022-indoor-repeat';src=ROOT/'docs/results/ht_indoor_repeat_2026-10-22/first60_comparison.mp4'
    expected={'name':tag+'-first60.mp4','bytes':src.stat().st_size,'sha256':sha(src)}
    existing={v['name']:v for v in release(tag)['assets']}
    if expected['name'] not in existing:
        with tempfile.TemporaryDirectory(prefix='ht-repeat-video-') as t:
            path=Path(t)/expected['name'];path.hardlink_to(src)
            subprocess.run(['gh','release','upload',tag,str(path),'--repo','CQULzz/HT_Explo'],check=True,timeout=180)
    remote={v['name']:v for v in release(tag)['assets']}
    assert expected['name'] in remote and matches(remote[expected['name']],expected),'Remote video verification failed'
    result={'tag':tag,'release':'https://github.com/CQULzz/HT_Explo/releases/tag/'+tag,
        'asset':expected,'verified_at':datetime.datetime.now().astimezone().isoformat(),
        'scope':'Derived first60s side-by-side comparison, not a fresh experiment or navigation modification. Full raw/results covered separately by stage50.json.'}
    write(ROOT/'docs/experiments/publication_addenda/stage50_video_comparison.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
