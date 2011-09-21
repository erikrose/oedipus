"""Test the mapping from our API to Sphinx's.

We mock out all Sphinx's APIs.

"""
import fudge
from nose import SkipTest
from nose.tools import eq_, assert_raises
import sphinxapi  # Comes in sphinx source code tarball

from oedipus import S, SearchError
from oedipus.tests import no_results, Biscuit


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
def test_count(sphinx_client):
    """Test ``S.__len__`` and ``S.count``."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('RunQueries').returns(no_results))
    s = S(Biscuit)
    eq_(len(s), 0)
    eq_(s.count(), 0)


@fudge.patch('sphinxapi.SphinxClient')
def test_connection_failure(sphinx_client):
    """``SearchError`` should be raised on connection error."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('RunQueries').returns(None))
    assert_raises(SearchError, S(Biscuit).raw)
