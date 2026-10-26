"""Check the parent-bus dependency omitted by the first overlay candidate."""
import subprocess,sys
base,merged=sys.argv[1:]
def cells(tree,node,prop):
 return [int(x,16) for x in subprocess.check_output(['fdtget','-t','x',tree,node,prop],text=True).split()]
original=[0,0,0,0x40000000]
assert cells(base,'/soc@0','ranges')==original
assert cells(merged,'/soc@0','ranges')==original+[0x60000000,0,0x60000000,0x01000000], 'missing or unexpected parent mapping'
assert cells(merged,'/soc@0','#address-cells')==[1]
assert cells(merged,'/soc@0','#size-cells')==[1]
assert cells(merged,'/','#address-cells')==[2]
ranges=cells(merged,'/soc@0','ranges')
def translate(addr,size):
 matches=[]
 for i in range(0,len(ranges),4):
  child,hi,lo,length=ranges[i:i+4]
  if child<=addr and addr+size<=child+length:matches.append((hi<<32)+lo+(addr-child))
 assert len(matches)==1,(addr,size,matches)
 return matches[0]
for node in ['/soc@0/phy@14550000','/soc@0/pcie@14520000']:
 regs=cells(merged,node,'reg');assert len(regs)%2==0
 for i in range(0,len(regs),2):assert translate(regs[i],regs[i+1])==regs[i]
pcie=cells(merged,'/soc@0/pcie@14520000','ranges')
assert pcie==[0x82000000,0,0x60000000,0x60000000,0,0x00ff0000]
assert translate(pcie[3],(pcie[4]<<32)+pcie[5])==0x60000000
for addr in [0,0x14700000,0x1c500000,0x3fffffff]:assert translate(addr,1)==addr
try:translate(0x40000000,1)
except AssertionError:pass
else:raise AssertionError('Modem window unexpectedly added')
print('PARENT_RESOURCE_TRANSLATION_PASS')
