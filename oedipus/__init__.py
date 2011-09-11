import logging
import os
import re
import socket

try:
    # Use Django settings if they're around:
    from django.conf import settings
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
#     #: Say '@relevance' to sort by relevance. Can be a tuple or list to sort by
#     #: one or more attributes. SPH_SORT_TIME_SEGMENTS and SPH_SORT_EXPR are
#     #: not supported.
#     ordering = '@relevance'


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

    def query(self, **kwargs):
        """Use the value of the ``any_`` kwarg as the query string.

        ElasticSearch supports restricting the search to individual fields, but
        Sphinx just takes a string and searches all fields. To present an
        elasticutils-compatible API, we take only the ``any_``  kwarg's value
        and use it as the query string, ignoring any other kwargs.

        """
        if 'any_' not in kwargs:
            raise TypeError('query() must have an `any_` kwarg.')
        return self._clone(next_step=('query', kwargs['any_']))

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
        return self._clone(next_step=('filter', kwargs.items()))

    def exclude(self, **kwargs):
        """Restrict the query to exclude results that match the given condition.

        Takes only a single kwarg, because Sphinx can't OR filters together
        (or, equivalently, exclude only documents which match all of several
        criteria).

        This exclusion is ANDed with any previously requested ones.

        """
        if len(kwargs) != 1:
            raise TypeError('exclude() takes exactly 1 keyword argument.')
        return self._clone(next_step=('exclude', kwargs.items()))

    def _sphinx(self):
        """Parametrize a SphinxClient to execute the query I represent, run it, and return it.

        Doesn't support batched queries yet.

        """
        sphinx = sphinxapi.SphinxClient()
        sphinx.SetServer(self.host, self.port)
        sphinx.SetMatchMode(sphinxapi.SPH_MATCH_EXTENDED2)
        sphinx.SetRankingMode(sphinxapi.SPH_RANK_PROXIMITY_BM25)

        # Loop over `self.steps` to build the query format that will be sent to
        # ElasticSearch, and returns it as a dict.
        filters = []
        query = ''
        sort = []
        fields = ['id']
        as_list = as_dict = False
        # Things to call: SetFilter, SetFilterRange, SetGroupBy
        for action, value in self.steps:
            if action == 'order_by':
                # TODO
                for key in value:
                    if key.startswith('-'):
                        sort.append({key[1:]: 'desc'})
                    else:
                        sort.append(key)
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
                query = _sanitize_query(value)
            elif action == 'filter':
                _set_filters(sphinx, value)
            elif action == 'exclude':
                # TODO
                pass
            else:
                raise NotImplementedError(action)

        if not sort:
            sort = getattr(self.meta, 'ordering', None) or self._default_sort()

        # Turn local state into parametrized SphinxClient:

        # TODO: Support other search modes.
        if type(sort) not in [list, tuple]:
            sort = [sort]
        if sort == ['@relevance']:
            sphinx.SetSortMode(sphinxapi.SPH_SORT_RELEVANCE, '')

        # Add query. This must be done after filters and such are set up, or
        # they may not apply.
        sphinx.AddQuery(query, self.meta.index)

# Old ES stuff:
#         qs = {}
#         if len(filters) > 1:
#             qs['filter'] = {'and': filters}
#         elif filters:
#             qs['filter'] = filters[0]
#
#         if len(queries) > 1:
#             qs['query'] = {'bool': {'must': queries}}
#         elif queries:
#             qs['query'] = queries[0]
#
#         if fields:
#             qs['fields'] = fields
#         if sort:
#             qs['sort'] = sort
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
        return '@relevance'

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
        except Exception, e:  # TODO: Don't catch SystemExit or KeyboardInterrupt.
            log.error('Sphinx threw an unknown exception: %s' % e)
            raise SearchError('Sphinx threw an unknown exception!')

        if not results:
            raise SearchError('Sphinx returned no results.')
        if results[0]['status'] == sphinxapi.SEARCHD_ERROR:
            raise SearchError('Sphinx had an error while performing a query.')

        # Perhaps more than just the matches would be useful to return someday.
        return results[0]['matches']


def _sanitize_query(query):
    """Strip control characters that cause problems."""
    query = re.sub(r'(?<=\S)\-', '\-', query)
    return query.replace('^', '').replace('$', '')


def _split(key):
    """Split a key like ``foo__gte`` into ``('foo', 'gte')``.

    Simple ``foo`` becomes ``('foo', '')``.

    """
    parts = key.rsplit('__', 1)
    if len(parts) == 1:
        parts.append('')
    return parts


def _set_filters(sphinx, keys_and_values):
    """Set a series of filters on a SphinxClient according to some Django ORM-lookup-style key/value pairs."""
    # TODO: This is pretty naive. Be smart: notice when you have both foo_gte
    # and foo_lte, and mix them down to a single call to SetFilterRange().
    for key, value in keys_and_values:
        field, comparator = _split(key)
        # Auto-listify ints for equality filters:
        if not comparator and type(value) in [int, long]:
            value = [value]

        if not comparator or comparator == 'in':
            sphinx.SetFilter(field, value)
        elif comparator == 'gte':
            sphinx.SetFilterRange(field, value, MAX_LONG)
        elif comparator == 'lte':
            sphinx.SetFilterRange(field, MIN_LONG, value)
        else:
            raise ValueError('"%s", in "%s__%s=%s", is not a supported comparator.' % (comparator, field, comparator, value))
