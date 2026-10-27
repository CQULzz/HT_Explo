"""Resolve explicit hardware modes and independently recorded direction evidence."""
from dataclasses import dataclass
from pathlib import Path
import hashlib, math
import yaml

@dataclass(frozen=True)
class RuntimePolicy:
    mode: str
    follower: bool
    command_bridge: bool
    command_topic: str
    direction_accepted: bool
    mapping_verified: bool
    terrain_validated: bool
    direction_acceptance: str


def direction_evidence(path,weights,channel_order,heading_offset):
    data=yaml.safe_load(Path(path).read_text())
    m=data['mapping'];terrain=data['terrain_response']['validated'] is True
    verified=(m['verified'] is True and list(channel_order)==m['channel_order']
        and math.isclose(float(heading_offset),float(m['heading_offset']),abs_tol=1e-9)
        and hashlib.sha256(Path(weights).read_bytes()).hexdigest()==m['weights_sha256'])
    return verified,terrain and verified


def resolve_runtime(mode='inspect',direction_acceptance='mapping',mapping_verified=False,
                    terrain_validated=False,start_follower='auto',start_command_bridge='auto',
                    command_topic='auto'):
    if mode not in ('inspect','preview','drive'):raise ValueError('run_mode must be inspect, preview or drive')
    if direction_acceptance not in ('mapping','validated'):raise ValueError('direction_acceptance must be mapping or validated')
    follower=mode!='inspect';bridge=mode=='drive'
    for name,value,expected in [('start_follower',start_follower,follower),('start_command_bridge',start_command_bridge,bridge)]:
        if str(value).lower() not in ('auto','true','false'):raise ValueError(f'{name} must be auto, true or false')
        if str(value).lower()!='auto' and (str(value).lower()=='true')!=expected:
            raise ValueError(f'{name} contradicts run_mode={mode}; select the matching run_mode')
    topic=('/ht_real/preview/cmd_vel_stamped' if mode=='preview' else '/ht_real/cmd_vel_stamped') if command_topic=='auto' else command_topic
    if not topic.startswith('/') or topic=='/':raise ValueError('command_topic must be an absolute topic')
    if mode=='preview' and not topic.startswith('/ht_real/preview/'):
        raise ValueError('preview command_topic must stay under /ht_real/preview/')
    accepted=mapping_verified and (direction_acceptance=='mapping' or terrain_validated)
    if mode=='drive' and not accepted:
        raise ValueError('Direction evidence does not satisfy direction_acceptance; inspect the direction validation file')
    return RuntimePolicy(mode,follower,bridge,topic,accepted,mapping_verified,terrain_validated,direction_acceptance)
