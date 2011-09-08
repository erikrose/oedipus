import os

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


class SearchError(Exception):
    pass


class S(elasticutils.S):
    sort_mode = (sphinxapi.SPH_SORT_RELEVANCE, '')

    def __init__(self, model, host=settings.SPHINX_HOST,
                              port=settings.SPHINX_PORT):
        # TODO: Look up ModelSearch for the model based on mappings in
        # settings.py.
        super(S, self).__init__(model)
        self.host = host
        self.port = port

    def facet(self, *args, **kwargs):
        raise NotImplementedError("Sphinx doesn't support faceting.")

    def _sphinx(self):
        """Return a SphinxClient parametrized to execute the query I
        represent."""
        sphinx = sphinxapi.SphinxClient()
        sphinx.SetServer(self.host, self.port)
        sphinx.SetMatchMode(sphinxapi.SPH_MATCH_EXTENDED2)
        sphinx.SetRankingMode(sphinxapi.SPH_RANK_PROXIMITY_BM25)
        sphinx.SetSortMode(*self.sort_mode)  # TODO: Don't.

        # Loop over `self.steps` to build the query format that will be sent to
        # ElasticSearch, and returns it as a dict.
        filters = []
        queries = []
        sort = []
        fields = ['id']
        facets = {}
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
                # TODO
                queries.extend(self._process_queries(value))
            elif action == 'filter':
                # TODO
                filters.extend(_process_filters(value))  # where we process range filters (and more)
            elif action == 'facet':
                # TODO
                facets.update(value)
            else:
                raise NotImplementedError(action)
        
        if not queries:
            raise SearchError('Sphinx needs at least one call to query() before it can do a search.')

        qs = {}
        if len(filters) > 1:
            qs['filter'] = {'and': filters}
        elif filters:
            qs['filter'] = filters[0]

        if len(queries) > 1:
            qs['query'] = {'bool': {'must': queries}}
        elif queries:
            qs['query'] = queries[0]

        if fields:
            qs['fields'] = fields
        if facets:
            qs['facets'] = facets
            # Copy filters into facets. You probably wanted this.
            for facet in facets.values():
                if 'facet_filter' not in facet and filters:
                    facet['facet_filter'] = qs['filter']
        if sort:
            qs['sort'] = sort
        if self.start:
            qs['from'] = self.start
        if self.stop is not None:
            qs['size'] = self.stop - self.start

        self.fields, self.as_list, self.as_dict = fields, as_list, as_dict
        return qs
        
        # TODO: Call _sanitize_query().

    def raw(self):
        sphinx = self._sphinx()
        try:
            result = self.sphinx.Query(query, self.index)
        except socket.timeout:
            log.error('Query has timed out!')
            raise SearchError('Query has timed out!')
        except socket.error, msg:
            log.error('Query socket error: %s' % msg)
            raise SearchError('Could not execute your search!')
        except Exception, e:
            log.error('Sphinx threw an unknown exception: %s' % e)
            raise SearchError('Sphinx threw an unknown exception!')

        # TODO: Maybe return something else:
        if result:
            return result['matches']
        else:
            return []
