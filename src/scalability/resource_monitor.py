"""Sample disjoint process RSS; configured heap is never reported as RSS."""
import os,time,threading,platform,subprocess
from pathlib import Path
class Monitor:
    def __init__(self,interval=.2):self.interval=interval;self.samples=[];self.stop=threading.Event()
    def sample(self):
        import psutil
        process=psutil.Process();python=process.memory_info().rss;jvm=0;other=0;cpu=process.cpu_times();cpu_seconds=cpu.user+cpu.system;pids=[process.pid]
        for p in process.children(recursive=True):
            try:
                rss=p.memory_info().rss;cpu=p.cpu_times();cpu_seconds+=cpu.user+cpu.system;pids.append(p.pid)
                if 'java' in p.name():jvm+=rss
                else:other+=rss
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        self.samples.append(dict(monotonic=time.monotonic(),python_rss=python,jvm_rss=jvm,other_child_rss=other,tree_rss=python+jvm+other,cpu_user_system_seconds=cpu_seconds,pids=sorted(pids)))
    def __enter__(self):
        def run():
            while not self.stop.wait(self.interval):self.sample()
        self.sample();self.thread=threading.Thread(target=run,daemon=True);self.thread.start();return self
    def __exit__(self,*args):self.stop.set();self.thread.join();self.sample()
    def summary(self):
        first,last=self.samples[0],self.samples[-1];duration=last['monotonic']-first['monotonic'];cpu=last['cpu_user_system_seconds']-first['cpu_user_system_seconds'] if last['pids']==first['pids'] else None
        return {key+'_sampled_peak':max(s[key] for s in self.samples) for key in ('python_rss','jvm_rss','tree_rss')}|{'sample_interval_seconds':self.interval,'samples':len(self.samples),'cpu_seconds_process_tree':cpu,'cpu_percent_one_core_basis':100*cpu/duration if cpu is not None and cpu>=0 and duration else None,'cpu_measurement_limit':'CPU delta unavailable when process membership changes'}
def environment(spark=None):
    import psutil,importlib.metadata as m
    read=lambda p:Path(p).read_text().strip() if Path(p).exists() else None
    import shutil
    observed={}
    if spark is not None:
        try:
            keys=('spark.master','spark.driver.memory','spark.executor.memory','spark.sql.shuffle.partitions','spark.sql.adaptive.enabled','spark.sql.files.maxPartitionBytes')
            observed={'spark_version':spark.version,'spark_config':{k:spark.conf.get(k,None) for k in keys},'jvm_max_heap_bytes':int(spark._jvm.java.lang.Runtime.getRuntime().maxMemory())}
        except Exception as exc:observed={'spark_runtime_inventory_error':type(exc).__name__}
    return dict(spark_runtime=observed,installed_packages={d.metadata['Name']:d.version for d in m.distributions() if d.metadata.get('Name')},disk_free_bytes=shutil.disk_usage('/kaggle/working' if Path('/kaggle/working').exists() else Path.cwd()).free,python=platform.python_version(),java=subprocess.run(['java','-version'],capture_output=True,text=True).stderr,cpu_model=next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),None),logical_cpus=os.cpu_count(),affinity=len(os.sched_getaffinity(0)),cpu_quota=read('/sys/fs/cgroup/cpu.max'),memory_limit=read('/sys/fs/cgroup/memory.max'),system_available_memory=psutil.virtual_memory().available,dependencies={x:m.version(x) for x in ('pyspark','numpy','pandas','pyarrow','psutil')},storage_type='unverified virtualized filesystem',limits='Kaggle platform limits apply; per-stage target2400s')
