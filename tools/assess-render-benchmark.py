#!/usr/bin/env python3
"""Assess synthetic rendering evidence. Never certifies physical phone usability."""
import argparse,json,re
from pathlib import Path

def assess(result,foot_log):
 reasons=[]
 if result.get('foot_exit') != 0:reasons.append('terminal did not exit normally')
 if re.search(r'^\s*err:',foot_log,re.M):reasons.append('terminal reported a parser/runtime error')
 hashes=result.get('screenshots',[])
 if not isinstance(hashes,list) or len(hashes)!=2 or any(not isinstance(x,str) or re.fullmatch(r'[0-9a-f]{64}',x) is None for x in hashes):
  reasons.append('two successful screenshots required')
 elif len(set(hashes))<2:reasons.append('screenshots did not change')
 if not isinstance(result.get('scanout_samples'),int) or result['scanout_samples']<16:reasons.append('incomplete scanout sample')
 if not isinstance(result.get('unique_scanout_fb_ids'),int) or result['unique_scanout_fb_ids']<2:reasons.append('active scanout buffers did not change')
 if result.get('log_sample_capped') is not False:reasons.append('error log measurement incomplete')
 return {'synthetic_render_pass':not reasons,'reasons':reasons,'physical_usability_accepted':False,'limits':['Screenshots and active DRM buffers do not prove panel output, touch latency, FPS or sustained performance']}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('result');ap.add_argument('--foot-log',required=True);a=ap.parse_args()
 r=assess(json.loads(Path(a.result).read_text()),Path(a.foot_log).read_text());print(json.dumps(r,indent=2));raise SystemExit(0 if r['synthetic_render_pass'] else 1)
