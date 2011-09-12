=======
oedipus
=======

oedipus is a friendlier API for the Sphinx search server. It presents a similar
API to elasticutils, giving you the option of switching back and forth between
Sphinx and elasticsearch at the flip of a switch, as long as you stick to the
common subset of functionality.

Requirements
============

* Not Django. oedipus has a few handy affordances for it but doesn't need it.
* sphinxapi.py, the Python module from the Sphinx source code distribution
* elasticutils

Limitations Compared to elasticutils
====================================

Because Sphinx itself is less flexible than ElasticSearch, oedipus can't offer
all the features of elasticutils' full API.

query() is Less Controllable
----------------------------

Sphinx takes just a query string and bangs it against all indexed fields.
ElasticSearch, on the other hand, lets you specify which fields to match
against per call. This makes the use of ``query()`` between the two necessarily
inconsistent:

* oedipus' ``query()`` takes a single keyword arg, ``any_``, which matches
  against all fields, Sphinx-style::

  S(Animal).query(any_='gerbil')

* elasticutils' ``query()`` takes an arbitrary number of keyword args, one per
  field to match against::

  S(Animal).query(title='gerbil')

Thus, if you want to maintain the ability to switch quickly between Sphinx and
ElasticSearch, simply combine the two::

  S(Animal).query(any_='gerbil', title='gerbil')

No Or-ing of Filters
--------------------

There's no way to "or" filters together in Sphinx, so oedipus does not support
elasticutils' ``F`` objects.

No ``gt`` or ``lt``
-------------------

oedipus supports ``gte`` and ``lte`` lookups but not ``gt`` or ``lt``, just
because that's what Sphinx directly supports. Add it for integers if it bothers
you. Floats (SetFilterFloatRange) are trickier.


Running the Tests
=================

Do something like this::

    DJANGO_SETTINGS_MODULE=kitsune.settings PYTHONPATH=/Users/erose/Checkouts/kitsune/vendor/src/elasticutils:/Users/erose/Checkouts/:/Users/erose/Checkouts/kitsune/vendor/packages/logilab-common:/Users/erose/Checkouts/kitsune/vendor/src/sphinxapi:. nosetests

Beware that if you run the support.mozilla.com tests, they will clear out your
Sphinx indices. Don't be surprised.

Future Plans
============

* Support for the rest of the Sphinx API would be nice: SetGroupDistinct,
  SetFilterFloatRange, SetIDRange, and everything else at
  http://sphinxsearch.com/docs/manual-0.9.9.html. I don't plan to add it,
  because I don't need it, but patches are welcome.
* Decouple the SphinxMeta classes from the models. We should have a nice way of
  assigning Sphinx metadata to third-party models that we can't just scribble
  on. Then we won't need to depend on Django.
* Think about mapping ``any_`` queries to ElasticSearch ``_all`` queries. We
  might need to add some support to elasticutils first.
* Make sure we always throw nice errors when someone tries to do
  elasticutils-ish things not supported by Sphinx, like passing ``F`` objects
  to ``filter()``.