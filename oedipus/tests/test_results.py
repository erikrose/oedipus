import collections
import fudge
from nose.tools import eq_, assert_raises

from oedipus import S
from oedipus.tests import Biscuit, SphinxMockingTestCase, BaseSphinxMeta
from oedipus.results import ObjectResults, DictResults, TupleResults


class ResultsTestCase(SphinxMockingTestCase):
    """Tests for various result formatters"""

    @fudge.patch('sphinxapi.SphinxClient')
    def test_objects(self, sphinx_client):
        """Test constructing and iterating over object-style results."""
        self.mock_sphinx(sphinx_client)

        results = list(S(Biscuit))  # S.__iter__ and DictResults.__iter__

        eq_(results[0].color, 'red')
        eq_(results[1].color, 'blue')

    @fudge.patch('sphinxapi.SphinxClient')
    def test_dicts_all_fields(self, sphinx_client):
        """Test constructing and iterating over dict-style results returning all model fields."""
        self.mock_sphinx(sphinx_client)
        results = list(S(Biscuit).values_dict())
        eq_(results, [{'color': 'red', 'id': 123},
                      {'color': 'blue', 'id': 124}])

    @fudge.patch('sphinxapi.SphinxClient')
    def test_dicts_without_id(self, sphinx_client):
        """Test dict-style results with explicit fields excluding ID."""
        self.mock_sphinx(sphinx_client)
        results = list(S(Biscuit).values_dict('color'))
        eq_(results, [{'color': 'red'},
                      {'color': 'blue'}])

    @fudge.patch('sphinxapi.SphinxClient')
    def test_dicts_overriding(self, sphinx_client):
        """Calls to ``values_dict()`` should override previous ones."""
        self.mock_sphinx(sphinx_client)
        results = list(S(Biscuit).values_dict('color').values_dict('id'))
        eq_(results, [{'id': 123},
                      {'id': 124}])

    @fudge.patch('sphinxapi.SphinxClient')
    def test_tuples(self, sphinx_client):
        """Test constructing and iterating over tuple-style results returning all model fields."""
        self.mock_sphinx(sphinx_client)
        results = list(S(Biscuit).values('id', 'color'))
        eq_(results, [(123, 'red'), (124, 'blue')])

    @fudge.patch('sphinxapi.SphinxClient')
    def test_tuples_without_id(self, sphinx_client):
        """Test tuple-style results that don't return ID."""
        self.mock_sphinx(sphinx_client)
        results = list(S(Biscuit).values('color'))
        eq_(results, [('red',), ('blue',)])

    @fudge.patch('sphinxapi.SphinxClient')
    def test_tuples_overriding(self, sphinx_client):
        """Calls to ``values()`` should override previous ones."""
        self.mock_sphinx(sphinx_client)
        results = list(S(Biscuit).values('color').values('id'))
        eq_(results, [(123,), (124,)])

    @fudge.patch('sphinxapi.SphinxClient')
    def test_tuples_no_fields(self, sphinx_client):
        """An empty values() call should raise ``TypeError``."""
        s = S(Biscuit)
        assert_raises(TypeError, s.values)

    @fudge.patch('sphinxapi.SphinxClient')
    def test_id_field(self, sphinx_client):
        """Assert that fetching results gets its object ID from the attr named by SphinxMeta.field_id, if present."""
        (sphinx_client.expects_call().returns_fake()
                      .is_a_stub()
                      .expects('RunQueries').returns(
                          [{'status': 0,
                            'total': 2,
                            'matches':
                                [{'attrs': {'thing_id': 123},
                                 'id': 3,
                                 'weight': 11111},
                                 {'attrs': {'thing_id': 124},
                                  'id': 4,
                                  'weight': 10000}]}]))

        class FunnyIdBiscuit(Biscuit):
            class SphinxMeta(BaseSphinxMeta):
                id_field = 'thing_id'

        results = list(S(FunnyIdBiscuit).values('color'))
        eq_(results, [('red',), ('blue',)])

    @fudge.patch('sphinxapi.SphinxClient')
    def test_object_ids(self, sphinx_client):
        """Test object_ids() method."""
        self.mock_sphinx(sphinx_client)

        results = S(Biscuit).object_ids()

        # Note: The results are dependent on mock_sphinx.  It should
        # return a list of ids.
        eq_(results, [123, 124])

    @fudge.patch('sphinxapi.SphinxClient')
    def test_object_ids_with_id_field(self, sphinx_client):
        """Test object_ids() method with field_id."""
        (sphinx_client.expects_call().returns_fake()
                      .is_a_stub()
                      .expects('RunQueries').returns(
                          [{'status': 0,
                            'total': 2,
                            'matches':
                                [{'attrs': {'thing_id': 123},
                                 'id': 3,
                                 'weight': 11111},
                                 {'attrs': {'thing_id': 124},
                                  'id': 4,
                                  'weight': 10000}]}]))

        class FunnyIdBiscuit(Biscuit):
            class SphinxMeta(BaseSphinxMeta):
                id_field = 'thing_id'

        results = S(FunnyIdBiscuit).values('color').object_ids()
        eq_(results, [123, 124])


def test_object_content_for_fields():
    TestResult = collections.namedtuple('TestResult', ['field1', 'field2'])
    content = ObjectResults.content_for_fields(
        TestResult('1', '2'),
        ['field1', 'field2'],
        ['field1', 'field2'])
    eq_(content, ('1', '2'))

    # Test the case where fields != highlight_fields.
    content = ObjectResults.content_for_fields(
        TestResult('4', '5'),
        ['field1', 'field2'],
        ['field1'])
    eq_(content, ('4',))


def test_tuple_content_for_fields():
    content = TupleResults.content_for_fields(
        ('1', '2'),
        ['field1', 'field2'],
        ['field1', 'field2'])
    eq_(content, ('1', '2'))

    # Test the case where fields != highlight_fields.
    content = TupleResults.content_for_fields(
        ('1', '2'),
        ['field1', 'field2'],
        ['field1'])
    eq_(content, ('1',))


def test_dict_content_for_fields():
    content = DictResults.content_for_fields(
        {'field1': '1', 'field2': '2'},
        ['field1', 'field2'],
        ['field1', 'field2'])
    eq_(content, ('1', '2'))

    # Test the case where fields != highlight_fields.
    content = DictResults.content_for_fields(
        {'field1': '1', 'field2': '2'},
        ['field1', 'field2'],
        ['field1'])
    eq_(content, ('1',))
