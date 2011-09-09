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


log = logging.getLogger('oedipus')


class SearchError(Exception):
    pass


# class SphinxDefaults(object):
#     #: Say '@relevance' to sort by relevance. Can be a tuple or list to sort by
#     #: one or more attributes. SPH_SORT_TIME_SEGMENTS and SPH_SORT_EXPR are
#     #: not supported.
#     ordering = '@relevance'


class S(elasticutils.S):
    """A lazy query of Sphinx, whose API is a subset of elasticutils.S"""
    def __init__(self, model, host=settings.SPHINX_HOST,
                              port=settings.SPHINX_PORT):
        super(S, self).__init__(model)
        self.meta = model.SphinxMeta
        self.host = host
        self.port = port

    def facet(self, *args, **kwargs):
        raise NotImplementedError("Sphinx doesn't support faceting.")

    def query(self, **kwargs):
        """Use the value of the only kwarg as the query string.

        ElasticSearch supports restricting the search to individual fields, but
        Sphinx just takes a string and makes the field decisions on the server.
        To present an elasticutils-compatible API, we take the only kwarg's
        value (no fair including more than one, because the results would be
        indeterminate) and use it as the query string. Better ideas welcome.

        """
        if len(kwargs) != 1:
            raise TypeError('query() takes exactly 1 keyword arg.')
        return self._clone(next_step=('query', kwargs[kwargs.keys()[0]]))

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
        # Things to call: SetFilter, SetFilterRange, Query, SetGroupBy
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
                # TODO
                filters.extend(_process_filters(value))  # where we process range filters (and more)
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
