from pathlib import Path
import subprocess,tempfile,sys
s=Path(sys.argv[1]).read_text();a=s.index('struct oriole_contact {');b=s.index('static void oriole_release_contacts',a);fn=s[a:b]
pre='''#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <assert.h>
#include <string.h>
#include <stdio.h>
typedef uint8_t u8;
'''
post='''
static void position(u8 *f,unsigned x,unsigned y){f[3]=x&255;f[4]=((y&15)<<4)|(x>>8);f[5]=y>>4;}
int main(void){
 u8 f[9]={0x87,0x23,0x01,0x20,0xa3,0x58,0x20,0x99,0};
 struct oriole_contact c={0};
 assert(oriole_decode_contact(f,9,1079,2399,&c)&&c.active&&c.slot==0&&c.x==800&&c.y==1418);
 f[1]=0x13;f[2]=0x91;position(f,1079,2399);
 assert(oriole_decode_contact(f,9,1079,2399,&c)&&c.slot==9&&c.x==1079&&c.y==2399);
 position(f,1080,2399);assert(!oriole_decode_contact(f,9,1079,2399,&c));
 position(f,1079,2400);assert(!oriole_decode_contact(f,9,1079,2399,&c));
 position(f,0,0);assert(oriole_decode_contact(f,9,1079,2399,&c));
 f[2]=0xa1;assert(!oriole_decode_contact(f,9,1079,2399,&c));
 f[2]=0x02;assert(!oriole_decode_contact(f,9,1079,2399,&c));f[2]=1;
 f[0]=0xa7;assert(!oriole_decode_contact(f,9,1079,2399,&c));f[0]=0x87;
 f[1]=0x65;assert(!oriole_decode_contact(f,9,1079,2399,&c));
 f[1]=0x43;assert(!oriole_decode_contact(f,9,1079,2399,&c));
 f[1]=0x20;assert(!oriole_decode_contact(f,9,1079,2399,&c));
 f[1]=0x33;position(f,4095,4095);assert(oriole_decode_contact(f,9,1079,2399,&c)&&!c.active);
 assert(!oriole_decode_contact(f,8,1079,2399,&c));assert(!oriole_decode_contact(f,10,1079,2399,&c));
 assert(!oriole_decode_contact(NULL,0,1079,2399,&c));
 puts("PASS actualdecoder: capturedmotion, enter/leave, edges, shortlength, wrongprefix/type/slot/coordinates; ASanUBSan");
}
'''
with tempfile.TemporaryDirectory(prefix='oriole-input28-') as td:
 p=Path(td);(p/'test.c').write_text(pre+fn+post)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
