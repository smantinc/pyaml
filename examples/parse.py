#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import getopt

from libaml.aml import AML
from libaml.aml import ResTypes


INDENT_BLOCK = '  '


if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1:], 'i:')
    params = dict([(i.lstrip('-'), j) for i, j in opts])

    if 'i' not in params:
        print('Usage:\n%s -i android-binary-xml.xml' % sys.argv[0])
        sys.exit(0)

    infile = params['i']

    with open(infile, 'rb') as fp:
        buf = fp.read()

    aml = AML(buf)
    namespaces = []
    indent = 0
    while aml.hasnext():
        header, body = aml.next()
        if header.type == ResTypes.RES_XML_START_ELEMENT_TYPE:
            print(INDENT_BLOCK * indent + '<%s%s>' % (body.nodename, ''.join(namespaces + [' %s="%s"' % (i, i.typedValue.value) for i in body.attributes])))
            namespaces = []
            indent += 1
        elif header.type == ResTypes.RES_XML_END_ELEMENT_TYPE:
            indent -= 1
            print(INDENT_BLOCK * indent + '</%s>' % body.nodename)
        elif header.type == ResTypes.RES_XML_START_NAMESPACE_TYPE:
            namespaces.append(' xmlns:%s="%s"' % (body.name, body.namespace))
        elif header.type == ResTypes.RES_XML_TYPE:
            print('<?xml version="1.0" encoding="utf-8"?>')
