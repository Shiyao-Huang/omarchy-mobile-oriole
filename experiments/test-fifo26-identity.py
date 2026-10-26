from pathlib import Path
import sys,tempfile,subprocess
s=Path(sys.argv[1]).read_text();a=s.index(' if (!seen ||');b=s.index(' for(phase=',a);body=s[a:b]
pre='''#include <stdint.h>
#include <assert.h>
#include <string.h>
#include <stdio.h>
#define ENODEV 19
#define dev_err(...) ((void)0)
static uint16_t get_unaligned_le16(const uint8_t*p){return p[0]|((uint16_t)p[1]<<8);}
static int check(const uint8_t *data,int seen){
'''
post='''return 0;}
int main(void){
 uint8_t data[216]={0},saved[216];
 data[0]=0xa5;data[1]=1;data[10]=0x48;data[11]=0x36;data[16]=0x49;
 data[80]=0x5f;data[81]=9;data[82]=0x37;data[83]=4;
 memcpy(saved,data,sizeof data);
 assert(check(data,1)==0);assert(check(data,0)==-ENODEV);
 unsigned fields[]={0,1,10,11,16,17,80,81,82,83};
 for(unsigned n=0;n<sizeof(fields)/sizeof(fields[0]);n++){
  memcpy(data,saved,sizeof data);data[fields[n]]^=1;assert(check(data,1)==-ENODEV);
 }
 memset(data,0,sizeof data);assert(check(data,1)==-ENODEV);
 puts("PASS actual identity gate: exact match, missing ready, each identity byte corrupted, allzero frame");
}
'''
with tempfile.TemporaryDirectory(prefix='fifo26-identity-') as td:
 p=Path(td);(p/'test.c').write_text(pre+body+post)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
