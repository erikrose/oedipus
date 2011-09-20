"""Test the mapping from our API to Sphinx's.

We mock out all Sphinx's APIs.

"""
from unittest import TestCase
import zlib

import fudge
from nose import SkipTest
from nose.tools import eq_, assert_raises
import sphinxapi  # Comes in sphinx source code tarball

from oedipus import S, MIN_LONG, MAX_LONG, SearchError


crc32 = lambda x: zlib.crc32(x.encode('utf-8')) & 0xffffffff


no_results = [dict(status=0, total=0, matches=[])]  # empty Sphinx results
model_cache = []


def convert_str(value):
    if isinstance(value, str):
        return crc32(value)
    return value


class BaseSphinxMeta(object):
    """Search metadata for Biscuit classes"""
    index = 'biscuit'
    filter_mapping = {
        'a': convert_str
        }


class QuerySet(list):
    """A list that also acts in a few ways like Django's QuerySets"""
    def values(self, *attrs):
        return [dict((k, v) for k, v in o.__dict__.iteritems()
                            if not attrs or k in attrs)
                for o in self]


class Manager(object):
    def filter(self, id__in=None):
        return QuerySet([m for m in model_cache if m.id in id__in])


class Biscuit(object):
    """A mocked-out Django model"""
    objects = Manager()

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        model_cache.append(self)

    SphinxMeta = BaseSphinxMeta


class BiscuitOrderDefault(object):
    """An arbitrary adaptation key that S can map to a SearchModel"""

    class SphinxMeta(BaseSphinxMeta):
        ordering = 'a'


class BiscuitOrderDefaultList(object):
    """An arbitrary adaptation key that S can map to a SearchModel"""

    class SphinxMeta(BaseSphinxMeta):
        ordering = ['a', 'b']


class BiscuitWithWeight(object):
    """Biscuit with default weights"""

    class SphinxMeta(BaseSphinxMeta):
        weights = {'a': 5, 'b': 5}


@fudge.patch('sphinxapi.SphinxClient')
def test_initialization(sphinx_client):
    """S-wide default modes should get set when the SphinxClient is made."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()  # Call other crap on it if you want; I don't care.
                  .expects('SetMatchMode').with_args(sphinxapi.SPH_MATCH_EXTENDED2)
                  .expects('SetRankingMode').with_args(sphinxapi.SPH_RANK_PROXIMITY_BM25)
                  .expects('SetSortMode').with_args(sphinxapi.SPH_SORT_EXTENDED, '@weight DESC, @id ASC'))
    S(Biscuit)._sphinx()


@fudge.patch('sphinxapi.SphinxClient')
def test_no_query(sphinx_client):
    """Evaluating without calling query() should run an empty query."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('AddQuery').with_args('', 'biscuit')
                  .expects('RunQueries').returns(no_results))
    S(Biscuit).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_simple_query(sphinx_client):
    """A lone call to query(any_=...) should pass through to Sphinx.

    Control chars should be stripped. Other kwargs should be ignored.

    """
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('AddQuery').with_args('gerbil', 'biscuit')
                  .expects('RunQueries').returns(no_results))
    S(Biscuit).query('^$gerbil', ignored_kwarg='dummy').raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_single_filter(sphinx_client):
    """A filter call should be translated into the right Sphinx API calls."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetFilter').with_args('a', [1], False)
                  .expects('SetFilter').with_args('b', [2, 3], False)

                  # These 2 lines must be ordered such because fudge assumes,
                  # when you call one method twice, that order matters.
                  .expects('SetFilterRange').with_args('c', 4, MAX_LONG, False)
                  .expects('SetFilterRange').with_args('d', MIN_LONG, 5, False)

                  .expects('RunQueries').returns(no_results))
    S(Biscuit).filter(a=1,  # Test auto-listification of ints for equality filters.
                      b__in=[2, 3],
                      c__gte=4,
                      d__lte=5).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_weight_one(sphinx_client):
    """Test a single weight adjustment."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetFieldWeights').with_args({'a': 1})
                  .expects('RunQueries')
                  .returns(no_results))
    S(Biscuit).weight(a=1).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_weight_multiple(sphinx_client):
    """Test a multiple weight adjustment."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetFieldWeights').with_args({'a': 1, 'b': 2})
                  .expects('RunQueries')
                  .returns(no_results))
    S(Biscuit).weight(a=1, b=2).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_weight_chaining(sphinx_client):
    """Tests chaining of weights.

    Multiple calls get squashed into one set of weights.

    """
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetFieldWeights').with_args({'a': 1, 'b': 2})
                  .expects('RunQueries')
                  .returns(no_results))
    S(Biscuit).weight(a=1).weight(b=2).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_weight_chaining_same_item(sphinx_client):
    """Tests chaining on the same item."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetFieldWeights').with_args({'a': 2})
                  .expects('RunQueries')
                  .returns(no_results))
    S(Biscuit).weight(a=1).weight(a=2).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_weights_with_defaults(sphinx_client):
    """Tests chaining on the same item."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetFieldWeights').with_args({'a': 5, 'b': 5})
                  .expects('RunQueries')
                  .returns(no_results))
    S(BiscuitWithWeight).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_weights_with_defaults_and_change(sphinx_client):
    """Tests chaining on the same item."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetFieldWeights').with_args({'a': 3, 'b': 5})
                  .expects('RunQueries')
                  .returns(no_results))
    S(BiscuitWithWeight).weight(a=3).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_single_exclude(sphinx_client):
    """Assert conditions invert correctly."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetFilter').with_args('b', [2, 3], True)
                  .expects('RunQueries').returns(no_results))
    S(Biscuit).exclude(b__in=[2, 3]).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_range_exclude(sphinx_client):
    """Putting a gte and a lte exclusion on the same field in the same call should set a single filter range exclusion on the query.

    Otherwise, there would be no way to say "Give me docs with X between 1 and
    10."

    """
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetFilterRange').with_args('a', 1, 10, True)
                  .expects('RunQueries').returns(no_results))
    S(Biscuit).exclude(a__gte=1, a__lte=10).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_chained_excludes(sphinx_client):
    """Test combining excludes, and test remaining filter inversions."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetFilter').with_args('b', [2], True)
                  .expects('SetFilterRange').with_args('c', 4, MAX_LONG, True)
                  .expects('SetFilterRange').with_args('d', MIN_LONG, 5, True)
                  .expects('RunQueries').returns(no_results))
    S(Biscuit).exclude(b=2).exclude(c__gte=4).exclude(d__lte=5).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_range_filter(sphinx_client):
    """Putting a gte and a lte exclusion on the same field in the same call should set a single filter range exclusion on the query.

    Otherwise, there would be no way to say "Give me docs with X between 1 and
    10."

    """
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetFilterRange').with_args('a', 1, 10, False)
                  .expects('RunQueries').returns(no_results))
    S(Biscuit).filter(a__gte=1, a__lte=10).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_order_by_fields(sphinx_client):
    """Test ordering by only field values."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetSortMode')
                  .with_args(sphinxapi.SPH_SORT_EXTENDED, 'a ASC, b DESC')
                  .expects('RunQueries').returns(no_results))
    S(Biscuit).order_by('a', '-b').raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_order_by_rank_explicitly(sphinx_client):
    """Test mixing the @rank pseudo-field into the ``order_by()``."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetSortMode')
                  .with_args(sphinxapi.SPH_SORT_EXTENDED,
                             'a ASC, @weight DESC, @id ASC')
                  .expects('RunQueries').returns(no_results))
    S(Biscuit).order_by('a', '-@rank').raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_filter_string_mapping(sphinx_client):
    """String values need to be mapped to ints for filtering."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetFilter').with_args('a', [crc32('test')], False)
                  .expects('RunQueries').returns(no_results))
    S(Biscuit).filter(a='test').raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_order_by_default(sphinx_client):
    """Assert that results order by rank by default."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetSortMode')
                  .with_args(sphinxapi.SPH_SORT_EXTENDED,
                             '@weight DESC, @id ASC')
                  .expects('RunQueries').returns(no_results))
    S(Biscuit).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_order_by_ordering_single(sphinx_client):
    """Test ``ordering`` attribute with a single value."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetSortMode')
                  .with_args(sphinxapi.SPH_SORT_EXTENDED,
                             'a ASC')
                  .expects('RunQueries').returns(no_results))
    S(BiscuitOrderDefault).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_order_by_ordering_list(sphinx_client):
    """Test ``ordering`` attribute with list of values."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetSortMode')
                  .with_args(sphinxapi.SPH_SORT_EXTENDED,
                             'a ASC, b ASC')
                  .expects('RunQueries').returns(no_results))
    S(BiscuitOrderDefaultList).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_count(sphinx_client):
    """Test ``S.__len__`` and ``S.count``."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('RunQueries').returns(no_results))
    s = S(Biscuit)
    eq_(len(s), 0)
    eq_(s.count(), 0)


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


class ResultsTestCase(SphinxMockingTestCase):
    """Tests for various result formatters"""

    @fudge.patch('sphinxapi.SphinxClient')
    def test_objects(self, sphinx_client):
        """Test constructing and iterating over object-style results."""
        self.mock_sphinx(sphinx_client)

        results = list(S(Biscuit))  # S.__iter__ and DictResults.__iter__

        eq_(results[0].color, 'red')
        eq_(results[1].color, 'blue')

    @fudge.patch('sphinxapi.SphinxClient')
    def test_dicts_all_fields(self, sphinx_client):
        """Test constructing and iterating over dict-style results returning all model fields."""
        self.mock_sphinx(sphinx_client)
        results = list(S(Biscuit).values_dict())
        eq_(results, [{'color': 'red', 'id': 123},
                      {'color': 'blue', 'id': 124}])

    @fudge.patch('sphinxapi.SphinxClient')
    def test_dicts_without_id(self, sphinx_client):
        """Test dict-style results with explicit fields excluding ID."""
        self.mock_sphinx(sphinx_client)
        results = list(S(Biscuit).values_dict('color'))
        eq_(results, [{'color': 'red'},
                      {'color': 'blue'}])

    @fudge.patch('sphinxapi.SphinxClient')
    def test_dicts_overriding(self, sphinx_client):
        """Calls to ``values_dict()`` should override previous ones."""
        self.mock_sphinx(sphinx_client)
        results = list(S(Biscuit).values_dict('color').values_dict('id'))
        eq_(results, [{'id': 123},
                      {'id': 124}])

    @fudge.patch('sphinxapi.SphinxClient')
    def test_tuples(self, sphinx_client):
        """Test constructing and iterating over tuple-style results returning all model fields."""
        self.mock_sphinx(sphinx_client)
        results = list(S(Biscuit).values('id', 'color'))
        eq_(results, [(123, 'red'), (124, 'blue')])

    @fudge.patch('sphinxapi.SphinxClient')
    def test_tuples_without_id(self, sphinx_client):
        """Test tuple-style results that don't return ID."""
        self.mock_sphinx(sphinx_client)
        results = list(S(Biscuit).values('color'))
        eq_(results, [('red',), ('blue',)])

    @fudge.patch('sphinxapi.SphinxClient')
    def test_tuples_overriding(self, sphinx_client):
        """Calls to ``values()`` should override previous ones."""
        self.mock_sphinx(sphinx_client)
        results = list(S(Biscuit).values('color').values('id'))
        eq_(results, [(123,), (124,)])

    @fudge.patch('sphinxapi.SphinxClient')
    def test_tuples_no_fields(self, sphinx_client):
        """An empty values() call should raise ``TypeError``."""
        s = S(Biscuit)
        assert_raises(TypeError, s.values)


@fudge.patch('sphinxapi.SphinxClient')
def test_connection_failure(sphinx_client):
    """``SearchError`` should be raised on connection error."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('RunQueries').returns(None))
    assert_raises(SearchError, S(Biscuit).raw)


def test_chained_filters():
    """Test several filter() calls ANDed together."""


def test_defaults():
    """Defaults from the metadata should be obeyed."""
