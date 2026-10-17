"""Disposable Docker checks for the Kubernetes example; no provider calls.

Requires Docker and PyYAML==6.0.3. This does not apply a Kubernetes manifest.
"""
import subprocess
import time
from pathlib import Path
import yaml

manifest = list(yaml.safe_load_all((Path(__file__).resolve().parents[1] / 'kubernetes-spec-example.yaml').read_text()))
for d in manifest:
 if not isinstance(d,dict) or d.get('kind')!='Deployment': continue
 c=d['spec']['template']['spec']['containers'][0];name=c['name'];uid=str(c['securityContext']['runAsUser']);gid=str(c['securityContext']['runAsGroup'])
 assert int(uid) >= 10000 and c['securityContext']['readOnlyRootFilesystem']
 assert '@sha256:' in c['image']
 args=['docker','run','-d','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user',uid+':'+gid]
 for m in c.get('volumeMounts',[]):args+=['--tmpfs',m['mountPath']+':rw,nosuid,uid=0,gid='+gid+',mode=0770']
 if name=='grafana':args+=['-e','GF_ANALYTICS_REPORTING_ENABLED=false','-e','GF_ANALYTICS_CHECK_FOR_UPDATES=false','-e','GF_PLUGINS_PREINSTALL_DISABLED=true']
 if name=='garmin-fetch-data':
  args+=['-e','HOME=/home/appuser','-e','PYTHONDONTWRITEBYTECODE=1','--entrypoint','python',c['image'],'-c',"from pathlib import Path; from unittest.mock import patch; import importlib; [(Path(p)/'offline-check').write_text('fixture') for p in ['/tmp','/home/appuser/.garminconnect','/home/appuser/fit_filestore']]; p=patch('influxdb.InfluxDBClient');p.start();importlib.import_module('garmin_grafana.garmin_fetch'); print('offline collector import and storage passed')"]
 else:args += [c['image']]
 ident=subprocess.check_output(args,text=True).strip()
 try:
  if name=='garmin-fetch-data':
   code=subprocess.check_output(['docker','wait',ident],text=True,timeout=45).strip();print(name,'exit',code,subprocess.check_output(['docker','logs',ident],text=True,stderr=subprocess.STDOUT)[-1000:],flush=True);assert code=='0'
  else:
   path,port=('/api/health',3000) if name=='grafana' else ('/ping',8086)
   ok=False
   for _ in range(35):
    r=subprocess.run(['docker','exec',ident,'sh','-c',f'(wget -T 2 -qO- http://127.0.0.1:{port}{path} || curl --max-time 2 -fsS http://127.0.0.1:{port}{path}) >/dev/null'],capture_output=True)
    if r.returncode==0:ok=True;break
    time.sleep(1)
   print(name,'read-only UID',uid,'health',ok,flush=True)
   if ok:
    assert subprocess.run(['docker','exec',ident,'sh','-c','touch /read-only-test'],capture_output=True).returncode != 0
   if not ok:print(subprocess.check_output(['docker','logs','--tail','15',ident],text=True,stderr=subprocess.STDOUT),flush=True)
   assert ok
 finally:subprocess.run(['docker','rm','-fv',ident],capture_output=True)
