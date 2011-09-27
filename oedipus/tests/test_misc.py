"""Test the mapping from our API to Sphinx's.

We mock out all Sphinx's APIs.

"""
import fudge
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
    assert_raises(SearchError, S(Biscuit)._raw)


@fudge.patch('sphinxapi.SphinxClient')
@fudge.patch('oedipus.settings')
def test_sphinx_max_results_clips(sphinx_client, settings):
    """Test SPHINX_MAX_RESULTS affects results."""
    settings.has_attr(SPHINX_MAX_RESULTS=5)
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetLimits').with_args(0, 5)
                  .expects('RunQueries').returns(no_results))

    # SPHINX_MAX_RESULTS only comes into play if there's no
    # stop in the slice.
    s = S(Biscuit)[0:]
    # Do this to trigger the results.
    s.count()
