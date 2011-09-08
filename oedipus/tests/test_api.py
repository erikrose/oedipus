"""Test the mapping from our API to Sphinx's.

We mock out all Sphinx's APIs.

"""
import fudge
from nose.tools import eq_, assert_raises
#from sphinxapi import SphinxClient
import sphinxapi  # Comes in sphinx source code tarball

from oedipus import S, SearchError


class Biscuit(object):
    """An arbitrary adaptation key that S can map to a SearchModel"""


class BiscuitSearch(object):
    """Search metadata for Biscuit"""


# def setup_module():
#     #plug.register_adapter(
#     ISearchModel.


@fudge.patch('sphinxapi.SphinxClient')
def test_initialization(sphinx_client):
    """The default modes should get set, and SearchError should be raised if you evaluate an S that's never had query() called on it."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()  # Call other crap on it if you want; I don't care.
                  .expects('SetMatchMode').with_args(sphinxapi.SPH_MATCH_EXTENDED2)
                  .expects('SetRankingMode').with_args(sphinxapi.SPH_RANK_PROXIMITY_BM25)
                  .expects('SetSortMode').with_args(sphinxapi.SPH_SORT_RELEVANCE, ''))

    s = S(Biscuit)
    # Should freak out since we didn't call query():
    assert_raises(SearchError, s._sphinx)


# @fudge.patch('SphinxClient')
# def test_no_restrictions(SphinxClient):
#     """Not filtering at all should produce a client that gets everything."""
#     s = S(Biscuit).query('gerbil')
#     eq_(, {'fields': ['id']})


def test_single_filter():
    """Test a single filter."""


def test_chained_filters():
    """Tests several filter() calls ANDed together."""
    