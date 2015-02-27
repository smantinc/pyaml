#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ctypes
import struct
import pkgutil

from .utils.decorator import Struct


class ByteArrayBuffer:
    def __init__(self):
        self._buffers = []

    @property
    def size(self):
        return sum([i.size for i in self._buffers])

    def append(self, data):
        class ByBytes:
            def __init__(self, bytesbuf):
                self._bytesbuf = bytesbuf

            @property
            def size(self):
                return len(self._bytesbuf)

            def tobytes(self):
                return self._bytesbuf

        self._buffers.append(ByBytes(data) if type(data) is bytes else data)

    def tobytes(self):
        return b''.join([i.tobytes() for i in self._buffers])


class ResTypes:
    RES_NULL_TYPE = 0x0000
    RES_STRING_POOL_TYPE = 0x0001
    RES_TABLE_TYPE = 0x0002
    RES_XML_TYPE = 0x0003
    RES_XML_FIRST_CHUNK_TYPE = 0x0100
    RES_XML_START_NAMESPACE_TYPE = 0x0100
    RES_XML_END_NAMESPACE_TYPE = 0x0101
    RES_XML_START_ELEMENT_TYPE = 0x0102
    RES_XML_END_ELEMENT_TYPE = 0x0103
    RES_XML_CDATA_TYPE = 0x0104
    RES_XML_LAST_CHUNK_TYPE = 0x017f
    RES_XML_RESOURCE_MAP_TYPE = 0x0180
    RES_TABLE_PACKAGE_TYPE = 0x0200
    RES_TABLE_TYPE_TYPE = 0x0201
    RES_TABLE_TYPE_SPEC_TYPE = 0x0202


def parsestruct(buf, structformat):
    size = struct.calcsize(structformat)
    return struct.unpack(structformat, buf[:size])


class ResXMLElement:
    def __init__(self, node, stringpool, namespace, name):
        self._node = node
        self._stringpool = stringpool
        self._namespace = namespace
        self._name = name

    def tobytes(self):
        ns = 0xffffffff if not self._namespace else self._stringpool.getstringref(self._namespace)
        n = self._stringpool.getstringref(self._name)
        return struct.pack('II', ns, n)

    @property
    def node(self):
        return self._node

    @property
    def nodename(self):
        return self._name

    @property
    def size(self):
        return 8


@Struct('I', ['ref'])
class ResourceRef(object):
    def __init__(self, stringpool, value=None):
        self._stringpool = stringpool
        self._value = value
        self._ref = AML.NONE_NAMESPACE_REF

    @property
    def value(self):
        return self._value

    @property
    def ref(self):
        return AML.NONE_NAMESPACE_REF if self._value is None else self._stringpool.getstringref(self._value)

    @ref.setter
    def ref(self, ref):
        if ref != AML.NONE_NAMESPACE_REF:
            self._value = self._stringpool.originalstrings[ref]
        self._ref = ref

    def tobytes(self):
        return struct.pack('I', self.ref)


class ResChunk:
    @staticmethod
    def parse(buf):
        header, nul = ResChunk.Header.parse(buf, buffer=buf)
        return header, buf[:header.chunkSize]

    @Struct('HHI', ['type', 'headerSize', 'chunkSize'])
    class Header:
        def __init__(self, buffer=None):
            self._buf = buffer

        def tobytesbybuf(self):
            return self._buf[:self.headerSize]

        def getbody(self):
            return self._buf[self.headerSize:self.chunkSize]

        def getnextchunkbuf(self):
            return self._buf[self.chunkSize:]

        def dump(self):
            print('type = 0x%04x headerSize = %d size = %d' % (self.type, self.headerSize, self.chunkSize))


@Struct([ResourceRef, ResourceRef, 'HHHHHH'], ['ns', 'name', 'attributeStart', 'attributeSize',
                                               'attributeCount', 'idIndex', 'classIndex', 'styleIndex'])
class ResXMLTree_attrExt:
    pass


@Struct('HBBI', ['size', 'res0', 'dataType', 'data'])
class Res_value(object):
    # Contains no data.
    TYPE_NULL = 0x00
    # The 'data' holds a ResTable_ref, a reference to another resource
    # table entry.
    TYPE_REFERENCE = 0x01
    # The 'data' holds an attribute resource identifier.
    TYPE_ATTRIBUTE = 0x02
    # The 'data' holds an index into the containing resource table's
    # global value string pool.
    TYPE_STRING = 0x03
    # The 'data' holds a single-precision floating point number.
    TYPE_FLOAT = 0x04
    # The 'data' holds a complex number encoding a dimension value,
    # such as "100in".
    TYPE_DIMENSION = 0x05
    # The 'data' holds a complex number encoding a fraction of a
    # container.
    TYPE_FRACTION = 0x06

    # Beginning of integer flavors...
    TYPE_FIRST_INT = 0x10

    # The 'data' is a raw integer value of the form n..n.
    TYPE_INT_DEC = 0x10
    # The 'data' is a raw integer value of the form 0xn..n.
    TYPE_INT_HEX = 0x11
    # The 'data' is either 0 or 1, for input "false" or "true" respectively.
    TYPE_INT_BOOLEAN = 0x12

    # Beginning of color integer flavors...
    TYPE_FIRST_COLOR_INT = 0x1c

    # The 'data' is a raw integer value of the form #aarrggbb.
    TYPE_INT_COLOR_ARGB8 = 0x1c
    # The 'data' is a raw integer value of the form #rrggbb.
    TYPE_INT_COLOR_RGB8 = 0x1d
    # The 'data' is a raw integer value of the form #argb.
    TYPE_INT_COLOR_ARGB4 = 0x1e
    # The 'data' is a raw integer value of the form #rgb.
    TYPE_INT_COLOR_RGB4 = 0x1f

    # ...end of integer flavors.
    TYPE_LAST_COLOR_INT = 0x1f

    # ...end of integer flavors.
    TYPE_LAST_INT = 0x1f

    def __init__(self, stringpool, value=None):
        self._data = 0
        self._stringpool = stringpool
        self._value = value

    @property
    def data(self):
        if self.dataType == Res_value.TYPE_STRING and self._value:
            return self._stringpool.getstringref(self._value)
        return self._data

    @data.setter
    def data(self, val):
        self._data = val
        if self.dataType == Res_value.TYPE_STRING and val != AML.NONE_NAMESPACE_REF:
            self._value = self._stringpool.originalstrings[val]

    @property
    def value(self):
        if self.dataType == Res_value.TYPE_INT_DEC:
            return str(ctypes.c_int32(self._data).value)
        elif self.dataType == Res_value.TYPE_STRING:
            return self._stringpool.getstringbyref(self._data)
        elif self.dataType == Res_value.TYPE_INT_BOOLEAN:
            return 'true' if self._data else 'false'
        return '@%08x' % self._data


@Struct('II', ['lineNumber', 'comment'])
class ResXMLTree_node:
    pass


@Struct([ResourceRef, ResourceRef, 'I', Res_value], ['ns', 'name', 'rawValue', 'typedValue'])
class ResXMLTree_attribute:
    def __init__(self, aml=None):
        self._aml = aml

    @property
    def namespace(self):
        return self.ns.value

    @property
    def attributename(self):
        return self.name.value

    def __str__(self):
        if self.namespace:
            return '%s:%s' % (self._aml.namespaces[self.namespace], self.attributename)
        return self.attributename

    @staticmethod
    def make(ns, stringpool, name, value):
        if type(value) == str:
            resval = Res_value.create(8, 0, Res_value.TYPE_STRING, AML.NONE_NAMESPACE_REF, stringpool=stringpool, value=value)
        elif type(value) == bool:
            valueref = 0xffffffff if value else 0
            resval = Res_value.create(8, 0, Res_value.TYPE_INT_BOOLEAN, valueref, stringpool=stringpool)
        elif type(value) == int:
            resval = Res_value.create(8, 0, Res_value.TYPE_INT_DEC, value, stringpool=stringpool)
        else:
            print('Other data types aren\'t supported, sorry')
            raise NotImplementedError()
        return ResXMLTree_attribute.create(ns, name, 0xffffffff, resval)

    def tobytes(self):
        if self.typedValue.dataType == Res_value.TYPE_STRING:
            self.rawValue = self.typedValue.data
        return self._tobytes()


@Struct([ResChunk.Header, ResXMLTree_node, ResXMLTree_attrExt], ['header', 'node', 'attrExt'])
class ResXMLTree:
    def __init__(self, aml):
        self._attributes = []
        self._aml = aml

    @property
    def attributes(self):
        return self._attributes

    def tobytes(self):
        self.header.chunkSize = self.size
        self.attrExt.attributeCount = len(self._attributes)
        return self._tobytes() + b''.join([i.tobytes() for i in self._attributes])

    @property
    def nodename(self):
        return self.attrExt.name.value

    @property
    def size(self):
        return ResXMLTree._size + sum([i.size for i in self._attributes])


class AML:
    ANDROID_NAMESPACE = 'http://schemas.android.com/apk/res/android'
    NONE_NAMESPACE_REF = 0xffffffff

    class StringList:
        def __init__(self, strings):
            self._strings = strings
            self._stringmapping = dict((j, i) for i, j in enumerate(strings))

        def getstringref(self, s):
            return self._stringmapping[s]

        def __contains__(self, item):
            return item in self._stringmapping

        def __getitem__(self, item):
            return self._strings[item]

        def __len__(self):
            return len(self._strings)

    class Chunk:
        def __init__(self, header):
            self._bytebuffer = ByteArrayBuffer()
            self._header = header

        @property
        def size(self):
            return self._bytebuffer.size

        @property
        def body(self):
            return self._header.getbody()

        def append(self, data):
            self._bytebuffer.append(data)

        def tobytes(self):
            self._header.chunkSize = self.size + self._header.headerSize
            return b''.join([self._header.tobytes(),
                             self._header.tobytesbybuf()[ResChunk.Header.size:],
                             self._bytebuffer.tobytes()])

    class ResourceMapChunk:
        ATTRS = eval(pkgutil.get_data('libaml', 'android-attrs.json'))
        def __init__(self, header, strings):
            self._header = header
            idlen = int((header.chunkSize - header.headerSize) / 4)
            ids = parsestruct(header.getbody(), str(idlen) + 'I')
            self._attrs = [(strings[i], j) for i, j in enumerate(ids)]
            self._attrset = set([i for i, j in self._attrs])

        @property
        def attrs(self):
            return self._attrs

        @property
        def attrnames(self):
            return [i for i, j in self._attrs]

        def __contains__(self, attrname):
            return attrname in self._attrset

        def append(self, attrname):
            if attrname not in AML.ResourceMapChunk.ATTRS:
                print("Couldn't find R.attr.%s value" % attrname)
                raise NotImplementedError()
            self._attrs.append((attrname, AML.ResourceMapChunk.ATTRS[attrname]))

        @property
        def size(self):
            return self._header.headerSize + len(self._attrs) * 4

        def tobytes(self):
            self._header.chunkSize = self.size
            resources = [i[1] for i in self._attrs]
            return self._header.tobytes() + struct.pack(str(len(resources)) + 'I', *resources)

    class StringPoolChunk(object):
        # If set, the string index is sorted by the string values (based
        # on strcmp16()).
        SORTED_FLAG = 1 << 0
        # String pool is encoded in UTF-8
        UTF8_FLAG = 1 << 8

        class _UTF16StringList:
            def __init__(self, aml):
                self._aml = aml

            def loadstrings(self, buf):
                strings = []
                indices = {}
                for i in range(self._aml.stringCount):
                    stringlen = parsestruct(buf, 'H')[0]
                    s = buf[2:2 + stringlen * 2].decode('utf-16')
                    buf = buf[(stringlen + 1) * 2 + 2:]
                    strings.append(s)
                    indices[s] = i
                return strings, indices

            @property
            def size(self):
                return sum([len(i) * 2 + 4 for i in self._aml.strings])

        class _UTF8StringList:
            def __init__(self, aml):
                self._aml = aml

            def loadstrings(self, buf):
                strings = []
                indices = {}
                for i in range(self._aml.stringCount):
                    stringlen = parsestruct(buf, 'H')[0] & 0xff
                    s = buf[2:2 + stringlen].decode('utf-8')
                    buf = buf[(stringlen + 1) + 2:]
                    strings.append(s)
                    indices[s] = i
                return strings, indices

            @property
            def size(self):
                return sum([len(i) + 3 for i in self._aml.strings])

        def __init__(self, buf):
            self._resourcemap = None
            self._header, self._body = ResChunk.Header.parse(buf, buffer=buf)
            self.stringCount, self.styleCount, self.flags, self.stringsStart, self.stylesStart = parsestruct(buf[8:], '5I')
            self._stringlist = self._UTF8StringList(self) if self.flags & AML.StringPoolChunk.UTF8_FLAG else self._UTF16StringList(self)
            self._strings, self._indices = self._stringlist.loadstrings(buf[self.stringsStart:])
            self._originalstrings = list(self._strings)

        @property
        def originalstrings(self):
            return self._originalstrings

        @property
        def size(self):
            size = self.stringslen()
            return size + (4 - size % 4) % 4

        @property
        def attrs(self):
            return [] if self._resourcemap is None else self._resourcemap.attrnames

        @property
        def strings(self):
            return list(self._strings if self._resourcemap is None else self._resourcemap.attrnames + self._strings)

        @property
        def resourcemap(self):
            return self._resourcemap

        @resourcemap.setter
        def resourcemap(self, resourcemap):
            attrlen = len(resourcemap.attrs)
            self._strings = self.strings[attrlen:]
            self._resourcemap = resourcemap

        def getstringref(self, s):
            return self._indices[s]

        def getstringbyref(self, ref):
            attrslen = len(self.attrs)
            return self.attrs[ref] if ref < attrslen else self._strings[ref - attrslen]

        def stringslen(self):
            return sum([len(i) * 2 + 4 for i in self.strings]) + self.stringCount * 4 + self._header.headerSize

        def _append(self, s):
            self.stringCount += 1
            self.stringsStart = self.stringCount * 4 + self._header.headerSize

        def _rebuildindices(self):
            self._indices = dict((j, i) for i, j in enumerate(self.strings))

        def setattribute(self, name, value):
            if name not in self._resourcemap:
                self._resourcemap.append(name)
                self._append(name)
            if type(value) is str:
                self.ensure(value)
            self._rebuildindices()

        def ensure(self, s):
            if s not in self._indices:
                self._strings.append(s)
                self._append(s)
                self._indices[s] = len(self.attrs) + len(self._strings) - 1

        def tobytes(self):
            bos = ByteArrayBuffer()
            bos.append(self._header)
            self.stringCount = (0 if self._resourcemap is None else len(self._resourcemap.attrs)) + len(self._strings)
            self.stringsStart = self.stringCount * 4 + self._header.headerSize
            bos.append(struct.pack('5I', self.stringCount, self.styleCount, self.flags,
                                   self.stringsStart, self.stylesStart))

            class OffsetCalculator:
                def __init__(self):
                    self._offset = 0

                def offset(self, s):
                    l = len(s) * 2 + 4
                    o = self._offset
                    self._offset += l
                    return o

            calculator = OffsetCalculator()
            strings = self.strings
            stringmaps = [calculator.offset(i) for i in strings]
            bos.append(struct.pack(str(self.stringCount) + 'I', *stringmaps))
            for i in strings:
                bos.append(struct.pack(str(len(i) + 2) + 'H', *([len(i)] + [ord(j) for j in i] + [0])))
            self._header.chunkSize = self.size
            stringslen = self.stringslen()
            bos.append(b'\x00' * (self._header.chunkSize - stringslen))
            return bos.tobytes()

    class InsertedPlaceHolder:
        def __init__(self, aml, node):
            self._aml = aml
            self._node = node
            self._bytebuffer = ByteArrayBuffer()

        def append(self, data):
            self._bytebuffer.append(data)

        @property
        def size(self):
            return self._bytebuffer.size

        def tobytes(self):
            return self._bytebuffer.tobytes()

        def writexmlstartelement(self, name, attrs, linenumber=0):
            stringpool = self._aml.stringpool
            self._aml.stringpool.ensure(name)
            attrExt = ResXMLTree_attrExt.create(ResourceRef.create(AML.NONE_NAMESPACE_REF, stringpool=stringpool),
                                                ResourceRef.create(stringpool=stringpool, value=name),
                                                20, 20, len(attrs), 0, 0, 0)
            element = ResXMLTree.create(ResChunk.Header.create(ResTypes.RES_XML_START_ELEMENT_TYPE, 16, 0),
                                        ResXMLTree_node.create(linenumber or self._node.lineNumber, 0xffffffff),
                                        attrExt, aml=self)
            androidns = ResourceRef(stringpool=stringpool, value=AML.ANDROID_NAMESPACE)
            for k, v in attrs.items():
                stringpool.setattribute(k, v)
                attr = ResXMLTree_attribute.make(androidns, stringpool,
                                                 ResourceRef.create(stringpool=stringpool, value=k), v)
                element.attributes.append(attr)
            self._bytebuffer.append(element)
            return element

        def writexmlendelement(self, name, linenumber=0):
            self._bytebuffer.append(ResChunk.Header.create(ResTypes.RES_XML_END_ELEMENT_TYPE, 16, 24))
            self._bytebuffer.append(ResXMLTree_node.create(linenumber or self._node.lineNumber, 0xffffffff))
            self._bytebuffer.append(struct.pack('I', 0xffffffff))
            self._bytebuffer.append(ResourceRef(self._aml.stringpool, name))

    @Struct([ResourceRef, ResourceRef], ['_name', '_namespace'])
    class XMLNamespace:
        @property
        def name(self):
            return self._name.value

        @property
        def namespace(self):
            return self._namespace.value

    def __init__(self, buffer):
        self._namespaces = {}
        self._stringpool = None
        self._strings = None
        self._header, self._body = ResChunk.Header.parse(buffer, buffer=buffer)
        self._rootchunk = AML.Chunk(self._header)
        self._bufptr = self._rootchunk.body
        self._firstchunk = True

    @property
    def stringpool(self):
        return self._stringpool

    @property
    def strings(self):
        return self._strings

    @property
    def namespaces(self):
        return self._namespaces

    def hasnext(self):
        return self._firstchunk or len(self._bufptr) > 0

    def next(self):
        if self._firstchunk:
            self._firstchunk = False
            return self._header, self._body
        self._header, chunk = ResChunk.parse(self._bufptr)
        self._body = self._header.getbody()
        if self._header.type == ResTypes.RES_STRING_POOL_TYPE:
            self._stringpool = AML.StringPoolChunk(self._bufptr)
            self._strings = AML.StringList(self._stringpool.strings)
            self._rootchunk.append(self._stringpool)
        elif self._header.type == ResTypes.RES_XML_START_NAMESPACE_TYPE:
            self._body, nul = AML.XMLNamespace.parse(self._header.getbody(), stringpool=self._stringpool)
            self._namespaces[self._body.namespace] = self._body.name
            self._rootchunk.append(self._header.tobytesbybuf())
            self._rootchunk.append(self._body)
        elif self._header.type == ResTypes.RES_XML_START_ELEMENT_TYPE:
            self._body, nul = ResXMLTree.parse(self._bufptr, aml=self, stringpool=self._stringpool)
            self._rootchunk.append(self._body)
            buf = self._header.getbody()[self._body.attrExt.attributeStart:]
            for i in range(self._body.attrExt.attributeCount):
                attribute, p = ResXMLTree_attribute.parse(buf, stringpool=self._stringpool, aml=self)
                self._body.attributes.append(attribute)
                buf = buf[self._body.attrExt.attributeSize:]
        elif self._header.type == ResTypes.RES_XML_END_ELEMENT_TYPE:
            node, nul = ResXMLTree_node.parse(self._bufptr[8:])
            ns, name = parsestruct(self._header.getbody(), 'II')
            self._body = ResXMLElement(node, self._stringpool, None, self._strings[name])
            self._rootchunk.append(self._header.tobytesbybuf())
            self._rootchunk.append(self._body)
        elif self._header.type == ResTypes.RES_XML_END_NAMESPACE_TYPE:
            self._body, nul = AML.XMLNamespace.parse(self._header.getbody(), stringpool=self._stringpool)
            self._rootchunk.append(self._header.tobytesbybuf())
            self._rootchunk.append(self._body)
        elif self._header.type == ResTypes.RES_XML_RESOURCE_MAP_TYPE:
            self._stringpool.resourcemap = AML.ResourceMapChunk(self._header, self._strings)
            self._rootchunk.append(self._stringpool.resourcemap)
        else:
            self._rootchunk.append(chunk)
        self._bufptr = self._header.getnextchunkbuf()
        return self._header, self._body

    def insert(self):
        try:
            inserted = AML.InsertedPlaceHolder(self, self._body.node)
        except AttributeError:
            raise AssertionError('Cannot insert after none xml node types!')
        self._rootchunk.append(inserted)
        return inserted

    def tobytes(self):
        return self._rootchunk.tobytes()
