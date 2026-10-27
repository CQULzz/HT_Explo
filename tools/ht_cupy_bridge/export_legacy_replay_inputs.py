#!/usr/bin/env python3
"""Export only the exact raw elevation/odometry inputs used by offline audit.

The gzip stream contains a format dictionary followed by trusted-local pickle
records (topic, bag receipt ns, original CDR bytes). No ROS nodes are started.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import sqlite3

from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
from cupy_to_ht import decode_elevation_source


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--bag',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--expected-raw-cdr-sha256',required=True)
    a=p.parse_args()
    counts=Counter()
    with a.output.open('xb') as target, gzip.GzipFile(fileobj=target,mode='wb',compresslevel=3,mtime=0) as stream:
        pickle.dump({'format':'ht_native_replay_inputs_v1',
                     'records':'(topic, bag_receipt_ns, original_cdr_bytes)',
                     'source':str(a.bag),'trusted_pickle_only':True},stream,protocol=5)
        for path in sorted(a.bag.glob('*.db3'),key=lambda x:int(x.stem.split('_')[-1])):
            c=sqlite3.connect('file:'+str(path)+'?mode=ro&immutable=1',uri=True)
            topics={i:name for i,name in c.execute('select id,name from topics')
                    if name in ('/elevation_mapping_node/elevation_map_raw','/state_estimation')}
            placeholders=','.join('?' for _ in topics)
            for topic,stamp,data in c.execute(f'select topic_id,timestamp,data from messages where topic_id in ({placeholders}) order by timestamp',tuple(topics)):
                pickle.dump((topics[topic],stamp,data),stream,protocol=5)
                counts[topics[topic]]+=1
            c.close()
            print('exported',path.name,dict(counts),flush=True)
    decoded=Counter();reasons=Counter();h=hashlib.sha256()
    with gzip.open(a.output,'rb') as stream:
        assert pickle.load(stream)['format']=='ht_native_replay_inputs_v1'
        while True:
            try:topic,receipt,data=pickle.load(stream)
            except EOFError:break
            decoded[topic]+=1
            if topic=='/elevation_mapping_node/elevation_map_raw':
                h.update(data)
                try:
                    decode_elevation_source(deserialize_message(data,GridMap))
                    reason='ACCEPTED'
                except (ValueError,TypeError,OverflowError) as e:reason=str(e)
                reasons[reason]+=1
    assert counts==decoded
    assert h.hexdigest()==a.expected_raw_cdr_sha256
    file_hash=hashlib.sha256()
    with a.output.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):file_hash.update(block)
    report=dict(topic_counts=dict(counts),readback_counts=dict(decoded),
                original_raw_map_cdr_sha256=h.hexdigest(),
                matches_experiment_input_digest=True,native_decoder_results=dict(reasons),
                file_bytes=a.output.stat().st_size,file_sha256=file_hash.hexdigest(),
                excluded_topics='Point clouds, TF, chassis status and command topics were not inputs to this HT interface audit; this is not a complete vehicle bag.')
    a.output.with_suffix(a.output.suffix+'.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
