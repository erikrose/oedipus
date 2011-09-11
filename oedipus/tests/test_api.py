"""Test the mapping from our API to Sphinx's.

We mock out all Sphinx's APIs.

"""
import fudge
from nose import SkipTest
import sphinxapi  # Comes in sphinx source code tarball

from oedipus import S, MIN_LONG, MAX_LONG


no_results = [dict(status=0, matches=[])]  # empty Sphinx results


class Biscuit(object):
    """An arbitrary adaptation key that S can map to a SearchModel"""

    class SphinxMeta(object):
        """Search metadata for Biscuit"""
        index = 'biscuit'


@fudge.patch('sphinxapi.SphinxClient')
def test_initialization(sphinx_client):
    """S-wide default modes should get set when the SphinxClient is made."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()  # Call other crap on it if you want; I don't care.
                  .expects('SetMatchMode').with_args(sphinxapi.SPH_MATCH_EXTENDED2)
                  .expects('SetRankingMode').with_args(sphinxapi.SPH_RANK_PROXIMITY_BM25)
                  .expects('SetSortMode').with_args(sphinxapi.SPH_SORT_RELEVANCE, ''))
    S(Biscuit)._sphinx()


@fudge.patch('sphinxapi.SphinxClient')
def test_no_query(sphinx_client):
    """Evaluating without calling query() should run an empty query."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('AddQuery').with_args('', 'biscuit')
                  .expects('RunQueries').returns([dict(status=0, matches=[])]))
    S(Biscuit).raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_simple_query(sphinx_client):
    """A lone call to query(any_=...) should pass through to Sphinx.

    Control chars should be stripped. Other kwargs should be ignored.

    """
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('AddQuery').with_args('gerbil', 'biscuit')
                  .expects('RunQueries').returns([dict(status=0, matches=[])]))
    S(Biscuit).query(any_='^$gerbil', ignored_kwarg='dummy').raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_single_filter(sphinx_client):
    """A filter call should be translated into the right Sphinx API calls."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetFilter').with_args('a', [1])
                  .expects('SetFilter').with_args('b', [2, 3])

                  # These 2 lines must be ordered such. Why? Fudge bug?
                  .expects('SetFilterRange').with_args('d', MIN_LONG, 5)
                  .expects('SetFilterRange').with_args('c', 4, MAX_LONG)

                  .expects('RunQueries').returns(no_results))
    S(Biscuit).filter(a=1,  # Test auto-listification of ints for equality filters.
                      b__in=[2, 3],
                      c__gte=4,
                      d__lte=5).raw()


def test_results_as_objects():
    """Results should come back as Django model objects by default."""
    # ...though we mock those model objects because we don't really want to
    # depend on Django; anything with a similar API should work.


def test_chained_filters():
    """Test several filter() calls ANDed together."""


def test_filter_adapters():
    """You should be able to set up conversions of enumerations to hashes, for example."""


def test_defaults():
    """Defaults from the metadata should be obeyed."""
