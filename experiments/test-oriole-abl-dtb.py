#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent binary FDT delta check; never contacts hardware."""
import struct
import sys
from pathlib import Path


def tree(path):
    data=Path(path).read_bytes()
    magic,size,off,strings=struct.unpack_from('>4I',data)
    assert magic==0xd00dfeed and size==len(data)
    nodes={};stack=[]
    while True:
        tag=struct.unpack_from('>I',data,off)[0];off+=4
        if tag==1:
            end=data.index(0,off);stack.append(data[off:end].decode());off=(end+4)&~3
            nodes['/'.join(stack) or '/']={}
        elif tag==2:stack.pop()
        elif tag==3:
            length,name=struct.unpack_from('>2I',data,off);off+=8
            start=strings+name;end=data.index(0,start)
            nodes['/'.join(stack) or '/'][data[start:end].decode()]=data[off:off+length]
            off=(off+length+3)&~3
        elif tag==4:pass
        elif tag==9:break
        else:raise AssertionError('bad FDT token')
    return nodes


base=tree(sys.argv[1]);out=Path(sys.argv[2])
paths={'dpm':'/dpm','log_arrdumppanic':'/dpm-stubs/log-arrdumppanic',
       'log_preslcdump':'/dpm-stubs/log-preslcdump','log_slcdump':'/dpm-stubs/log-slcdump'}
for variant,value in [('b0',0x9845001),('a0',0x9845000)]:
    got=tree(out/('oriole-'+variant+'.dtb'))
    assert got['/']['soc_id']==struct.pack('>2I',value,0)
    assert got['/chosen']['bootargs']==b'console=tty0 panic=10 clk_ignore_unused pd_ignore_unused rdinit=/init omamobile.initramfs\0'
    assert '/ect' in got
    for label,path in paths.items():
        assert got['/__symbols__'][label]==path.encode()+b'\0'
        assert struct.unpack('>I',got[path]['phandle'])[0]>0
        if path!='/dpm':assert got[path]['status']==b'disabled\0'
    allowed_nodes={'/ect','/dpm','/dpm-stubs','/__symbols__',*paths.values()}
    for path,props in base.items():
        assert path in got,('missing node',path)
        for name,value in props.items():
            if (path,name) in [('/','soc_id'),('/chosen','bootargs')]:continue
            assert got[path].get(name)==value,('changed property',path,name)
    for path,props in got.items():
        if path in allowed_nodes:
            allowed={'phandle'} if path=='/dpm' else {'phandle','status'} if path in paths.values() else set(paths) if path=='/__symbols__' else set()
            assert set(props)-set(base.get(path,{}))<=allowed,(path,props)
        else:
            assert path in base,('extra node',path)
            allowed={'soc_id'} if path=='/' else {'bootargs'} if path=='/chosen' else set()
            assert set(props)-set(base[path])<=allowed,('extra property',path)
print('PASS both silicon IDs, exact diagnostic bootargs, DPM targets and unchanged hardware tree')
