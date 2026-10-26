#!/usr/bin/env python3
"""Bounded serial payload receiver. Caller owns the TTY and destination directory."""
import os,sys,select,time,hashlib,termios,tty
from pathlib import Path

def receive(fd, target, size, expected, deadline_seconds=120):
    if not 0 < size <= 8*1024*1024 or len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected):
        raise ValueError('invalid size or digest')
    target=Path(target);tmp=target.with_name(target.name+'.part')
    handle=None;created=False;old=termios.tcgetattr(fd);digest=hashlib.sha256();end=time.monotonic()+deadline_seconds
    try:
        handle=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        created=True
        tty.setraw(fd,termios.TCSANOW)
        os.write(fd,b'ORIOLE_TRANSFER_READY\n')
        left=size
        while left:
            remaining=end-time.monotonic()
            if remaining<=0 or not select.select([fd],[],[],remaining)[0]:raise TimeoutError('payload deadline')
            b=os.read(fd,min(left,65536))
            if not b:raise EOFError('short payload')
            digest.update(b);left-=len(b)
            view=memoryview(b)
            while view:
                n=os.write(handle,view);view=view[n:]
        os.fsync(handle);os.close(handle);handle=None
        if digest.hexdigest()!=expected:raise ValueError('digest mismatch')
        os.replace(tmp,target)
        termios.tcflush(fd,termios.TCIFLUSH)
    except BaseException:
        if handle is not None:os.close(handle)
        if created:
            try:tmp.unlink()
            except FileNotFoundError:pass
        raise
    finally:
        termios.tcsetattr(fd,termios.TCSANOW,old)
    os.write(fd,b'ORIOLE_TRANSFER_SHA256_OK\n')

if __name__=='__main__':
    dest=Path('/var/tmp/oriole-aquamarine-c1')
    dest.mkdir(mode=0o700,exist_ok=True)
    mode=sys.argv[1]
    if mode not in ('probe','candidate'):raise ValueError('unknown mode')
    target=dest/('transport-probe.bin' if mode=='probe' else 'libaquamarine-candidate.so')
    receive(0,target,int(sys.argv[2]),sys.argv[3])
