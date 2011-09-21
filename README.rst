=======
oedipus
=======

oedipus is a friendlier API for the Sphinx search server. It presents a similar
API to elasticutils, giving you the option of switching back and forth between
Sphinx and elasticsearch at the flip of a switch, as long as you stick to the
common subset of functionality.

Requirements
============

* Django, unless you're willing to implement some of the Django model API on
  your own model objects. There's no way to get useful non-integer information
  out of Sphinx on its own, so we use the passed-in model objects to query a
  secondary DB.
* sphinxapi.py, the Python module from the Sphinx source code distribution

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

* oedipus' ``query()`` takes a single argument, which matches against all
  fields, Sphinx-style::

    S(Animal).query('gerbil')

* elasticutils' ``query()`` takes an arbitrary number of keyword args, one per
  field to match against::

    S(Animal).query(title='gerbil')

Thus, if you want to maintain the ability to switch quickly between Sphinx and
ElasticSearch, simply combine the two::

  S(Animal).query('gerbil', title='gerbil')

No Or-ing of Filters
--------------------

There's no way to "or" filters together in Sphinx, so oedipus does not support
elasticutils' ``F`` objects.

No ``gt`` or ``lt``
-------------------

oedipus supports ``gte`` and ``lte`` lookups but not ``gt`` or ``lt``, just
because that's what Sphinx directly supports. Add it for integers if it bothers
you. Floats (``SetFilterFloatRange()``) are trickier.

``values()``
------------

If you call ``values()``, you must pass in a list of fields. In elasticutils,
this is optional.

Faceting
--------

There isn't any, because Sphinx doesn't support it.


Other Behavior Notes
====================

``order_by()`` calls pave over the effect of previous ``order_by()`` calls.
Ordering defaults to most-relevant-first.

Running the Tests
=================

1. Install the packages listed in requirements.txt using pip::

    pip install -r requirements.txt

2. Run the tests using nose::

    nosetests

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
* Think about mapping oedipus 1-arg queries to ElasticSearch ``_all`` queries.
  We might need to add some support to elasticutils first.
* Make sure we always throw nice errors when someone tries to do
  elasticutils-ish things not supported by Sphinx, like passing ``F`` objects
  to ``filter()``.
