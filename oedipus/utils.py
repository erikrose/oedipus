def lookup_triples(dic):
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


def listify(maybe_list):
    if isinstance(maybe_list, (list, tuple)):
        return maybe_list
    return [maybe_list]


def mix_slices(j, k):
    """Merge two slices into one such that ``X[mix_slices(j, k)] == X[j][k]``.

    :arg j: A slice
    :arg k: A second slice or an int. If an int, return an int. If a slice,
        return a slice.

    Negative starts, stops, or indexes are unsupported. Non-1 steps are
    unsupported so far.

    This function doesn't know the size of the sequence you're dereferencing,
    so any IndexErrors will happen when you do said derferencing.

    """
    def none_is_infinity(key):
        """Return a sort key such that None sorts higher than anything else."""
        return (1, None) if key is None else (0, key)

    if not isinstance(j, slice):
        raise TypeError('First argument must be a slice.')

    jstart = j.start or 0

    if isinstance(k, slice):
        kstart = k.start or 0

        # Compute min(j.stop, k.stop + jstart) where None means infinity:
        stop = min(j.stop,
                   None if k.stop is None else k.stop + jstart,
                   key=none_is_infinity)

        return slice(jstart + kstart, stop)
    else:
        return jstart + k
