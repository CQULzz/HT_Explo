"""Read-only experiment termination; never publishes navigation commands."""
import collections
import math


class MissionStopRule:
    def __init__(self, initial_base, home_radius=.5, hold_s=20., blocked_s=300.):
        self.initial_base = tuple(initial_base)
        self.home_radius, self.hold_s, self.blocked_s = home_radius, hold_s, blocked_s
        self.home_since = None
        self.home_anchor = None
        self.history = collections.deque()
        self.outcome = 'RUNNING'
        self.first_finish_s = None

    def update(self, elapsed, base, command, finish, fresh, volume):
        if self.outcome != 'RUNNING':
            return self.outcome
        if finish and self.first_finish_s is None:
            self.first_finish_s = elapsed
        near_home = math.dist(base, self.initial_base) <= self.home_radius
        stopped_command = abs(command[0]) < .01 and abs(command[1]) < .01
        if finish and fresh and near_home and stopped_command:
            if self.home_since is None or math.dist(base, self.home_anchor) > .05:
                self.home_since, self.home_anchor = elapsed, tuple(base)
            if elapsed-self.home_since >= self.hold_s:
                self.outcome = 'RETURNED_AND_STOPPED'
        else:
            self.home_since = self.home_anchor = None

        self.history.append((elapsed, tuple(base), bool(finish), float(volume), bool(fresh)))
        while len(self.history)>1 and self.history[1][0] <= elapsed-self.blocked_s:
            self.history.popleft()
        # This is an explicit failure, never a substitute for task completion.
        # A new finish phase or useful new views reset the evidence interval.
        if self.outcome == 'RUNNING' and self.history and elapsed-self.history[0][0] >= self.blocked_s:
            origin = self.history[0][1]
            persistent = all(math.dist(p, origin) <= .15 and f == bool(finish) and ok
                             for _, p, f, _, ok in self.history)
            if persistent and volume-self.history[0][3] <= 50.:
                self.outcome = 'PERSISTENT_BLOCKED'
        return self.outcome

    def status(self, elapsed, base):
        return {'outcome': self.outcome, 'elapsed_s': elapsed,
                'base_xy': list(base),
                'distance_to_initial_m': math.dist(base, self.initial_base),
                'first_finish_elapsed_s': self.first_finish_s,
                'home_hold_elapsed_s': 0. if self.home_since is None else elapsed-self.home_since,
                'criteria': {'home_radius_m': self.home_radius,
                             'stationary_hold_s': self.hold_s,
                             'persistent_block_failure_s': self.blocked_s}}
