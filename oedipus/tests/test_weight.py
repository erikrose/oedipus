import fudge

from oedipus import S
from oedipus.tests import no_results, Biscuit, BaseSphinxMeta


class BiscuitWithWeight(object):
    """Biscuit with default weights"""

    class SphinxMeta(BaseSphinxMeta):
        weights = {'a': 5, 'b': 5}


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
