"""Execute the candidate's actual SPI wrapper with allocation/transport faults.
This tests memory ownership and call contracts, not kernel SPI timing/hardware.
"""
from pathlib import Path
import tempfile,subprocess,sys
src=Path(sys.argv[1]).read_text();a=src.index('static int oriole_fts_spi_sync(');b=src.index('\n#endif',a);fn=src[a:b]
pre=r'''
#include <assert.h>
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t u8;
#define GFP_KERNEL 0
struct spi_transfer { void *rx_buf; const void *tx_buf; unsigned len; struct spi_transfer *next; };
struct spi_message { struct spi_transfer *transfers; };
struct spi_device { int unused; };
#define list_for_each_entry(p,h,m) for(p=*(h);p;p=p->next)
static int alloc_fail,allocated,calls,transport_ret; static const void *preserved;
static void *kzalloc(size_t n,int flags) { (void)flags; if(alloc_fail)return NULL;void *p=calloc(1,n);if(p)allocated++;return p; }
static void kfree(void *p){assert(p);allocated--;free(p);}
static int spi_sync(struct spi_device *dev,struct spi_message *m){(void)dev;calls++; for(struct spi_transfer*x=m->transfers;x;x=x->next)if(x->rx_buf){assert(x->tx_buf);if(x->tx_buf!=preserved)for(unsigned i=0;i<x->len;i++)assert(((u8*)x->tx_buf)[i]==0);}return transport_ret;}
'''
post=r'''
int main(void){
 struct spi_device d={0};u8 rx[217],tx[217];memset(tx,0xa5,sizeof(tx));preserved=tx;
 struct spi_transfer a={.tx_buf=tx,.len=3},b={.rx_buf=rx,.len=217},c={.rx_buf=rx,.len=1};struct spi_message m={&a};
 assert(oriole_fts_spi_sync(&d,&m)==0&&calls==1&&allocated==0); /* write only */
 a.next=&b;assert(oriole_fts_spi_sync(&d,&m)==0&&calls==2&&b.tx_buf==NULL&&allocated==0);
 transport_ret=-EIO;assert(oriole_fts_spi_sync(&d,&m)==-EIO&&calls==3&&b.tx_buf==NULL&&allocated==0);transport_ret=0;
 alloc_fail=1;assert(oriole_fts_spi_sync(&d,&m)==-ENOMEM&&calls==3&&b.tx_buf==NULL&&allocated==0);alloc_fail=0;
 b.len=0;assert(oriole_fts_spi_sync(&d,&m)==-EINVAL&&calls==3);b.len=65537;assert(oriole_fts_spi_sync(&d,&m)==-EINVAL&&calls==3);b.len=217;
 b.next=&c;assert(oriole_fts_spi_sync(&d,&m)==-EINVAL&&calls==3&&allocated==0);b.next=NULL;
 b.tx_buf=tx;assert(oriole_fts_spi_sync(&d,&m)==0&&calls==4&&b.tx_buf==tx&&allocated==0);
 for(unsigned i=0;i<5;i++){unsigned lengths[]={1,9,32,33,217};b.tx_buf=NULL;b.len=lengths[i];assert(oriole_fts_spi_sync(&d,&m)==0&&b.tx_buf==NULL&&allocated==0);}
 puts("PASS: write-only, zero-clock RX, SPI error cleanup, ENOMEM, zero/oversize, multiple RX, existing TX ownership");
}
'''
with tempfile.TemporaryDirectory(prefix='oriole-rx-test-') as td:
 p=Path(td);(p/'test.c').write_text(pre+fn+post)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-g',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
