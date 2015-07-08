#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import getopt

from libaml.aml import AML
from libaml.aml import ResTypes


"""
This example demonstrates the how to modify binary XML using libaml.
It parses AndroidManifest.xml and increases version code by one.
"""

if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1:], 'i:o:')
    params = dict([(i.lstrip('-'), j) for i, j in opts])

    if 'i' not in params:
        print('Usage:\n%s -i AndroidManifest.xml [-o outfile.xml]' % sys.argv[0])
        sys.exit(0)

    infile = params['i']
    outfile = params['o'] if 'o' in params else infile

    with open(infile, 'rb') as fp:
        buf = fp.read()

    aml = AML(buf)
    while aml.hasnext():
        header, body = aml.next()
        if header.type == ResTypes.RES_XML_START_ELEMENT_TYPE and body.nodename == 'manifest':
            for i in body.attributes:
                if str(i) == 'android:versionCode':
                    i.typedValue.data += 1

    with open(outfile, 'wb') as fp:
        fp.write(aml.tobytes())
    print('Done.')
