import fudge

from oedipus import S
from oedipus.tests import no_results, Biscuit, BaseSphinxMeta

import sphinxapi


class BiscuitWithGroupBy(object):
    """Biscuit with default groupby"""

    class SphinxMeta(BaseSphinxMeta):
        group_by = ('a', '@group')


@fudge.patch('sphinxapi.SphinxClient')
def test_group_by(sphinx_client):
    """Test group by."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetGroupBy')
                  .with_args('a', sphinxapi.SPH_GROUPBY_ATTR, '@group DESC')
                  .expects('RunQueries')
                  .returns(no_results))
    S(Biscuit).group_by('a', '-@group')._raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_group_by_asc(sphinx_client):
    """Test group by ascending."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetGroupBy')
                  .with_args('a', sphinxapi.SPH_GROUPBY_ATTR, '@group ASC')
                  .expects('RunQueries')
                  .returns(no_results))
    S(Biscuit).group_by('a', '@group')._raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_group_by_override(sphinx_client):
    """Test group by override."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetGroupBy')
                  .with_args('a', sphinxapi.SPH_GROUPBY_ATTR, '@group ASC')
                  .expects('RunQueries')
                  .returns(no_results))
    # The second call overrides the first one.
    S(Biscuit).group_by('b', '-@group').group_by('a', '@group')._raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_group_by_multiple_bits(sphinx_client):
    """Test group by with multiple bits."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetGroupBy')
                  .with_args('a', sphinxapi.SPH_GROUPBY_ATTR, '@relevance DESC, age ASC')
                  .expects('RunQueries')
                  .returns(no_results))
    S(Biscuit).group_by('a', ('-@relevance', 'age'))._raw()


@fudge.patch('sphinxapi.SphinxClient')
def test_group_by_sphinxmeta(sphinx_client):
    """Test group by from SphinxMeta."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetGroupBy')
                  .with_args('a', sphinxapi.SPH_GROUPBY_ATTR, '@group ASC')
                  .expects('RunQueries')
                  .returns(no_results))
    S(BiscuitWithGroupBy)._raw()
