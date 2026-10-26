#!/usr/bin/env python3
"""Bounded surfaceless GBM/GLES draw + readback. No display/session changes."""
import ctypes as C, os, json, time, sys
P=C.c_void_p; I=C.c_int; U=C.c_uint; F=C.c_float; B=C.c_ubyte
E=C.CDLL('libEGL.so.1'); G=C.CDLL('libGLESv2.so.2'); M=C.CDLL('libgbm.so.1')
def fn(lib,name,restype,args):
 f=getattr(lib,name);f.restype=restype;f.argtypes=args;return f
geterr=fn(E,'eglGetError',I,[])
def ok(value,where):
 if not value:raise RuntimeError(where+' EGL='+hex(geterr()))
 return value
fn(M,'gbm_create_device',P,[I]);fn(M,'gbm_device_destroy',None,[P]);fn(E,'eglGetProcAddress',P,[C.c_char_p]);fn(E,'eglInitialize',U,[P,C.POINTER(I),C.POINTER(I)]);fn(E,'eglQueryString',C.c_char_p,[P,I]);fn(E,'eglBindAPI',U,[U]);fn(E,'eglChooseConfig',U,[P,C.POINTER(I),C.POINTER(P),I,C.POINTER(I)]);fn(E,'eglCreateContext',P,[P,P,P,C.POINTER(I)]);fn(E,'eglMakeCurrent',U,[P,P,P,P]);fn(E,'eglDestroyContext',U,[P,P]);fn(E,'eglTerminate',U,[P])
fn(G,'glGetString',C.c_char_p,[U]);fn(G,'glGetError',U,[]);fn(G,'glCreateShader',U,[U]);fn(G,'glShaderSource',None,[U,I,C.POINTER(C.c_char_p),C.POINTER(I)]);fn(G,'glCompileShader',None,[U]);fn(G,'glGetShaderiv',None,[U,U,C.POINTER(I)]);fn(G,'glGetShaderInfoLog',None,[U,I,C.POINTER(I),P]);fn(G,'glCreateProgram',U,[]);fn(G,'glAttachShader',None,[U,U]);fn(G,'glBindAttribLocation',None,[U,U,C.c_char_p]);fn(G,'glLinkProgram',None,[U]);fn(G,'glGetProgramiv',None,[U,U,C.POINTER(I)]);fn(G,'glUseProgram',None,[U]);fn(G,'glGetUniformLocation',I,[U,C.c_char_p]);fn(G,'glUniform4f',None,[I,F,F,F,F]);fn(G,'glGenTextures',None,[I,C.POINTER(U)]);fn(G,'glBindTexture',None,[U,U]);fn(G,'glTexImage2D',None,[U,I,I,I,I,I,U,U,P]);fn(G,'glTexParameteri',None,[U,U,I]);fn(G,'glGenFramebuffers',None,[I,C.POINTER(U)]);fn(G,'glBindFramebuffer',None,[U,U]);fn(G,'glFramebufferTexture2D',None,[U,U,U,U,I]);fn(G,'glCheckFramebufferStatus',U,[U]);fn(G,'glViewport',None,[I,I,I,I]);fn(G,'glVertexAttribPointer',None,[U,I,U,B,I,P]);fn(G,'glEnableVertexAttribArray',None,[U]);fn(G,'glDrawArrays',None,[U,I,I]);fn(G,'glFinish',None,[]);fn(G,'glReadPixels',None,[I,I,I,I,U,U,P])
def shader(kind,source):
 s=G.glCreateShader(kind);v=C.c_char_p(source);G.glShaderSource(s,1,C.byref(v),None);G.glCompileShader(s);status=I();G.glGetShaderiv(s,0x8B81,C.byref(status))
 if not status.value:
  b=C.create_string_buffer(2048);G.glGetShaderInfoLog(s,len(b),None,b);raise RuntimeError('shader compile '+repr(b.value))
 return s
fd=None;gbm=None;display=None;context=None;result={'claim':'GPU GLES shader/readback only; no physical display or smoothness acceptance'};start=time.monotonic()
try:
 fd=os.open(sys.argv[1] if len(sys.argv)>1 else '/dev/dri/renderD128',os.O_RDWR|os.O_CLOEXEC)
 gbm=ok(M.gbm_create_device(fd),'gbm_create')
 addr=ok(E.eglGetProcAddress(b'eglGetPlatformDisplayEXT'),'platform_proc')
 display=ok(C.CFUNCTYPE(P,U,P,C.POINTER(I))(addr)(0x31D7,gbm,None),'platform_gbm')
 major=I();minor=I();ok(E.eglInitialize(display,C.byref(major),C.byref(minor)),'initialize')
 exts=E.eglQueryString(display,0x3055) or b'';assert b'EGL_KHR_surfaceless_context' in exts
 ok(E.eglBindAPI(0x30A0),'bind_gles')
 attrs=(I*9)(0x3040,4,0x3024,8,0x3023,8,0x3022,8,0x3038);config=P();n=I()
 ok(E.eglChooseConfig(display,attrs,C.byref(config),1,C.byref(n)),'choose_config');assert n.value==1
 context=ok(E.eglCreateContext(display,config,None,(I*3)(0x3098,2,0x3038)),'context')
 ok(E.eglMakeCurrent(display,None,None,context),'make_current')
 renderer=G.glGetString(0x1F01).decode();result['renderer']=renderer;result['version']=G.glGetString(0x1F02).decode();print(json.dumps(result),flush=True)
 assert 'Mali-G78' in renderer and not any(x in renderer.lower() for x in ('llvmpipe','softpipe','swrast')),renderer
 vs=shader(0x8B31,b'attribute vec2 position; void main(){ gl_Position=vec4(position,0.0,1.0); }')
 fs=shader(0x8B30,b'precision mediump float; uniform vec4 color; void main(){ gl_FragColor=color; }')
 program=G.glCreateProgram();G.glAttachShader(program,vs);G.glAttachShader(program,fs);G.glBindAttribLocation(program,0,b'position');G.glLinkProgram(program);status=I();G.glGetProgramiv(program,0x8B82,C.byref(status));assert status.value
 G.glUseProgram(program);color=G.glGetUniformLocation(program,b'color');assert color>=0
 texture=U();G.glGenTextures(1,C.byref(texture));G.glBindTexture(0x0DE1,texture);G.glTexParameteri(0x0DE1,0x2801,0x2600);G.glTexParameteri(0x0DE1,0x2800,0x2600);G.glTexImage2D(0x0DE1,0,0x1908,16,16,0,0x1908,0x1401,None)
 framebuffer=U();G.glGenFramebuffers(1,C.byref(framebuffer));G.glBindFramebuffer(0x8D40,framebuffer);G.glFramebufferTexture2D(0x8D40,0x8CE0,0x0DE1,texture,0);assert G.glCheckFramebufferStatus(0x8D40)==0x8CD5
 G.glViewport(0,0,16,16);vertices=(F*6)(-1,-1,3,-1,-1,3);G.glVertexAttribPointer(0,2,0x1406,0,0,C.cast(vertices,P));G.glEnableVertexAttribArray(0);pixels=(B*(16*16*4))()
 for rgba in [(255,0,0,255),(0,255,0,255),(0,0,255,255)]:
  G.glUniform4f(color,*[v/255 for v in rgba]);G.glDrawArrays(4,0,3);G.glFinish();G.glReadPixels(0,0,16,16,0x1908,0x1401,pixels);err=G.glGetError();assert err==0,hex(err);assert bytes(pixels)==bytes(rgba)*256,'pixel mismatch'
 result.update(pass_shader_readback=True,frames=3,pixels_verified=768,seconds=round(time.monotonic()-start,3));print(json.dumps(result),flush=True)
finally:
 if display:
  E.eglMakeCurrent(display,None,None,None)
  if context:E.eglDestroyContext(display,context)
  E.eglTerminate(display)
 if gbm:M.gbm_device_destroy(gbm)
 if fd is not None:os.close(fd)
