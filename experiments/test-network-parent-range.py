from pathlib import Path
import subprocess,tempfile
helper=Path(__file__).with_name('network-enum-overlay').joinpath('parent-range.inc').read_text()
src='#include <assert.h>\n#include <stdbool.h>\n#include <stdint.h>\ntypedef uint32_t u32;\n'+helper+'''
int main(void) {
 u32 v[4]={0,0,0,0x40000000};
 assert(oriole_parent_range_valid(v,16,1,1));
 assert(!oriole_parent_range_valid(v,32,1,1));
 assert(!oriole_parent_range_valid(v,16,2,1));
 assert(!oriole_parent_range_valid(v,16,1,2));
 for (unsigned i=0;i<4;i++){v[i]^=1;assert(!oriole_parent_range_valid(v,16,1,1));v[i]^=1;}
 return 0;
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'test.c';p.write_text(src);b=Path(d)/'test';subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p),'-o',str(b)],check=True);subprocess.run([str(b)],check=True)
print('PARENT_RANGE_GUARD_PASS')
