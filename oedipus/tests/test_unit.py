"""Unit-tests for little bits here and there"""

from nose.tools import eq_

from oedipus import S


def test_consolidate_ranges():
    """Assert that _consolidate_ranges() collapses lte/gte pairs."""
    input = [('category', 'gte', 1),
             ('category', 'lte', 10),
             ('category', '', 5),
             ('name', '', 'frank'),
             ('pog', 'gte', 0)]
    output = set([('category', 'RANGE', (1, 10)),
                  ('category', '', 5),
                  ('name', '', 'frank'),
                  ('pog', 'gte', 0)])
    eq_(set(S._consolidate_ranges(input)), output)
