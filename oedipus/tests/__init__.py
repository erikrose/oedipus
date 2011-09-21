import zlib


no_results = [dict(status=0, total=0, matches=[])]  # empty Sphinx results
crc32 = lambda x: zlib.crc32(x.encode('utf-8')) & 0xffffffff


def convert_str(value):
    if isinstance(value, str):
        return crc32(value)
    return value


class BaseSphinxMeta(object):
    """Search metadata for Biscuit classes"""
    index = 'biscuit'
    filter_mapping = {'a': convert_str}


class QuerySet(list):
    """A list that also acts in a few ways like Django's QuerySets"""
    def values(self, *attrs):
        return [dict((k, v) for k, v in o.__dict__.iteritems()
                            if not attrs or k in attrs)
                for o in self]


class Manager(object):
    def filter(self, id__in=None):
        return QuerySet([m for m in model_cache if m.id in id__in])


model_cache = []


class Biscuit(object):
    """A mocked-out Django model"""
    objects = Manager()

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        model_cache.append(self)

    SphinxMeta = BaseSphinxMeta
