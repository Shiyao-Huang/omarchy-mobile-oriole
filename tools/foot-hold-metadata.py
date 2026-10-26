#!/usr/bin/env python3
"""Add the missing Foot hold capability to an existing desktop entry.
Leaves all existing fields and other desktop groups intact.
"""
def with_hold(text):
    lines=text.splitlines(keepends=True)
    if lines.count('[Desktop Entry]\n')!=1:raise ValueError('Expected one Desktop Entry')
    start=lines.index('[Desktop Entry]\n');end=next((i for i in range(start+1,len(lines)) if lines[i].startswith('[')),len(lines))
    fields=dict(line.strip().split('=',1) for line in lines[start+1:end] if '=' in line and not line.lstrip().startswith('#'))
    if fields.get('Exec')!='foot':raise ValueError('Only the verified Foot entry is supported')
    for key in ('TerminalArgHold','X-TerminalArgHold'):
        if key in fields:
            if fields[key]=='--hold':return text
            raise ValueError('Existing hold setting requires review')
    lines.insert(start+1,'X-TerminalArgHold=--hold\n')
    return ''.join(lines)
