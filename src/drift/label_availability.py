"""Release labels on a simulated window clock."""
from collections import defaultdict


class LabelSchedule:
    def __init__(self,delay):
        if delay<0:raise ValueError('Label delay must be nonnegative')
        self.delay=delay
        self.pending=defaultdict(list)

    def predict(self,window,identifier,error):
        self.pending[window+self.delay].append((identifier,error))

    def release(self,window):
        released=[]
        for time in sorted(k for k in self.pending if k<=window):
            released.extend((identifier,error,time) for identifier,error in self.pending.pop(time))
        return released
