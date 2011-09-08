=======
oedipus
=======

oedipus is a friendlier API for the Sphinx search server. It presents a similar
API to elasticutils, giving you the option of switching back and forth between
Sphinx and elasticsearch at the flip of a switch, as long as you stick to the
common subset of functionality.

Running the Tests
=================

Do something like this::

    DJANGO_SETTINGS_MODULE=kitsune.settings PYTHONPATH=/Users/erose/Checkouts/kitsune/vendor/src/elasticutils:/Users/erose/Checkouts/:/Users/erose/Checkouts/kitsune/vendor/src/django:/Users/erose/Checkouts/kitsune/apps/search:/Users/erose/Checkouts/kitsune/vendor/packages/logilab-common:/Users/erose/Checkouts/kitsune/lib:/Users/erose/Checkouts/kitsune/vendor/src/django-celery:. nosetests

Future Plans
============

Support for the rest of the Sphinx API would be nice: SetGroupDistinct,
SetFilterFloatRange, SetIDRange, and everything else at
http://sphinxsearch.com/docs/manual-0.9.9.html. I don't plan to add it, because
I don't need it, but patches are welcome.
