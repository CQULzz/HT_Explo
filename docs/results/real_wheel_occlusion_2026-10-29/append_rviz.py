from pathlib import Path
import shutil,json,subprocess
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
from PIL import Image
O=Path(__file__).parent;src=O/'rviz_after/preview_0178.png';assert src.is_file();shutil.copy2(O/'all_comparisons.pdf',O/'core_figures.pdf');font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc');plt.rcParams['font.family']='Noto Sans CJK JP';fig,ax=plt.subplots(figsize=(16,10));ax.imshow(Image.open(src));ax.axis('off');fig.suptitle('修后实际RViz：原始录包离线重算回放，非实车控制录像',fontsize=17);fig.text(.5,.035,'四视图：估计的全局历史高程、局部高程、八方向HT、半透明XYθ体素；青色线是录包轨迹，不是规划路径。',ha='center',fontsize=12);fig.tight_layout(rect=[0,.05,1,.95]);fig.savefig(O/'figures/07_actual_rviz_preview.png',dpi=140);fig.savefig(O/'rviz_preview.pdf');plt.close(fig);subprocess.run(['pdfunite',str(O/'core_figures.pdf'),str(O/'rviz_preview.pdf'),str(O/'all_comparisons.pdf')],check=True);names=json.load(open(O/'FIGURES.json'));names.append('07_actual_rviz_preview.png');(O/'FIGURES.json').write_text(json.dumps(names,indent=2)+'\n')
