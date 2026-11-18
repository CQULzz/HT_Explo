from pathlib import Path
import yaml,json
p=Path('/mnt/d/TARE-Native-Campus-20261118/extract.sh');print(repr(p.read_bytes()))
r=Path('/home/lzz/tare_native_campus_repeat_20261118/runs/native_campus_02');print([e['topic_metadata']['name'] for e in yaml.safe_load((r/'bag/metadata.yaml').read_text())['rosbag2_bagfile_information']['topics_with_message_count']]);print((r/'NODES.txt').read_text());print((r/'COMMANDS.json').read_text())
print([(repr(p.name),p.stat().st_size) for p in Path('/mnt/d/TARE-Native-Campus-20261118').glob('*diagnostic*')])
