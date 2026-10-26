import tempfile,subprocess,json,os,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
class Contract(unittest.TestCase):
 def test_agent_holds_and_preserves_arguments(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);log=d/'argv.json';shim=d/'setsid';shim.write_text('#!/usr/bin/env python3\nimport os,json,sys\nopen(os.environ["ARG_LOG"],"w").write(json.dumps(sys.argv[1:]))\n');shim.chmod(0o755)
   args=['--app-id=org.omarchy.agent','claude','--prompt','space ; $(not-executed) "quoted"']
   subprocess.run(['/bin/sh',str(root/'tools/agent-terminal-hold.sh'),*args],env={**os.environ,'PATH':str(d)+':'+os.environ['PATH'],'ARG_LOG':str(log)},check=True)
   self.assertEqual(json.loads(log.read_text()),['uwsm-app','--','xdg-terminal-exec','--hold','--app-id=org.omarchy.agent','-e',*args[1:]])
 def test_non_agent_original_passthrough(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);log=d/'argv.json';original=d/'original';original.write_text('#!/usr/bin/env python3\nimport json,sys\nopen('+repr(str(log))+',"w").write(json.dumps(sys.argv[1:]))\n');original.chmod(0o755)
   text=(root/'tools/agent-terminal-hold.sh').read_text();self.assertIn('exec /usr/bin/omarchy-launch-tui "$@"',text)
   candidate=d/'candidate';candidate.write_text(text.replace('/usr/bin/omarchy-launch-tui',str(original)))
   args=['--app-id=other','command','a b'];subprocess.run(['/bin/sh',str(candidate),*args],check=True);self.assertEqual(json.loads(log.read_text()),args)
unittest.main()
