# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Things concerned with types and type-checking in PyMVPA"""

import numpy as np


def is_datasetlike(obj):
    """Check if an object looks like a Dataset."""
    if hasattr(obj, 'samples') and \
       hasattr(obj, 'sa') and \
       hasattr(obj, 'fa') and \
       hasattr(obj, 'a'):
        return True

    return False


def accepts_dataset_as_samples(fx):
    """Decorator to extract samples from Datasets.

    Little helper to allow methods to be written for plain data (if they
    don't need information from a Dataset), but at the same time also
    accept whole Datasets as input.
    """
    def extract_samples(obj, data):
        if is_datasetlike(data):
            return fx(obj, data.samples)
        else:
            return fx(obj, data)
    return extract_samples


def asobjarray(x):
    """Generates numpy.ndarray with dtype object from an iterable

    Is needed to assure object dtype, so first empty array of
    dtype=object needs to be constructed and then only items to be
    assigned.

    Parameters
    ----------
    x : list or tuple or ndarray
    """
    res = np.empty(len(x), dtype=object)
    res[:] = x
    return res
