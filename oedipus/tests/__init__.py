from unittest import TestCase
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


class SphinxMockingTestCase(TestCase):
    """Testcase which mocks out Sphinx to return 2 results"""

    def setUp(self):
        Biscuit(id=123, color='red')
        Biscuit(id=124, color='blue')

    def tearDown(self):
        global model_cache
        model_cache = []

    def mock_sphinx(self, sphinx_client):
        # TODO: Do this in setUp() somehow.
        (sphinx_client.expects_call().returns_fake()
                      .is_a_stub()
                      .expects('RunQueries').returns(
                          [{'status': 0,
                            'total': 2,
                            'matches':
                                [{'attrs': {'color': 3},
                                 'id': 123,
                                 'weight': 11111},
                                 {'attrs': {'color': 4},
                                  'id': 124,
                                  'weight': 10000}]}]))


class BigSphinxMockingTestCase(TestCase):
    """Enforces one call to RunQueries and also makes more biscuits.

    Everyone likes biscuits.

    """
    def setUp(self):
        Biscuit(id=100, color='red')
        Biscuit(id=101, color='orange')
        Biscuit(id=102, color='yellow')
        Biscuit(id=103, color='green')
        Biscuit(id=104, color='blue')
        Biscuit(id=105, color='indigo')
        Biscuit(id=106, color='violet')

    def tearDown(self):
        global model_cache
        model_cache = []

    def mock_sphinx(self, sphinx_client):
        matches = [{'attrs': {'color': biscuit.id + 100},
                    'id': biscuit.id,
                    'weight': 10000}
                   for biscuit in model_cache]

        (sphinx_client.expects_call().returns_fake()
                      .is_a_stub()
                      .expects('RunQueries')
                      .times_called(1)
                      .returns(
                          [{'status': 0,
                            'total': len(matches),
                            'matches': matches}]))
