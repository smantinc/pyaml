#!/usr/bin/env python
# -*- coding: utf-8 -*-

import inspect
import struct

class Struct:
    def __init__(self, signature, fieldnames):
        self._signature = signature
        self._fieldnames = fieldnames
        self._structs = Struct.initstructs(signature, fieldnames)
        self._structsize = Struct.calculatesize(signature)

    @staticmethod
    def initstructs(signature, fieldnames):
        nameoffset = 0

        class BySignature:
            def __init__(self, names, signature):
                self._signature = signature
                self._names = names
                self._size = struct.calcsize(signature)

            def parse(self, _buf, *args, **kwargs):
                return zip(self._names, struct.unpack(self._signature, _buf[:self._size])), _buf[self._size:]

            def tobytes(self, obj):
                return struct.pack(self._signature, *[getattr(obj, i) for i in self._names])

        class ByStruct:
            def __init__(self, name, st):
                self._name = name
                self._struct = st

            def parse(self, _buf, *args, **kwargs):
                obj, nextbuf = self._struct.parse(_buf, *args, **kwargs)
                return [(self._name, obj)], nextbuf

            def tobytes(self, obj):
                st = getattr(obj, self._name)
                return st.tobytes()

        structs = []
        if type(signature) is str:
            structs.append(BySignature(fieldnames, signature))
        else:
            for sig in signature:
                if type(sig) is str:
                    names = fieldnames[nameoffset:nameoffset+len(sig)]
                    nameoffset += len(names)
                    structs.append(BySignature(names, sig))
                else:
                    name = fieldnames[nameoffset]
                    nameoffset += 1
                    structs.append(ByStruct(name, sig))
        return structs

    @staticmethod
    def calculatesize(signature):
        return sum([struct.calcsize(i) if type(i) is str else i.size for i in signature])

    @staticmethod
    def override(cls, name, attr):
        if hasattr(cls, name):
            setattr(cls, '_' + name, attr)
        else:
            setattr(cls, name, attr)

    def __call__(self, cls):
        def getinitargs(kwargs):
            return dict([(k, v) for k, v in kwargs.items() if k in cls._INIT_KWARGS])

        def create(*args, **kwargs):
            s = cls(**getinitargs(kwargs))
            for i, j in enumerate(args):
                setattr(s, self._fieldnames[i], j)
            return s

        def tobytes(s):
            bos = [i.tobytes(s) for i in self._structs]
            return b''.join(bos)

        def parse(buf, *args, **kwargs):
            obj = cls(*args, **getinitargs(kwargs))
            for i in self._structs:
                items, buf = i.parse(buf, *args, **kwargs)
                for k, v in items:
                    setattr(obj, k, v)
            return obj, buf

        try:
            cls._INIT_KWARGS = set(inspect.getargspec(cls.__init__)[0][1:])
        except (TypeError, AttributeError):
            cls._INIT_KWARGS = set([])
        Struct.override(cls, 'tobytes', tobytes)
        Struct.override(cls, 'create', staticmethod(create))
        Struct.override(cls, 'parse', staticmethod(parse))
        Struct.override(cls, 'size', self._structsize)
        return cls


@Struct('HHI', ['type', 'headerSize', 'size'])
class MyStruct:
    pass


@Struct(['II', MyStruct, 'HHL'], ['id', 'name', 'typedValue', 's1', 's2', 's3'])
class MyAnotherStruct:
    pass

if __name__ == '__main__':
    s1 = MyStruct.create(10, 20, 30)
    buf = s1.tobytes()
    s1, p = MyStruct.parse(buf)
    ss = MyAnotherStruct.create(1, 2, s1, 3, 4, 5)
    buf = ss.tobytes()
    ss1, p = MyAnotherStruct.parse(buf)
    print(str(ss1))