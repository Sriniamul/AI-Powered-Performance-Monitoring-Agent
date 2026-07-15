"""Local web dashboard for incidents detected by the performance agent."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def load_issues(artifact_dir: str | Path, limit: int = 250) -> list[dict]:
    """Load incident snapshots, newest first, ignoring partial/corrupt files."""
    root = Path(artifact_dir)
    issues = []
    for path in sorted(root.glob("metrics_snapshot_*.json"), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            metrics = payload.get("metrics", {})
            decision = payload.get("decision", {})
            if str(metrics.get("environment", "")).lower() == "demo":
                continue
            if not decision.get("should_act", False):
                continue
            issues.append({
                "id": path.stem.removeprefix("metrics_snapshot_"),
                "timestamp": metrics.get("timestamp"),
                "service": metrics.get("service_name", "unknown"),
                "environment": metrics.get("environment", "unknown"),
                "machine_name": metrics.get("machine_name", "unknown"),
                "machine_ip": metrics.get("machine_ip", "unavailable"),
                "operating_system": metrics.get("operating_system", "unknown"),
                "severity": decision.get("severity", "unknown"),
                "reason": decision.get("reason", "Unknown anomaly"),
                "cause": describe_cause(metrics, decision),
                "cpu_percent": metrics.get("cpu_percent"),
                "memory_percent": metrics.get("memory_percent"),
                "disk_percent": metrics.get("disk_percent"),
                "disk_read_mb_s": metrics.get("disk_read_mb_s"),
                "disk_write_mb_s": metrics.get("disk_write_mb_s"),
                "network_sent_mb_s": metrics.get("network_sent_mb_s"),
                "network_received_mb_s": metrics.get("network_received_mb_s"),
                "network_connections": metrics.get("network_connections"),
                "process_count": metrics.get("process_count"),
                "zombie_process_count": metrics.get("zombie_process_count"),
                "jvm_available": metrics.get("jvm_available", False),
                "jvm_heap_percent": metrics.get("jvm_heap_percent"),
                "jvm_heap_used_mb": metrics.get("jvm_heap_used_mb"),
                "jvm_heap_capacity_mb": metrics.get("jvm_heap_capacity_mb"),
                "jvm_young_gc_count": metrics.get("jvm_young_gc_count"),
                "jvm_full_gc_count": metrics.get("jvm_full_gc_count"),
                "jvm_gc_time_seconds": metrics.get("jvm_gc_time_seconds"),
                "jvm_thread_count": metrics.get("jvm_thread_count"),
                "jvm_daemon_thread_count": metrics.get("jvm_daemon_thread_count"),
                "jvm_deadlock_detected": metrics.get("jvm_deadlock_detected"),
                "jvm_classes_loaded": metrics.get("jvm_classes_loaded"),
                "jvm_classes_unloaded": metrics.get("jvm_classes_unloaded"),
                "jvm_pid": metrics.get("jvm_pid"),
                "artifact": path.name,
                "llm_status": metrics.get("llm", {}).get("status", "not_available"),
                "llm_model": metrics.get("llm", {}).get("model"),
                "llm_analysis": metrics.get("llm", {}).get("root_cause", "LLM analysis was not captured for this incident."),
                "suggested_solution": metrics.get("llm", {}).get("suggested_solution", "LLM analysis was not captured for this incident."),
                "llm_confidence": metrics.get("llm", {}).get("confidence", "low"),
            })
        except (OSError, json.JSONDecodeError, TypeError):
            continue
        if len(issues) >= limit:
            break
    return issues


def describe_cause(metrics: dict, decision: dict) -> str:
    """Translate detector output into a useful, non-speculative explanation."""
    reason = str(decision.get("reason", "")).lower()
    cpu = metrics.get("cpu_percent")
    memory = metrics.get("memory_percent")
    cpu_text = f"{cpu:.1f}%" if isinstance(cpu, (int, float)) else "an elevated level"
    memory_text = f"{memory:.1f}%" if isinstance(memory, (int, float)) else "an elevated level"
    cpu_high = "cpu_percent" in reason
    memory_high = "memory_percent" in reason
    process_note = describe_process_attribution(metrics, cpu_high, memory_high)
    if cpu_high and memory_high:
        return (f"CPU reached {cpu_text} and memory reached {memory_text}, both above their configured limits. "
                f"The machine is experiencing simultaneous compute saturation and memory pressure. {process_note}")
    if memory_high:
        return (f"Memory utilization reached {memory_text}, exceeding the configured limit. "
                f"Possible causes include sustained allocations, cache growth, or a memory leak. {process_note}")
    if cpu_high:
        return (f"CPU utilization reached {cpu_text}, exceeding the configured limit. "
                f"Possible causes include a busy workload, expensive processing, or a tight loop. {process_note}")
    if "disk_percent" in reason:
        disk = metrics.get("disk_percent")
        value = f"{disk:.1f}%" if isinstance(disk, (int, float)) else "an elevated level"
        return f"Disk utilization reached {value}, leaving limited free capacity for applications and diagnostic artifacts."
    if "zombie_process" in reason:
        return f"Detected {metrics.get('zombie_process_count', 0)} zombie process(es), indicating a parent process has not reaped exited children."
    if "jvm_heap_percent" in reason:
        return (f"JVM heap utilization reached {metrics.get('jvm_heap_percent', 0):.1f}% "
                f"({metrics.get('jvm_heap_used_mb', 0):.1f} MB used). Sustained heap pressure can increase garbage collection pauses or indicate retained objects.")
    if "isolation" in reason or "model" in reason or "ml" in reason:
        return "The observed resource pattern differs significantly from the agent's learned baseline."
    return "The collected metrics matched the agent's anomaly policy and require further diagnostic review."


def describe_process_attribution(metrics: dict, cpu_high: bool, memory_high: bool) -> str:
    if cpu_high:
        process = metrics.get("top_cpu_process")
        usage = "cpu_percent"
        label = "CPU"
    elif memory_high:
        process = metrics.get("top_memory_process")
        usage = "memory_percent"
        label = "memory"
    else:
        return ""
    if not process:
        return "No process-level attribution was available for this sample."
    return (f"Likely contributing process at sampling time: {process.get('name', 'unknown')} "
            f"(PID {process.get('pid', 'unknown')}), using {process.get(usage, 0):.1f}% {label}.")


HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Performance Agent</title>
<style>
:root{color-scheme:dark;--bg:#07111f;--panel:#0e1b2d;--line:#21334b;--muted:#91a4bd;--text:#eef5ff;--blue:#54a8ff;--red:#ff5876;--orange:#ffad42;--green:#42d9a1}*{box-sizing:border-box}body{margin:0;font:14px Inter,Segoe UI,Arial,sans-serif;background:radial-gradient(circle at 10% 0,#132b4b 0,transparent 35%),var(--bg);color:var(--text)}main{max-width:1280px;margin:auto;padding:32px 24px}.top{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:26px}h1{margin:0;font-size:28px;letter-spacing:-.5px}.subtitle{color:var(--muted);margin-top:7px}.live{display:flex;align-items:center;gap:8px;color:var(--green);font-weight:600}.dot{width:9px;height:9px;border-radius:50%;background:var(--green);box-shadow:0 0 12px var(--green)}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:18px}.card,.toolbar,.tablebox{background:rgba(14,27,45,.92);border:1px solid var(--line);border-radius:14px}.card{padding:20px}.label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.8px}.value{font-size:29px;font-weight:700;margin-top:8px}.toolbar{display:flex;gap:12px;padding:14px;margin-bottom:14px}select,input{background:#091626;color:var(--text);border:1px solid var(--line);border-radius:8px;padding:10px 12px;outline:none}input{flex:1;min-width:180px}.tablebox{overflow:auto;max-height:62vh;scrollbar-gutter:stable;scrollbar-color:#496789 #091626;scrollbar-width:auto}.tablebox::-webkit-scrollbar{width:14px;height:14px}.tablebox::-webkit-scrollbar-track{background:#091626}.tablebox::-webkit-scrollbar-thumb{background:#496789;border:3px solid #091626;border-radius:10px}table{width:100%;min-width:3100px;border-collapse:separate;border-spacing:0}th,td{text-align:left;padding:14px 16px;border-bottom:1px solid var(--line);white-space:nowrap}th{position:sticky;top:0;z-index:2;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.7px;background:#0a1728}tr:last-child td{border:0}tbody tr:hover{background:#13243a}.reason{white-space:normal;min-width:320px;max-width:460px}.badge{display:inline-block;padding:5px 9px;border-radius:20px;font-size:11px;font-weight:700;text-transform:uppercase}.critical{background:#4a1322;color:#ff7890}.high{background:#492d0f;color:#ffc36b}.medium{background:#123552;color:#77bfff}.low{background:#123b31;color:#65e0b3}.empty{text-align:center;color:var(--muted);padding:50px!important}.foot{color:var(--muted);font-size:12px;margin-top:12px;text-align:right}@media(max-width:850px){.cards{grid-template-columns:repeat(2,1fr)}.top{align-items:flex-start;flex-direction:column}}@media(max-width:480px){.cards{grid-template-columns:1fr}.toolbar{flex-direction:column}}
</style></head><body><main>
<div class="top"><div><h1>AI Powerded Performance monitor agent</h1><div class="subtitle">AI agent detections across services and environments</div></div><div class="live"><span class="dot"></span>LIVE MONITORING</div></div>
<section class="cards"><div class="card"><div class="label">Total incidents</div><div class="value" id="total">—</div></div><div class="card"><div class="label">Critical</div><div class="value" id="critical">—</div></div><div class="card"><div class="label">Environments</div><div class="value" id="envs">—</div></div><div class="card"><div class="label">Latest detection</div><div class="value" id="latest" style="font-size:17px">—</div></div></section>
<div class="toolbar"><input id="search" placeholder="Search service or reason…"><select id="environment"><option value="">All environments</option></select><select id="severity"><option value="">All severities</option><option>critical</option><option>high</option><option>medium</option><option>low</option></select></div>
<div class="tablebox"><table><thead><tr><th>Detected at</th><th>Environment</th><th>Machine</th><th>Severity</th><th>CPU</th><th>Memory</th><th>Disk</th><th>Network ↓/↑</th><th>Processes</th><th>JVM Heap</th><th>GC (Young/Full)</th><th>JVM Threads</th><th>Classes</th><th>Detected issue</th><th>Cause</th><th>LLM Analysis</th><th>Suggested Solution</th></tr></thead><tbody id="rows"></tbody></table></div><div class="foot" id="updated"></div>
</main><script>
let issues=[];const $=id=>document.getElementById(id);function esc(v){return String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function pct(v){return v==null?'—':`${Number(v).toFixed(1)}%`}function date(v){if(!v)return'—';return new Date(v).toLocaleString([], {dateStyle:'medium',timeStyle:'medium'})}function jvm(v,f){return v.jvm_available?f:'No JVM'}function render(){const q=$('search').value.toLowerCase(),env=$('environment').value,sev=$('severity').value;const shown=issues.filter(x=>(!env||x.environment===env)&&(!sev||x.severity===sev)&&(!q||`${x.machine_name} ${x.service} ${x.reason} ${x.cause} ${x.llm_analysis} ${x.suggested_solution}`.toLowerCase().includes(q)));$('rows').innerHTML=shown.length?shown.map(x=>`<tr><td>${esc(date(x.timestamp))}</td><td>${esc(x.environment)}</td><td title="${esc(x.operating_system)} · ${esc(x.machine_ip)}">${esc(x.machine_name)}</td><td><span class="badge ${esc(x.severity)}">${esc(x.severity)}</span></td><td>${pct(x.cpu_percent)}</td><td>${pct(x.memory_percent)}</td><td>${pct(x.disk_percent)}</td><td>${esc(x.network_received_mb_s??'—')} / ${esc(x.network_sent_mb_s??'—')} MB/s</td><td>${esc(x.process_count)} <span title="Zombie processes">(${esc(x.zombie_process_count??0)} zombie)</span></td><td>${esc(jvm(x,pct(x.jvm_heap_percent)))}</td><td>${esc(jvm(x,`${x.jvm_young_gc_count??'—'} / ${x.jvm_full_gc_count??'—'}`))}</td><td>${esc(jvm(x,x.jvm_thread_count??'—'))}</td><td>${esc(jvm(x,`${x.jvm_classes_loaded??'—'} / ${x.jvm_classes_unloaded??'—'}`))}</td><td class="reason">${esc(x.reason).replaceAll('_',' ')}</td><td class="reason">${esc(x.cause)}</td><td class="reason" title="Model: ${esc(x.llm_model)} · Confidence: ${esc(x.llm_confidence)}">${esc(x.llm_analysis)}</td><td class="reason">${esc(x.suggested_solution)}</td></tr>`).join(''):'<tr><td class="empty" colspan="17">No incidents match these filters.</td></tr>'}async function refresh(){try{const r=await fetch('/api/issues?limit=500',{cache:'no-store'});issues=await r.json();$('total').textContent=issues.length;$('critical').textContent=issues.filter(x=>x.severity==='critical').length;const envs=[...new Set(issues.map(x=>x.environment))];$('envs').textContent=envs.length;const chosen=$('environment').value;$('environment').innerHTML='<option value="">All environments</option>'+envs.map(x=>`<option>${esc(x)}</option>`).join('');$('environment').value=chosen;$('latest').textContent=issues.length?date(issues[0].timestamp):'No detections';$('updated').textContent=`Updated ${new Date().toLocaleTimeString()}`;render()}catch(e){$('updated').textContent='Dashboard API unavailable'}}['search','environment','severity'].forEach(x=>$(x).addEventListener(x==='search'?'input':'change',render));refresh();setInterval(refresh,5000);
</script></body></html>'''


def make_handler(artifact_dir: Path):
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            request = urlparse(self.path)
            if request.path == "/":
                self._send(200, HTML.encode(), "text/html; charset=utf-8")
            elif request.path == "/api/issues":
                query = parse_qs(request.query)
                try:
                    limit = min(max(int(query.get("limit", [250])[0]), 1), 1000)
                except ValueError:
                    limit = 250
                body = json.dumps(load_issues(artifact_dir, limit)).encode()
                self._send(200, body, "application/json")
            elif request.path == "/health":
                self._send(200, b'{"status":"ok"}', "application/json")
            else:
                self._send(404, b'{"error":"not found"}', "application/json")

        def _send(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            return

    return DashboardHandler


def main():
    parser = argparse.ArgumentParser(description="AI Performance Agent incident dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--artifacts", default="artifacts")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(Path(args.artifacts)))
    print(f"Dashboard running at http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
