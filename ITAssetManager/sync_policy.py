"""Decide when a stable external revision can safely replace the UI snapshot."""
class SyncPolicy:
    def __init__(self):self.candidate=None;self.baseline=None;self.samples=0
    def observe(self,revision,baseline,busy):
        if baseline!=self.baseline:
            self.baseline=baseline;self.candidate=None;self.samples=0
        if revision==baseline:
            self.candidate=None;self.samples=0;return 'same'
        if revision==self.candidate:self.samples+=1
        else:self.candidate=revision;self.samples=1
        if busy:return 'blocked'
        return 'reload' if self.samples>=2 else 'waiting'
