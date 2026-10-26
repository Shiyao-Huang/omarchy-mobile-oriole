from pathlib import Path
import importlib.util
p=Path(__file__).resolve().parents[1]/'tools/assess-render-benchmark.py';s=importlib.util.spec_from_file_location('assessment',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
v={'foot_exit':0,'screenshots':['a'*64,'b'*64],'scanout_samples':16,'unique_scanout_fb_ids':3,'log_sample_capped':False}
assert m.assess(v,'warn: missing optional protocol')['synthetic_render_pass']
assert not m.assess(v,' err: invalid section name')['synthetic_render_pass']
for change in [{'foot_exit':1},{'screenshots':['a'*64,'capture-failed']},{'screenshots':['a'*64]*2},{'screenshots':None},{'scanout_samples':0},{'unique_scanout_fb_ids':1},{'log_sample_capped':True}]:
 assert not m.assess(v|change,'')['synthetic_render_pass'],change
assert not m.assess({},'')['synthetic_render_pass']
assert m.assess(v,'')['physical_usability_accepted'] is False
print('PASS synthetic draw, parser failure despite rc0, failed captures, no updates, incomplete log and physical-acceptance boundary')
