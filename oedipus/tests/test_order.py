import fudge
from nose.tools import eq_
import sphinxapi

from oedipus import S
from oedipus.tests import no_results, Biscuit, BaseSphinxMeta


class BiscuitOrderDefault(object):
    """An arbitrary adaptation key that S can map to a SearchModel"""

    class SphinxMeta(BaseSphinxMeta):
        ordering = 'a'


class BiscuitOrderDefaultList(object):
    """An arbitrary adaptation key that S can map to a SearchModel"""

    class SphinxMeta(BaseSphinxMeta):
        ordering = ['a', 'b']


def test_extended_sort_fields():
    """Make sure the expansion of the @rank pseudo-field works."""
    esf = S._extended_sort_fields
    eq_(esf(['fred', '-george', '-@rank']),
        'fred ASC, george DESC, @weight DESC, @id ASC')
    # No reason to flip the ID sorting when sorting by ASC rank:
    eq_(esf(['@rank']), '@weight ASC, @id ASC')


@fudge.patch('sphinxapi.SphinxClient')
def test_order_by_fields(sphinx_client):
    """Test ordering by only field values."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetSortMode')
                  .with_args(sphinxapi.SPH_SORT_EXTENDED, 'a ASC, b DESC')
                  .expects('RunQueries').returns(no_results))
    S(Biscuit).order_by('a', '-b')._raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_order_by_rank_explicitly(sphinx_client):
    """Test mixing the @rank pseudo-field into the ``order_by()``."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetSortMode')
                  .with_args(sphinxapi.SPH_SORT_EXTENDED,
                             'a ASC, @weight DESC, @id ASC')
                  .expects('RunQueries').returns(no_results))
    S(Biscuit).order_by('a', '-@rank')._raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_order_by_default(sphinx_client):
    """Assert that results order by rank by default."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetSortMode')
                  .with_args(sphinxapi.SPH_SORT_EXTENDED,
                             '@weight DESC, @id ASC')
                  .expects('RunQueries').returns(no_results))
    S(Biscuit)._raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_order_by_ordering_single(sphinx_client):
    """Test ``ordering`` attribute with a single value."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetSortMode')
                  .with_args(sphinxapi.SPH_SORT_EXTENDED,
                             'a ASC')
                  .expects('RunQueries').returns(no_results))
    S(BiscuitOrderDefault)._raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_order_by_ordering_list(sphinx_client):
    """Test ``ordering`` attribute with list of values."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetSortMode')
                  .with_args(sphinxapi.SPH_SORT_EXTENDED,
                             'a ASC, b ASC')
                  .expects('RunQueries').returns(no_results))
    S(BiscuitOrderDefaultList)._raw()
