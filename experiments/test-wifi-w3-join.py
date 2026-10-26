#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual-C join ABI tests and ASan kill test for a header-only conversion."""
from pathlib import Path
import re,subprocess,tempfile,sys,os

def block(s,begin):
 a=s.index(begin);b=s.index('{',a);depth=1;e=b+1
 while depth:
  depth+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]

root=Path(sys.argv[1]);header=(root/'fwil_types.h').read_text();source=(root/'cfg80211.c').read_text()
structs='\n'.join(block(header,'struct '+n+' {')+';' for n in ['brcmf_ssid_le','brcmf_join_scan_params_le','brcmf_assoc_params_v1_le','brcmf_ext_join_params_v1_le'])
fn=block(source,'static s32 brcmf_join_v1(')
pre=r'''
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <stdio.h>
#include <assert.h>
typedef uint32_t u32; typedef uint16_t u16; typedef uint8_t u8;
typedef int32_t s32; typedef uint32_t __le32; typedef uint16_t __le16;
#define ETH_ALEN 6
#define IEEE80211_MAX_SSID_LEN 32
#define ENOMEM 12
#define EBADE 52
#define GFP_KERNEL 0
#define cpu_to_le32(x) ((u32)(x))
#define cpu_to_le16(x) ((u16)(x))
#define BRCMF_SCAN_JOIN_ACTIVE_DWELL_TIME_MS 320
#define BRCMF_SCAN_JOIN_PASSIVE_DWELL_TIME_MS 400
#define BRCMF_SCAN_JOIN_PROBE_INTERVAL_MS 20
#define bphy_err(drvr,...) ((void)(drvr))
#define brcmf_dbg(...) ((void)0)
struct brcmf_pub {int unused;};
struct brcmf_if {struct brcmf_pub *drvr;bool fwil_fwerr;};
struct cfg80211_connect_params {const u8 *ssid,*bssid;};
static int alloc_fail,fw_error,called,freed;
static size_t alloc_len,wire_len;
static u8 wire[128];
static void *mock_alloc(size_t n){alloc_len=n;return alloc_fail?NULL:calloc(1,n);}
#define kzalloc_obj(x) mock_alloc(sizeof(x))
#define kzalloc(n,f) mock_alloc(n)
static void kfree(void *p){freed++;free(p);}
static void eth_broadcast_addr(u8 *p){memset(p,255,6);}
static int brcmf_fil_bsscfg_data_set(struct brcmf_if *p,const char *name,void *buf,size_t n)
{assert(p->fwil_fwerr);assert(!strcmp(name,"join"));assert(n<=sizeof(wire));called++;wire_len=n;memcpy(wire,buf,n);return fw_error;}
'''
main=r'''
static void put32(u8 *p,u32 v){p[0]=v;p[1]=v>>8;p[2]=v>>16;p[3]=v>>24;}
int main(void){
 struct brcmf_pub d={0};struct brcmf_if p={&d,false};
 u8 ssid[32],bssid[6]={2,3,4,5,6,7};for(int i=0;i<32;i++)ssid[i]=(u8)(i+1);
 assert(offsetof(struct brcmf_ext_join_params_v1_le,assoc_le)==60);
 assert(offsetof(struct brcmf_assoc_params_v1_le,chanspec_list)==16);
 for(int channel=0;channel<2;channel++)for(int b=0;b<2;b++)for(int full=0;full<2;full++)for(int err=0;err<2;err++){
  struct cfg80211_connect_params c={ssid,b?bssid:NULL};u32 len=full?32:0;u16 ch=channel?0x1234:0;
  u8 expected[78]={0};put32(expected+4,len);memcpy(expected+8,ssid,len);expected[40]=255;
  put32(expected+44,channel?16:UINT32_MAX);put32(expected+48,channel?320:UINT32_MAX);
  put32(expected+52,channel?400:UINT32_MAX);put32(expected+56,UINT32_MAX);
  if(b)memcpy(expected+64,bssid,6);else memset(expected+64,255,6);
  put32(expected+72,channel);if(channel){expected[76]=0x34;expected[77]=0x12;}
  called=freed=0;fw_error=err?-7:0;alloc_fail=0;
  assert(brcmf_join_v1(&p,&c,len,ch)==(err?-EBADE:0));
  assert(called==1&&freed==1&&!p.fwil_fwerr);assert(wire_len==(channel?78:76));
  assert(alloc_len>=wire_len);assert(!memcmp(wire,expected,wire_len));
 }
 struct cfg80211_connect_params c={ssid,NULL};called=freed=0;alloc_fail=1;
 assert(brcmf_join_v1(&p,&c,32,0x1234)==-ENOMEM);assert(!called&&!freed&&!p.fwil_fwerr);
 puts("PASS exact wire layout, channel/BSSID/SSID variants, allocator and firmware errors");
}
'''
assert '__le16 chanspec_list[1];' in structs
flex=structs.replace('__le16 chanspec_list[1];','__le16 chanspec_list[];')
assert 'jp = kzalloc_obj(*jp);' in fn
fixed=fn.replace('jp = kzalloc_obj(*jp);','jp = kzalloc(len, GFP_KERNEL);')
with tempfile.TemporaryDirectory() as td:
 for name,st,func in [('baseline',structs,fn),('header_only',flex,fn),('fixed',flex,fixed)]:
  p=Path(td)/name;c=p.with_suffix('.c');c.write_text(pre+st+func+main)
  subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(c),'-o',str(p)],check=True)
  result=subprocess.run([str(p)],capture_output=True,text=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0'))
  if name=='header_only':
   assert result.returncode!=0 and 'AddressSanitizer' in result.stderr,(name,result)
   print('RED header-only mutation detected by ASan')
  else:
   assert result.returncode==0,(name,result.stderr);print(name,result.stdout.strip())
print('Hardware association is covered by separate W3 runtime evidence')
