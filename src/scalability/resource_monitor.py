"""Sample disjoint process RSS; configured heap is never reported as RSS."""
import os,time,threading,platform,subprocess
from pathlib import Path
class Monitor:
    def __init__(self,interval=.2):self.interval=interval;self.samples=[];self.stop=threading.Event()
    def sample(self):
        import psutil
        process=psutil.Process();python=process.memory_info().rss;jvm=0;other=0
        for p in process.children(recursive=True):
            try:
                rss=p.memory_info().rss
                if 'java' in p.name():jvm+=rss
                else:other+=rss
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        self.samples.append(dict(monotonic=time.monotonic(),python_rss=python,jvm_rss=jvm,other_child_rss=other,tree_rss=python+jvm+other))
    def __enter__(self):
        def run():
            while not self.stop.wait(self.interval):self.sample()
        self.sample();self.thread=threading.Thread(target=run,daemon=True);self.thread.start();return self
    def __exit__(self,*args):self.stop.set();self.thread.join();self.sample()
    def summary(self):return {key+'_sampled_peak':max(s[key] for s in self.samples) for key in ('python_rss','jvm_rss','tree_rss')}|{'sample_interval_seconds':self.interval,'samples':len(self.samples)}
def environment():
    import psutil,importlib.metadata as m
    read=lambda p:Path(p).read_text().strip() if Path(p).exists() else None
    return dict(python=platform.python_version(),java=subprocess.run(['java','-version'],capture_output=True,text=True).stderr,cpu_model=next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),None),logical_cpus=os.cpu_count(),affinity=len(os.sched_getaffinity(0)),cpu_quota=read('/sys/fs/cgroup/cpu.max'),memory_limit=read('/sys/fs/cgroup/memory.max'),system_available_memory=psutil.virtual_memory().available,dependencies={x:m.version(x) for x in ('pyspark','numpy','pandas','pyarrow','psutil')},storage_type='unverified virtualized filesystem',limits='Kaggle platform limits apply; per-stage target2400s')
