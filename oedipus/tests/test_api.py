"""Test the mapping from our API to Sphinx's.

We mock out all Sphinx's APIs.

"""
import zlib

import fudge
from nose import SkipTest
from nose.tools import eq_
import sphinxapi  # Comes in sphinx source code tarball

from oedipus import S, MIN_LONG, MAX_LONG


crc32 = lambda x: zlib.crc32(x.encode('utf-8')) & 0xffffffff


no_results = [dict(status=0, matches=[])]  # empty Sphinx results


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

class Biscuit(object):
    """An arbitrary adaptation key that S can map to a SearchModel"""

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


def test_chained_filters():
    """Test several filter() calls ANDed together."""


def test_results_as_objects():
    """Results should come back as Django model objects by default."""
    # ...though we mock those model objects because we don't really want to
    # depend on Django; anything with a similar API should work.


def test_defaults():
    """Defaults from the metadata should be obeyed."""
