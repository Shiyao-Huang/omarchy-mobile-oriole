from pathlib import Path
import subprocess,tempfile,sys
src=Path(sys.argv[1]).read_text();mode=sys.argv[2]
if mode=='green':
 a=src.index('static void oriole_fts_free_dma(');b=src.index('\n#endif',a);fn=src[a:b]
else:
 a=src.index('#ifdef CONFIG_I2C_BY_DMA',src.index('ProbeErrorExit_7:'));b=src.index('#endif',a);body=src[a:b].split('\n',1)[1];fn='static void oriole_fts_free_dma(struct fts_ts_info *info) {\n'+body+'\n}'
pre='''#include <stdlib.h>
#include <assert.h>
#include <stdio.h>
struct dma {char *rdBuf,*wrBuf;};struct fts_ts_info {struct dma *dma_buf;};
#define kfree free
'''
post='''
int main(void) {
 struct fts_ts_info info={calloc(1,sizeof(struct dma))};
 info.dma_buf->rdBuf=malloc(4096);info.dma_buf->wrBuf=malloc(4096);
 oriole_fts_free_dma(&info); assert(info.dma_buf==NULL);
 oriole_fts_free_dma(&info);
 info.dma_buf=calloc(1,sizeof(struct dma));info.dma_buf->rdBuf=malloc(4096);
 oriole_fts_free_dma(&info);assert(info.dma_buf==NULL);
 info.dma_buf=calloc(1,sizeof(struct dma));oriole_fts_free_dma(&info);
 puts("PASS full allocation, partial allocation, null, repeated cleanup");
}
'''
with tempfile.TemporaryDirectory(prefix='oriole-free-') as td:
 p=Path(td);(p/'test.c').write_text(pre+fn+post)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-g',str(p/'test.c'),'-o',str(p/'test')],check=True)
 q=subprocess.run([str(p/'test')],capture_output=True,text=True)
 if mode=='red':
  assert q.returncode!=0 and 'heap-use-after-free' in q.stderr
  print('RED reproduced: AddressSanitizer heap-use-after-free in inherited probe cleanup')
 else:
  assert q.returncode==0,(q.returncode,q.stderr);print(q.stdout.strip())
