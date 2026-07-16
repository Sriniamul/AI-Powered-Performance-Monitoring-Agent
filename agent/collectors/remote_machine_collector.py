"""Collect a Linux machine's core performance metrics over SSH."""

import json


REMOTE_SCRIPT = r'''import json, os, platform, socket, time
def cpu_times():
    v=list(map(int,open('/proc/stat').readline().split()[1:])); return sum(v), v[3]+(v[4] if len(v)>4 else 0)
a,ai=cpu_times(); time.sleep(.2); b,bi=cpu_times(); cpu=0 if b==a else (1-(bi-ai)/(b-a))*100
mem={x.split(':')[0]:int(x.split()[1]) for x in open('/proc/meminfo') if ':' in x}
mt=mem.get('MemTotal',0); ma=mem.get('MemAvailable',mem.get('MemFree',0)); memory=0 if not mt else (mt-ma)*100/mt
st=os.statvfs('/'); dt=st.f_blocks*st.f_frsize; df=st.f_bavail*st.f_frsize
procs=[]
for p in os.listdir('/proc'):
    if p.isdigit():
        try:
            name=open('/proc/'+p+'/comm').read().strip(); rss=int(open('/proc/'+p+'/statm').read().split()[1])*os.sysconf('SC_PAGE_SIZE')
            procs.append({'pid':int(p),'name':name,'memory_percent':0 if not mt else rss*100/(mt*1024)})
        except: pass
host=socket.gethostname()
print(json.dumps({'machine_name':host,'machine_ip':socket.gethostbyname(host),'operating_system':platform.platform(),'os_environment':platform.system().lower(),'architecture':platform.machine(),'cpu_percent':round(cpu,2),'memory_percent':round(memory,2),'memory_total_mb':round(mt/1024,2),'memory_available_mb':round(ma/1024,2),'disk_percent':round(0 if not dt else (dt-df)*100/dt,2),'disk_total_gb':round(dt/1073741824,2),'disk_free_gb':round(df/1073741824,2),'process_count':len(procs),'zombie_process_count':0,'top_memory_process':max(procs,key=lambda x:x['memory_percent']) if procs else None,'top_cpu_process':None,'network_sent_mb_s':None,'network_received_mb_s':None,'network_connections':None,'jvm_available':False,'jvm_pid':None}))'''


class RemoteMachineCollector:
    def __init__(self, machine: dict):
        self.machine = machine

    def collect(self) -> dict:
        try:
            import paramiko
        except ImportError as exc:
            raise RuntimeError("Remote monitoring requires the 'paramiko' package") from exc

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=self.machine["ip_address"],
                port=int(self.machine.get("port", 22)),
                username=self.machine.get("username"),
                password=self.machine.get("password"),
                timeout=float(self.machine.get("timeout_seconds", 10)),
                look_for_keys=not bool(self.machine.get("password")),
                allow_agent=True,
            )
            command = "python3 -c " + _shell_quote(REMOTE_SCRIPT)
            _, stdout, stderr = client.exec_command(command, timeout=20)
            error = stderr.read().decode("utf-8", "replace").strip()
            output = stdout.read().decode("utf-8", "replace").strip()
            if not output:
                raise RuntimeError(error or "remote collector returned no data")
            metrics = json.loads(output.splitlines()[-1])
            metrics["machine_ip"] = self.machine["ip_address"]
            metrics["machine_name"] = self.machine.get("name") or metrics["machine_name"]
            return metrics
        finally:
            client.close()


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"
