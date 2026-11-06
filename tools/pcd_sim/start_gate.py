"""Readiness policy for simulation starts, independent of ROS transports."""
import math


class StartGate:
    def __init__(self, required, max_age_s=1., hold_s=1.):
        if not required or max_age_s <= 0 or hold_s < 0:
            raise ValueError('Invalid start gate policy')
        if not all(math.isfinite(x) for x in (max_age_s, hold_s)):
            raise ValueError('Start gate times must be finite')
        self.required = tuple(required)
        self.max_age_s = max_age_s
        self.hold_s = hold_s
        self.latest = {}
        self.ready_since = None
        self.previous_now = None
        self.clock_fault = False
        self.started = False

    def observe(self, name, source_s, receipt_s):
        if name not in self.required or not all(math.isfinite(x) for x in (source_s, receipt_s)):
            return
        self.latest[name] = (source_s, receipt_s)

    def evaluate(self, now_s, wall_s, boundaries_delivered):
        if self.previous_now is not None and now_s < self.previous_now:
            self.clock_fault = True
        self.previous_now = now_s
        missing = [name for name in self.required if name not in self.latest]
        stale = [name for name, (source, receipt) in self.latest.items()
                 if not (0 <= now_s-source <= self.max_age_s and
                         0 <= wall_s-receipt <= self.max_age_s)]
        reason = 'READY'
        if self.clock_fault or now_s <= 0:
            reason = 'CLOCK_INVALID'
        elif not boundaries_delivered:
            reason = 'BOUNDARY_WAIT'
        elif missing:
            reason = 'INPUT_MISSING'
        elif stale:
            reason = 'INPUT_STALE'
        if reason != 'READY':
            self.ready_since = None
        elif self.ready_since is None:
            self.ready_since = now_s
        eligible = reason == 'READY' and now_s-self.ready_since >= self.hold_s
        release = eligible and not self.started
        self.started = self.started or release
        return {'reason': reason, 'missing': missing, 'stale': stale,
                'ready_since_sim_s': self.ready_since, 'release': release,
                'started': self.started, 'sim_time_s': now_s,
                'sources': {name: value[0] for name, value in self.latest.items()}}
