"""Test the mapping from our API to Sphinx's.

We mock out all Sphinx's APIs.

"""
import fudge
from nose.tools import eq_, assert_raises
import sphinxapi  # Comes in sphinx source code tarball

from oedipus import S, SearchError


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
    """Evaluating without calling query() should raise a SearchError."""
    s = S(Biscuit)
    # Should freak out since we didn't call query():
    #assert_raises(SearchError, s._sphinx)


@fudge.patch('sphinxapi.SphinxClient')
def test_simple_query(sphinx_client):
    """A lone call to query() should pass through to Sphinx.

    Control chars should be stripped.

    """
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('AddQuery').with_args('gerbil', 'biscuit')
                  .expects('RunQueries').returns([dict(status=0, matches=[])]))
    s = S(Biscuit).query(dummy='^$gerbil').raw()


def test_single_filter():
    """Test a single filter."""


def test_chained_filters():
    """Tests several filter() calls ANDed together."""


def test_defaults():
    """Defaults from the metadata should be obeyed."""
