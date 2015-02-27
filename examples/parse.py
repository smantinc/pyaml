#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import getopt

from libaml.aml import AML
from libaml.aml import ResTypes


if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1:], 'i:')
    params = dict([(i.lstrip('-'), j) for i, j in opts])
    infile = params['i']

    with open(infile, 'rb') as fp:
        buf = fp.read()

    aml = AML(buf)
    while aml.hasnext():
        header, body = aml.next()
        if header.type == ResTypes.RES_XML_START_ELEMENT_TYPE:
            print('<%s%s>' % (body.nodename, ''.join([' %s="%s"' % (i, i.typedValue.value) for i in body.attributes])))
        elif header.type == ResTypes.RES_XML_START_NAMESPACE_TYPE:
            print('xmlns:%s="%s"' % (body.name, body.namespace))
