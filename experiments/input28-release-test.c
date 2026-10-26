#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#define MT_TOOL_FINGER 0
struct input_dev {unsigned selected,bits,pointers,syncs;};
static void input_mt_slot(struct input_dev*d,unsigned s){assert(s<10);d->selected=s;}
static void input_mt_report_slot_state(struct input_dev*d,int tool,bool active){assert(tool==0&&!active);d->bits&=~(1u<<d->selected);}
static void input_mt_report_pointer_emulation(struct input_dev*d,bool count){assert(!count&&d->bits==0);d->pointers++;}
static void input_sync(struct input_dev*d){assert(d->bits==0);d->syncs++;}
static void oriole_release_contacts(struct input_dev *input)
{
 unsigned int slot;
 for(slot=0;slot<10;slot++) {
  input_mt_slot(input,slot);
  input_mt_report_slot_state(input,MT_TOOL_FINGER,false);
 }
 input_mt_report_pointer_emulation(input,false);
 input_sync(input);
}

int main(void){struct input_dev d={0,(1u<<0)|(1u<<5)|(1u<<9),0,0};oriole_release_contacts(&d);assert(d.bits==0&&d.syncs==1);oriole_release_contacts(&d);assert(d.bits==0&&d.syncs==2&&d.pointers==2);puts("PASS actualrelease: multiple activecontacts released before final sync, repeat safe");}