import logging
import os
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

import elasticutils
import sphinxapi


# 64-bit signed min and max, which are the bounds of Sphinx's range filters:
MIN_LONG = -9223372036854775808
MAX_LONG =  9223372036854775807


log = logging.getLogger('oedipus')


class SearchError(Exception):
    pass


# class SphinxDefaults(object):
#     #: Say '@rank' to sort by relevance. Can be a tuple or list to sort by
#     #: one or more attributes. SPH_SORT_TIME_SEGMENTS and SPH_SORT_EXPR are
#     #: not supported.
#     ordering = '@rank'


class S(elasticutils.S):
    """A lazy query of Sphinx whose API is a subset of elasticutils.S"""
    def __init__(self, model, host=settings.SPHINX_HOST,
                              port=settings.SPHINX_PORT):
        super(S, self).__init__(model)
        self.meta = model.SphinxMeta
        self.host = host
        self.port = port

    def facet(self, *args, **kwargs):
        raise NotImplementedError("Sphinx doesn't support faceting.")

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

        What should be the range of weights?

        Weights given here are added to any defaults or any previously
        specified weights, though later references to the same field override
        earlier ones. If we need to clear weights, add a ``clear_weights()``
        method.

        """
        # If we ever need index boosting, weight_indices() might be nice.
        raise NotImplementedError

    def filter(self, **kwargs):
        """Restrict the query to results matching the given conditions.

        This filter is ANDed with any previously requested ones.

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

    @staticmethod
    def _extended_sort_fields(fields):
        """Return the field expressions to sort by the given pseudo-fields in SPH_SORT_EXTENDED mode.

        order_by() understands these types of pseudo-fields:

            * some_field (sort ascending)
            * -some_field (sort descending)
            * @rank (sort by rank ascending)
            * -@rank (sort by rank descending--usually what you want)

        If ``fields`` is empty, return ''.

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

    @classmethod
    def _set_filters(cls, sphinx, keys_and_values, exclude=False):
        """Set a series of filters on a SphinxClient according to some Django ORM-lookup-style key/value pairs."""
        ranges = cls._consolidate_ranges(keys_and_values)
        for field, comparator, value in ranges:
            # Auto-listify ints for equality filters:
            if not comparator and type(value) in [int, long]:
                value = [value]

            if not comparator or comparator == 'in':
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
        filters = []
        query = sort = ''
        fields = ['id']
        as_list = as_dict = False
        # Things to call: SetGroupBy
        for action, value in self.steps:
            if action == 'order_by':
                sort = self._extended_sort_fields(value)
            elif action == 'values':
                # TODO
                fields.extend(value)
                as_list, as_dict = True, False
            elif action == 'values_dict':
                # TODO
                if not value:
                    fields = []
                else:
                    fields.extend(value)
                as_list, as_dict = False, True
            elif action == 'query':
                query = self._sanitize_query(value)
            elif action == 'filter':
                self._set_filters(sphinx, value)
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

# Old ES stuff:
#         qs = {}
#
#         if fields:
#             qs['fields'] = fields
#         if self.start:
#             qs['from'] = self.start
#         if self.stop is not None:
#             qs['size'] = self.stop - self.start
#
#         self.fields, self.as_list, self.as_dict = fields, as_list, as_dict
#         return qs
        return sphinx

    def _default_sort(self):
        """Return the ordering to use if the SphinxMeta doesn't specify one."""
        return ['-@rank']

    def raw(self):
        """Return the raw matches from the first (and only) query.

        If anything goes wrong, raise SearchError.

        """
        sphinx = self._sphinx()
        try:
            results = sphinx.RunQueries()
        except socket.timeout:
            log.error('Query has timed out!')
            raise SearchError('Query has timed out!')
        except socket.error, msg:
            log.error('Query socket error: %s' % msg)
            raise SearchError('Could not execute your search!')
        except Exception, e:
            log.error('Sphinx threw an unknown exception: %s' % e)
            raise SearchError('Sphinx threw an unknown exception!')

        if not results:
            raise SearchError('Sphinx returned no results.')
        if results[0]['status'] == sphinxapi.SEARCHD_ERROR:
            raise SearchError('Sphinx had an error while performing a query.')

        # Perhaps more than just the matches would be useful to return someday.
        return results[0]['matches']


class SphinxTolerantElastic(elasticutils.S):
    """Thin wrapper around elasticutils' S which ignores Sphinx-specific hacks

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


def _listify(maybe_list):
    if type(maybe_list) in [list, tuple]:
        return maybe_list
    return [maybe_list]
