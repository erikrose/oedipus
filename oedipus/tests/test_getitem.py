"""Tests for queries, filters, and excludes"""

import fudge
from nose.tools import eq_, assert_raises

from oedipus import S
from oedipus.tests import (no_results, Biscuit, SphinxMockingTestCase,
                           BigSphinxMockingTestCase)
from oedipus.utils import mix_slices


# A single Sphinx search result--just the "red" object:
red_results = [{'status': 0,
                'total': 1,
                'matches':
                     [{'attrs': {},
                       'id': 123,
                       'weight': 11111}]}]
blue_results = [{'status': 0,
                 'total': 1,
                 'matches':
                      [{'attrs': {},
                        'id': 124,
                        'weight': 11111}]}]


def _test_mixing(j, k):
    """Assert that ``[0..20][mix_slices(j, k)] == [0..20][j][k]``."""
    seq = range(10)
    eq_(seq[mix_slices(j, k)], seq[j][k])


def _test_mixing_slices(a, b, c, d):
    """Make things a little easier to read.

    It's hard to read around repeated calls to slices():

    """
    _test_mixing(slice(a, b), slice(c, d))


def test_mix_slice_and_int():
    """Test mixing slices and simple int indices."""
    _test_mixing(slice(1, 8), 3)
    _test_mixing(slice(3, 6), 2)

    # Index reaching beyond sequence:
    eq_(mix_slices(slice(2, 5), 7), 2 + 7)


def test_mix_slices():
    """Assert mixing various pairs of slices works."""
    _test_mixing_slices(1, 7, 2, 6)
    _test_mixing_slices(4, 10, 2, 6)

    _test_mixing_slices(None, 5, 2, 3)
    _test_mixing_slices(None, 5, None, 3)

    # j.stop is None:
    _test_mixing_slices(3, None, None, 3)

    # j.stop > k.stop + j.start:
    _test_mixing_slices(0, 9, None, 3)

    # j.stop < k.stop + j.start:
    _test_mixing_slices(0, 2, None, 3)

    # Non-overlapping slices. Also, k.stop is None:
    _test_mixing_slices(None, 5, 7, None)

    # None party!
    _test_mixing_slices(None, None, None, None)


def test_mix_nonslice_error():
    """Assert ``TypeError`` is raised when first arg isn't a slice."""
    assert_raises(TypeError, mix_slices, 5, 6)


@fudge.patch('sphinxapi.SphinxClient')
def test_slice(sphinx_client):
    """Slicing shouldn't cause any calls to Sphinx."""
    S(Biscuit)[:9]


@fudge.patch('sphinxapi.SphinxClient')
def test_slice_twice(sphinx_client):
    """Slicing multiple times shouldn't even cause any calls to Sphinx."""
    S(Biscuit)[:9][2:]


class ConcreteSlicingTestCase(SphinxMockingTestCase):
    """Tests for slices that ultimately resolve to results.

    Because they do, we need to have some mock models instantiated in
    ``setUp()``.

    """
    @fudge.patch('sphinxapi.SphinxClient')
    def test_index(self, sphinx_client):
        """Getting an indexed item should set limits and hit Sphinx."""
        (sphinx_client.expects_call().returns_fake()
                      .is_a_stub()
                      .expects('SetLimits').with_args(3, 1)
                      .expects('RunQueries').returns(red_results))
        eq_(S(Biscuit)[3].color, 'red')

    @fudge.patch('sphinxapi.SphinxClient')
    def test_index_doesnt_ruin_s(self, sphinx_client):
        """Make sure asking for a single item doesn't wreck future attempts to take other slices of an ``S``."""
        (sphinx_client.expects_call().returns_fake()
                      .is_a_stub()
                      .remember_order()
                      .expects('SetLimits').with_args(4, 1)
                      .expects('RunQueries').returns(red_results)
                      .expects('SetLimits').with_args(5, 1)
                      .expects('RunQueries').returns(blue_results))
        s = S(Biscuit)
        s[4]
        s[5]

class IntegratedSlicesTestCase(BigSphinxMockingTestCase):
    @fudge.patch('sphinxapi.SphinxClient')
    def test_slice_after_len(self, sphinx_client):
        """Make sure you can slice after len and that it hits Sphinx
        only once.

        """
        self.mock_sphinx(sphinx_client)

        test_s = S(Biscuit)

        # This triggers the one-and-only Sphinx hit.  We should have a
        # set of results now that we use for the rest of the test
        # case.
        num_results = len(test_s)
        eq_(num_results, 7)

        # Test that we can slice the results without triggering a
        # Sphinx hit.
        results = list(test_s[3:5])
        eq_(len(results), 2)
        eq_(results[0].id, 103)
        eq_(results[1].id, 104)

        # Test that we can slice the results again and that it doesn't
        # trigger another Sphinx hit and also that the previous slice
        # doesn't affect these results.
        results = list(test_s[1:2])
        eq_(len(results), 1)
        eq_(results[0].id, 101)

        # Also, this shouldn't affect the original results.
        num_results = len(test_s)
        eq_(num_results, 7)


@fudge.patch('sphinxapi.SphinxClient')
def test_slice_limit_setting(sphinx_client):
    """Assert limits are set correctly when slicing."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetLimits').with_args(7, 5)
                  .expects('RunQueries').returns(no_results))
    s = S(Biscuit)[5:20][2:7]
    list(s)  # Iterate to concretize.


@fudge.patch('sphinxapi.SphinxClient')
def test_slice_caching(sphinx_client):
    """Slicing shouldn't re-query if the results have already been fetched."""
    (sphinx_client.expects_call().returns_fake()
                  .is_a_stub()
                  .expects('SetLimits').times_called(1)
                  .expects('RunQueries').returns(no_results).times_called(1))
    # All these slice bounds are arbitrary:
    s = S(Biscuit)[2:20]
    list(s)  # Force it to do the query.
    list(s[:4])  # Reslice and iterate, tempting it to re-query.
