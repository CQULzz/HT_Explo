"""Side-by-side first60s of actual recorded videos; no interpolation."""
import json,hashlib,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import cv2
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/results/ht_indoor_repeat_2026-10-22'
ENC=Path('/home/lzz/.cache/ht-report-tools/python/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2')

def main():
    header=OUT/'comparison_header.png'
    im=Image.new('RGB',(1920,50),(18,27,36));draw=ImageDraw.Draw(im)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',24)
    draw.text((20,9),'PREVIOUS: early return | same runtime code',font=font,fill='#f9b6b6')
    draw.text((980,9),'REPEAT: 600s test | same runtime code',font=font,fill='#a9ecfa');im.save(header)
    old=ROOT/'docs/results/ht_sim_check_2026-10-22/indoor/camera_h264.mp4';new=OUT/'indoor/camera_h264.mp4';movie=OUT/'first60_comparison.mp4'
    command=[str(ENC),'-nostdin','-hide_banner','-v','error','-y','-t','60','-i',str(old),'-t','60','-i',str(new),
        '-loop','1','-framerate','15','-i',str(header),'-filter_complex_threads','1',
        '-filter_complex','[0:v][1:v]hstack=inputs=2[views];[2:v][views]vstack=inputs=2[out]',
        '-map','[out]','-t','60','-r','15','-c:v','libx264','-threads','2','-preset','fast','-crf','25','-pix_fmt','yuv420p','-movflags','+faststart',str(movie)]
    subprocess.run(command,check=True)
    decoded=subprocess.run([str(ENC),'-nostdin','-v','error','-i',str(movie),'-f','null','-'],capture_output=True,timeout=120)
    cap=cv2.VideoCapture(str(movie));fps=cap.get(cv2.CAP_PROP_FPS);count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));cap.release()
    result={'command':command,'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [old,new,header]},
        'full_decode_returncode':decoded.returncode,'fps':fps,'frames':count,'duration_s':count/fps,
        'sha256':hashlib.sha256(movie.read_bytes()).hexdigest(),'scope':'First60 measured seconds at original speed; left previous indoor, right unchanged runtime repeat. Native captured camera plus existing HUD. Not RViz or a fresh navigation experiment.'}
    (OUT/'first60_video_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    assert decoded.returncode==0 and fps==15 and count==900,result
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
