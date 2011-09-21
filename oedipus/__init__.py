import collections
import logging
import re
import socket

try:
    # Use Django settings if they're around:
    from django.conf import settings
    # But Django can be around without the settings actually working, if the
    # DJANGO_SETTINGS_MODULE isn't set.
    getattr(settings, 'smoo', None)
except ImportError:
    # Otherwise, come up with some defaults:
    class settings(object):
        SPHINX_HOST = '127.0.0.1'
        SPHINX_PORT = 3381

import sphinxapi

from oedipus.results import DictResults, TupleResults, ObjectResults


# 64-bit signed min and max, which are the bounds of Sphinx's range filters:
MIN_LONG = -9223372036854775808
MAX_LONG =  9223372036854775807


# min/max weights allow us to have a set of weight values that we can
# translate to sphinx and elasticutils which both use different ranges
# for weight values.
#
# FIXME - These are based on sphinx weight values used in kitsune.  If
# we want to change it, we can do that.  If there are other consumers,
# we can add an interface for the application to set the desired
# range, too.
MIN_WEIGHT = 1
MAX_WEIGHT = 10


log = logging.getLogger('oedipus')


class SearchError(Exception):
    pass


class S(object):
    """A lazy query of Sphinx whose API is a subset of elasticutils.S"""
    def __init__(self, model, host=settings.SPHINX_HOST,
                              port=settings.SPHINX_PORT):
        self.type = model
        self.steps = []
        self.meta = model.SphinxMeta
        self.host = host
        self.port = port
        # Fields included in tuple and dict-formatted results:
        self._fields = ()
        self._results_class = ObjectResults
        self._start, self._stop = None, None
        self._results_cache = None

    def _clone(self, next_step=None):
        new = self.__class__(self.type)
        new.steps = list(self.steps)
        if next_step:
            new.steps.append(next_step)
        new.meta = self.meta
        new.host = self.host
        new.port = self.port
        new._results_class = self._results_class
        new._fields = self._fields
        return new

    def query(self, text, **kwargs):
        """Use the value of the ``any_`` kwarg as the query string.

        ElasticSearch supports restricting the search to individual fields, but
        Sphinx just takes a string and searches all fields. To present an
        elasticutils-compatible API, we take only the ``any_``  kwarg's value
        and use it as the query string, ignoring any other kwargs.

        """
        return self._clone(next_step=('query', text))

    def weight(self, **kwargs):
        """Set the weighting of matches per field.

        Weights given here are added to any defaults or any previously
        specified weights, though later references to the same field
        override earlier ones.

        Weights range from ``MIN_WEIGHT`` to ``MAX_WEIGHT``.

        Note: If we need to clear weights, add a ``clear_weights()``
        method.

        Note: If we ever need index boosting, ``weight_indices()``
        might be nice.

        """
        _check_weights(kwargs)
        return self._clone(next_step=('weight', kwargs))

    def filter(self, **kwargs):
        """Restrict the query to results matching the given conditions.

        This filter is ANDed with any previously requested ones.

        If you pass something mutable as the value for any kwarg, please don't
        mutate it later. The values are internalized by ``S`` objects (and
        shared with their clones), and ``S`` objects are supposed to be
        immutable.

        """
        return self._clone(next_step=('filter', _lookup_triples(kwargs)))

    def exclude(self, **kwargs):
        """Restrict the query to exclude results that match the given condition.

        Typically takes only a single kwarg, because Sphinx can't OR filters
        together (or, equivalently, exclude only documents which match all of
        several criteria). Taking multiple arbitrary kwargs would imply that it
        could, assuming parallel semantics with the Django ORM's ``exclude()``.

        However, closed range filters can have 2 kwargs: a ``__lte`` and a
        ``__gte`` about the same field. These mix down to a single call to
        SetFilterRange filter.

        Feel free to call ``exclude()`` more than once. Each exclusion is ANDed
        with any previously applied ones.

        If you pass something mutable as the value for any kwarg, please don't
        mutate it later. The values are internalized by ``S`` objects (and
        shared with their clones), and ``S`` objects are supposed to be
        immutable.

        """
        items = _lookup_triples(kwargs)
        if len(items) == 1:
            return self._clone(next_step=('exclude', items))
        if len(items) == 2:
            # Make sure they're a gte/lte pair on the same field:
            (field1, cmp1, val1), (field2, cmp2, val2) = items
            if field1 == field2:
                cmps = {cmp1: val1, cmp2: val2}
                if 'lte' in cmps and 'gte' in cmps:
                    return self._clone(next_step=('exclude', items))
        raise TypeError('exclude() takes exactly 1 keyword argument or a '
                        'pair of __lte/__gte arguments referencing the same '
                        'field.')

    # TODO: Turn these into values() and values_list(), like Django.
    def values_dict(self, *fields):
        """Return a new S whose results will be returned as dictionaries."""
        return self._clone(next_step=('values_dict', fields))

    def order_by(self, *fields):
        """Returns a new S with the field ordering changed.

        ``order_by()`` takes these types of arguments:

        * some_field (sort ascending)
        * -some_field (sort descending)
        * @rank (sort by rank ascending)
        * -@rank (sort by rank descending--usually what you want)

        """
        return self._clone(next_step=('order_by', fields))

    def values(self, *fields):
        """Return a new ``S`` whose results are returned as a list of tuples.

        Each tuple has an element for each field named in ``fields``.

        """
        if not fields:
            raise TypeError('values() must be given a list of field names.')
        return self._clone(next_step=('values', fields))

    def count(self):
        """Return the number of hits for the current query.

        Can't avoid hitting the DB if we want accuracy, since Sphinx may
        contain documents that have since been deleted from the DB.

        """
        return len(self._results())

    __len__ = count

    def __iter__(self):
        return iter(self._results())

    @staticmethod
    def _extended_sort_fields(fields):
        """Return the field expressions to sort by the given pseudo-fields in SPH_SORT_EXTENDED mode.

        If ``fields`` is empty, return ''. See also ``order_by()``.

        """
        def rank_expanded(fields):
            """Return fields, replacing @rank with @weight/@id pairs."""
            for f in fields:
                if f == '@rank':
                    yield '@weight'
                    yield '@id'
                elif f == '-@rank':
                    yield '-@weight'
                    yield '@id'
                else:
                    yield f

        return ', '.join((f[1:] + ' DESC') if f.startswith('-') else
                         (f + ' ASC')
                         for f in rank_expanded(fields))

    @staticmethod
    def _consolidate_ranges(triples):
        """In a list of (field, comparand, value) triples, merge any lte/gte triples on the same field into a single ``RANGE`` triple.

        Return a comprehensive iterable of triples.

        """
        inequalities = ['gte', 'lte']
        d = {}  # {'color': {'gte': 0. 'lte': 10}}
        for field, cmp, value in triples:
            if cmp in inequalities:
                d.setdefault(field, {})[cmp] = value
            else:
                yield field, cmp, value

        for field, cmp_vals in d.iteritems():
            if len(cmp_vals) == 2:
                yield field, 'RANGE', (cmp_vals['gte'], cmp_vals['lte'])
            else:  # There's only 1 comparator in there.
                yield field, cmp_vals.keys()[0], cmp_vals.values()[0]

    def _set_filters(self, sphinx, keys_and_values, exclude=False):
        """Set a series of filters on a SphinxClient according to some Django ORM-lookup-style key/value pairs."""
        ranges = self._consolidate_ranges(keys_and_values)
        for field, comparator, value in ranges:
            value = self._apply_filter_mappings(field, value)
            if not comparator:
                sphinx.SetFilter(field, [value], exclude)
            elif comparator == 'in':
                sphinx.SetFilter(field, value, exclude)
            elif comparator == 'gte':
                sphinx.SetFilterRange(field, value, MAX_LONG, exclude)
            elif comparator == 'lte':
                sphinx.SetFilterRange(field, MIN_LONG, value, exclude)
            elif comparator == 'RANGE':
                # exclude() range with both min and max given:
                sphinx.SetFilterRange(field, value[0], value[1], exclude)
            else:
                raise ValueError('"%s", in "%s__%s=%s", is not a supported '
                                 'comparator.' %
                                 (comparator, field, comparator, value))

    def _apply_filter_mappings(self, name, value):
        """Apply filter mappings to convert values to int."""
        mappings = getattr(self.meta, 'filter_mapping', {})
        converter = mappings.get(name, None)
        if converter:
            if (isinstance(value, collections.Iterable) and
                not isinstance(value, basestring)):
                return map(converter, value)
            return converter(value)
        return value

    @staticmethod
    def _sanitize_query(query):
        """Strip control characters that cause problems."""
        query = re.sub(r'(?<=\S)\-', '\-', query)
        return query.replace('^', '').replace('$', '')

    def _sphinx(self):
        """Parametrize a SphinxClient to execute the query I represent, run it, and return it.

        Doesn't support batched queries yet.

        """
        # TODO: Refactor so we can do multiple searches without reopening the
        # connection to Sphinx.
        sphinx = sphinxapi.SphinxClient()
        sphinx.SetServer(self.host, self.port)
        sphinx.SetMatchMode(sphinxapi.SPH_MATCH_EXTENDED2)
        sphinx.SetRankingMode(sphinxapi.SPH_RANK_PROXIMITY_BM25)

        # Loop over `self.steps` to build the query format that will be sent to
        # ElasticSearch, and returns it as a dict.
        query = sort = ''
        try:
            weights = dict(self.meta.weights)
        except AttributeError:
            weights = {}
        # TODO: Something that calls SetGroupBy, perhaps
        for action, value in self.steps:
            if action == 'order_by':
                sort = self._extended_sort_fields(value)
            elif action == 'values':
                self._fields = value
                self._results_class = TupleResults
            elif action == 'values_dict':
                self._fields = value
                self._results_class = DictResults
            elif action == 'query':
                query = self._sanitize_query(value)
            elif action == 'filter':
                self._set_filters(sphinx, value)
            elif action == 'weight':
                weights.update(value)
            elif action == 'exclude':
                self._set_filters(sphinx, value, exclude=True)
            else:
                raise NotImplementedError(action)

        if not sort:
            sort = self._extended_sort_fields(
                    (_listify(getattr(self.meta, 'ordering', [])) or
                     self._default_sort()))

        # EXTENDED is a superset of all the modes we care about, so we just use
        # it all the time:
        sphinx.SetSortMode(sphinxapi.SPH_SORT_EXTENDED, sort)

        # Add query. This must be done after filters and such are set up, or
        # they may not apply.
        sphinx.AddQuery(query, self.meta.index)

        # set the final set of weights here
        if weights:
            # weights are name -> field_weight where the field_weights
            # are essentially ok for Sphinx, so we just pass them
            # through.
            sphinx.SetFieldWeights(weights)

# Old ES stuff:
#         qs = {}
#
#         if self.start:
#             qs['from'] = self.start
#         if self.stop is not None:
#             qs['size'] = self.stop - self.start
#
#         return qs
        return sphinx

    def _results(self):
        """Return an iterable of results in whatever format was picked.

        The format is determined by earlier calls to values() or values_dict().
        The result supports len() as well.

        """
        raw = self._raw()  # side effect: sets _results_class and _fields
        return self._results_class(self.type, raw, self._fields)

    def _default_sort(self):
        """Return the ordering to use if the SphinxMeta doesn't specify one."""
        return ['-@rank']

    def _raw(self):
        """Return the raw matches from the first (and only) query.

        If anything goes wrong, raise SearchError. Cache the results. Calling
        this after a SearchError will retry.

        """
        if self._results_cache is None:
            sphinx = self._sphinx()
            try:
                self._results_cache = results = sphinx.RunQueries()
            except socket.timeout:
                log.error('Query has timed out!')
                raise SearchError('Query has timed out!')
            except socket.error, msg:
                log.error('Query socket error: %s', msg)
                raise SearchError('Could not execute your search!')
            except Exception, e:
                log.error('Sphinx threw an unknown exception: %s', e)
                raise SearchError('Sphinx threw an unknown exception!')

            if not results:
                raise SearchError('Sphinx returned no results.')
            if results[0]['status'] == sphinxapi.SEARCHD_ERROR:
                raise SearchError('Sphinx had an error while performing a '
                                  'query.')

        # We do only one query at a time; return the first one:
        return self._results_cache[0]


try:
    import elasticutils
except ImportError:
    pass
else:
    class SphinxTolerantElastic(elasticutils.S):
        """Shim around elasticutils' S which ignores Sphinx-specific hacks

        Use this when you're using ElasticSearch if your project is flipping
        quickly between ElasticSearch and Sphinx.

        """
        def query(self, text, **kwargs):
            """Ignore any non-kw arg."""
            # TODO: If you're feeling fancy, turn the `text` arg into an "or" query
            # across all fields, or use the all_ index, or something.
            super(SphinxTolerantElastic, self).query(**kwargs)


def _lookup_triples(dic):
    """Turn a kwargs dictionary into a triple of (field, comparator, value)."""
    def _split(key):
        """Split a key like ``foo__gte`` into ``('foo', 'gte')``.

        Simple ``foo`` becomes ``('foo', '')``.

        """
        parts = key.rsplit('__', 1)
        if len(parts) == 1:
            parts.append('')
        return parts
    return [_split(key) + [value] for key, value in dic.items()]



def _check_weights(weights):
    """Verifies weight values are in the appropriate range.

    :param weights: name -> field_weight dict

    :raises ValueError: if a weight is not in the range
    """
    for key, value in weights.items():
        if not (MIN_WEIGHT <= value <= MAX_WEIGHT):
            raise ValueError('"%d" for field "%s" is outside of range of '
                             '%d to %d' %
                             (value, key, MIN_WEIGHT, MAX_WEIGHT))


def _listify(maybe_list):
    if isinstance(maybe_list, (list, tuple)):
        return maybe_list
    return [maybe_list]
