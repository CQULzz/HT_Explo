from pathlib import Path
import json,subprocess,imageio_ffmpeg
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).parent;names=json.loads((O/'FIGURES.json').read_text());font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',25);out=O/'HT_texture_study_charts.mp4';ff=imageio_ffmpeg.get_ffmpeg_exe();cmd=[ff,'-v','error','-n','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','10','-i','-','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(out)];p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=(O/'chart_video_encode.log').open('w'))
for i,name in enumerate(names):
 fig=Image.open(O/'figures'/name).convert('RGB');fig.thumbnail((1900,1000));im=Image.new('RGB',(1920,1080),'#10181d');im.paste(fig,((1920-fig.width)//2,60+(1000-fig.height)//2));d=ImageDraw.Draw(im);d.text((20,12),f'离线诊断图表轮播（不是RViz或实车录像）｜图{i+1}/{len(names)}',font=font,fill='white');data=im.tobytes()
 for _ in range(30):p.stdin.write(data)
p.stdin.close();assert p.wait()==0;subprocess.run([ff,'-v','error','-i',str(out),'-f','null','-'],check=True);(O/'CHART_VIDEO_CHECK.json').write_text(json.dumps({'frames':len(names)*30,'fps':10,'resolution':[1920,1080],'duration_s':len(names)*3,'full_decode_passed':True,'scope':'Static diagnostic figures only, not RViz/robot/simulation recording'},indent=2)+'\n');print(out,flush=True)
