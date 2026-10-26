#!/usr/bin/env python3
"""Compare complete calibration bodies to pinned GPL stock, not numeric-only lists."""
from pathlib import Path
import sys,re,json,hashlib,difflib
port=Path(sys.argv[1]);stock=Path(sys.argv[2]);manifest=json.loads((Path(__file__).parent/'gs101-stock-pcie-source.json').read_text())
pinned=stock/'pcie-exynos-gs101-rc-cal.c'
assert hashlib.sha256(pinned.read_bytes()).hexdigest()==manifest['files'][pinned.name]['sha256']
a=(port/'phy-gs101-pcie.c').read_text();b=pinned.read_text()
def body(s,name):
 start=s.index('{',s.index(name+'('));i=start+1;depth=1
 while depth:
  depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[start:i]
def normalize(s):
 s=re.sub(r'/\*.*?\*/','',s,flags=re.S)
 s=re.sub(r'\b(?:pr_debug|dev_info)\(.*?\);','',s,flags=re.S)
 s=s.replace('exynos_pcie->phy_pcs_base','phy->pcs_base').replace('exynos_pcie->','phy->')
 return re.findall(r'0[xX][0-9a-fA-F]+|\w+|[^\s]',s)
for x,y in [('gs101_pcie_phy_pwrdn','exynos_pcie_rc_phy_all_pwrdn'),('gs101_pcie_phy_pwrdn_clear','exynos_pcie_rc_phy_all_pwrdn_clear'),('gs101_pcie_phy_config','exynos_pcie_rc_pcie_phy_config')]:
 aa=normalize(body(a,x));bb=normalize(body(b,y))
 if aa!=bb:
  print('\n'.join(difflib.unified_diff(bb,aa,fromfile='stock',tofile='port')));raise SystemExit(x+' mismatch')
 print('PINNED_CALIBRATION_BODY_MATCH',x)
