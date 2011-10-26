from unittest import TestCase

import fudge

from nose.tools import eq_, assert_raises

from oedipus import S, ExcerptError
from oedipus.tests import no_results, Biscuit, BaseSphinxMeta, Manager
import oedipus.tests


class BiscuitTestCase(TestCase):
    def setUp(self):
        Biscuit(id=123, name='sesame', content='has sesame foo')
        Biscuit(id=124, name='dog', content='biscuit fit for a dog')
        Biscuit(id=125, name='cup', content='has sesame fa\xc3\xa7on foo')

    def tearDown(self):
        oedipus.tests.model_cache = []


class ExcerptBiscuitWithLimit(object):
    """A mocked-out Django model"""
    objects = Manager()

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    class SphinxMeta(BaseSphinxMeta):
        excerpt_limit = 5


@fudge.patch('sphinxapi.SphinxClient')
def test_highlight_chainable(sphinx_client):
    """Test highlight chainable sets options."""
    (sphinx_client.expects_call()
                  .returns_fake()
                  .is_a_stub()
                  .expects('RunQueries')
                  .returns(no_results))
    s = S(ExcerptBiscuitWithLimit).highlight('color',
                                             before_match='<i>',
                                             after_match='</i>')
    s._raw()

    # These three are set in the highlight() call.
    eq_(s._highlight_options,
        {'before_match': '<i>',
         'after_match': '</i>'})
    eq_(s._highlight_fields, ('color',))


@fudge.patch('sphinxapi.SphinxClient')
def test_highlight_overrides_previous(sphinx_client):
    """Test highlight chainable overrides previous highlight."""
    (sphinx_client.expects_call()
                  .returns_fake()
                  .is_a_stub()
                  .expects('RunQueries')
                  .returns(no_results))
    s = (S(ExcerptBiscuitWithLimit).highlight('color',
                                              before_match='<i>',
                                              after_match='</i>',
                                              limit=100)
                                   .highlight('name',
                                              before_match='<b>',
                                              after_match='</b>'))

    s._raw()

    # These three are set in the highlight() call.
    eq_(s._highlight_options,
        {'before_match': '<b>',
         'after_match': '</b>',
         'limit': 100})
    eq_(s._highlight_fields, ('name',))


@fudge.patch('sphinxapi.SphinxClient')
def test_highlight_chainable_no_sphinx_meta_limit(sphinx_client):
    """Test highlight chainable sets options."""
    (sphinx_client.expects_call()
                  .returns_fake()
                  .is_a_stub()
                  .expects('RunQueries')
                  .returns(no_results))
    s = S(Biscuit).highlight('color',
                             before_match='<i>',
                             after_match='</i>')
    s._raw()

    # There should be no limit defined.
    assert 'limit' not in s._highlight_options


class TestHighlight(BiscuitTestCase):
    @fudge.patch('sphinxapi.SphinxClient')
    def test_highlight_not_subset_of_fields(self, sphinx_client):
        """Test excerpt with some fields highlighted."""
        (sphinx_client.expects_call()
                      .returns_fake()
                      .is_a_stub()
                      .expects('RunQueries')
                      .returns(
                          [{'status': 0,
                            'total': 2,
                            'matches':
                              [{'attrs': {'name': 3, 'content': 4},
                                'id': 123, 'weight': 11111}]
                          }]))

        s = (S(Biscuit).query('foo')
                       .highlight('content',
                                  before_match='<i>',
                                  after_match='</i>'))

        results = list(s)
        assert_raises(ExcerptError, lambda: s.excerpt(results[0]))


class TestExcerpt(BiscuitTestCase):
    @fudge.patch('sphinxapi.SphinxClient')
    def test_excerpt(self, sphinx_client):
        """Test excerpt with all fields highlighted."""
        (sphinx_client.expects_call()
                      .returns_fake()
                      .is_a_stub()
                      .expects('BuildExcerpts')
                      .with_args(['sesame', 'has sesame foo'],
                                 'biscuit',
                                 'foo',
                                 {'before_match': '<i>',
                                  'after_match': '</i>'})
                      .returns(
                          [('sesame', 'has sesame <i>foo</i>')])
                      .expects('RunQueries')
                      .returns(
                          [{'status': 0,
                            'total': 2,
                            'matches':
                              [{'attrs': {'name': 3, 'content': 4},
                                'id': 123, 'weight': 11111}]
                          }]))

        s = (S(Biscuit).query('foo')
                       .highlight('name', 'content',
                                  before_match='<i>',
                                  after_match='</i>')
                       .values('name', 'content'))

        results = list(s)
        s.excerpt(results[0])

    @fudge.patch('sphinxapi.SphinxClient')
    def test_excerpt_with_unicode(self, sphinx_client):
        """Test excerpt with all fields highlighted."""
        (sphinx_client.expects_call()
                      .returns_fake()
                      .is_a_stub()
                      .expects('BuildExcerpts')
                      .with_args(['has sesame fa\xc3\xa7on foo'],
                                 'biscuit',
                                 'foo',
                                 {'before_match': '<i>',
                                  'after_match': '</i>'})
                      .returns(
                          [('has sesame fa\xc3\xa7on <i>foo</i>',)])
                      .expects('RunQueries')
                      .returns(
                          [{'status': 0,
                            'total': 2,
                            'matches':
                              [{'attrs': {'name': 3, 'content': 4},
                                'id': 125, 'weight': 11111}]
                          }]))

        s = (S(Biscuit).query('foo')
                       .highlight('content',
                                  before_match='<i>',
                                  after_match='</i>')
                       .values('content'))

        results = list(s)
        eq_(s.excerpt(results[0])[0], u'has sesame fa\xe7on <i>foo</i>')

    @fudge.patch('sphinxapi.SphinxClient')
    def test_naughty_excerpt_throws_error(self, sphinx_client):
        """Test using results from one S in another S.excerpt()."""
        (sphinx_client.expects_call()
                      .returns_fake()
                      .is_a_stub()
                      .expects('RunQueries')
                      .returns(
                          [{'status': 0,
                            'total': 2,
                            'matches':
                              [{'attrs': {'name': 3, 'content': 4},
                                'id': 123, 'weight': 11111}]
                          }]))

        s = (S(Biscuit).query('foo')
                       .highlight('name', 'content',
                                  before_match='<i>',
                                  after_match='</i>'))

        results = list(s)

        s2 = (S(Biscuit).highlight('name', 'content',
                                   before_match='<i>',
                                   after_match='</i>'))

        assert_raises(ExcerptError, lambda: s2.excerpt(results[0]))

    @fudge.patch('sphinxapi.SphinxClient')
    def test_excerpt_limit_fields(self, sphinx_client):
        """Test excerpt with some fields highlighted."""
        (sphinx_client.expects_call()
                      .returns_fake()
                      .is_a_stub()
                      .expects('BuildExcerpts')
                      .with_args(['has sesame foo'],
                                 'biscuit',
                                 'foo',
                                 {'before_match': '<i>',
                                  'after_match': '</i>'})
                      .returns(
                          [('has sesame <i>foo</i>',)])
                      .expects('RunQueries')
                      .returns(
                          [{'status': 0,
                            'total': 2,
                            'matches':
                              [{'attrs': {'name': 3, 'content': 4},
                                'id': 123, 'weight': 11111}]
                          }]))

        s = (S(Biscuit).query('foo')
                       .highlight('content',
                                  before_match='<i>',
                                  after_match='</i>')
                       .values('content'))

        results = list(s)
        s.excerpt(results[0])
