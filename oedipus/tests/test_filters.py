"""Tests for queries, filters, and excludes"""

import fudge
from nose import SkipTest
from nose.tools import eq_

from oedipus import S, MIN_LONG, MAX_LONG
from oedipus.tests import no_results, Biscuit, crc32


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


def test_consolidate_ranges():
    """Assert that _consolidate_ranges() collapses lte/gte pairs."""
    input = [('category', 'gte', 1),
             ('category', 'lte', 10),
             ('category', '', 5),
             ('name', '', 'frank'),
             ('pog', 'gte', 0)]
    output = set([('category', 'RANGE', (1, 10)),
                  ('category', '', 5),
                  ('name', '', 'frank'),
                  ('pog', 'gte', 0)])
    eq_(set(S._consolidate_ranges(input)), output)


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
def test_filter_string_mapping(sphinx_client):
    """String values need to be mapped to ints for filtering."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetFilter').with_args('a', [crc32('test')], False)
                  .expects('RunQueries').returns(no_results))
    S(Biscuit).filter(a='test').raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_chained_filters_and_excludes(sphinx_client):
    """Test several filter() and exclude() calls ANDed together."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetFilter').with_args('a', [1], False)
                  .expects('SetFilter').with_args('b', [2], False)
                  .expects('SetFilter').with_args('c', [3], True)
                  .expects('RunQueries').returns(no_results))
    S(Biscuit).filter(a=1).filter(b=2).exclude(c=3).raw()
