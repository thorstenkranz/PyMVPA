#emacs: -*- mode: python-mode; py-indent-offset: 4; indent-tabs-mode: nil -*-
#ex: set sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Dataset that gets its samples from an EEP binary file"""

__docformat__ = 'restructuredtext'


import numpy as N

from mvpa.datasets.mapped import MappedDataset
from mvpa.misc.eepbin import EEPBin
from mvpa.mappers.mask import MaskMapper
from mvpa.base.dochelpers import enhancedDocString



class EEPDataset(MappedDataset):
    """Dataset using a EEP binary file as source.

    EEP files are used by eeprobe_ a software for analysing even-related
    potentials (ERP), which was developed at the Max-Planck Institute for
    Cognitive Neuroscience in Leipzig, Germany.

    .. _eegprobe: http://http://www.ant-neuro.com/products/eeprobe
    """
    def __init__(self, samples=None, dsattr=None, **kwargs):
        """Initialize EEPDataset.

        :Parameters:
          samples: Filename (string) of a EEP binary file or an `EEPBin`
                   object
        """
        # if dsattr is none, set it to an empty dict
        if dsattr is None:
            dsattr = {}

        # default way to use the constructor: with filename
        if not samples is None:
            if isinstance(samples, str):
                # open the eep file
                try:
                    eb = EEPBin(samples)
                except RuntimeError, e:
                    warning("ERROR: EEPDatasets: Cannot open samples file %s" \
                            % samples) # should we make also error?
                    raise e
            elif isinstance(samples, EEPBin):
                # nothing special
                eb = samples
            else:
                raise ValueError, \
                      "EEPDataset constructor takes the filename of an " \
                      "EEP file or a EEPBin object as 'samples' argument."
            samples = eb.data
            # TODO: make proper properties for base Dataset based on _dsattr
            # update dsattr with some information from EEPBin
            dsattr['eb_dt'] = eb.dt
            dsattr['eb_channels'] = eb.channels
            dsattr['eb_t0'] = eb.t0

        # come up with mapper if fresh samples were provided
        if not samples is None:
            mapper = MaskMapper(N.ones((eb.nchannels,
                                        eb.nsamples), dtype='bool'))
        else:
            mapper = None

        # init dataset
        MappedDataset.__init__(self,
                               samples=samples,
                               mapper=mapper,
                               dsattr=dsattr,
                               **(kwargs))

    __doc__ = enhancedDocString('EEPDataset', locals(), MappedDataset)


    channelids = property(fget=lambda self: self._dsattr['eb_channels'],
                          doc='List of channel IDs')
    t0 = property(fget=lambda self: self._dsattr['eb_t0'],
                          doc='Location of first sample relative to stimulus ' \
                              'onset (in seconds).')
    dt = property(fget=lambda self: self._dsattr['eb_dt'],
                          doc='Time difference between two samples ' \
                              '(in seconds).')
    samplingrate = property(fget=lambda self: 1.0 / self._dsattr['eb_dt'],
                          doc='Time difference between two samples ' \
                              '(in seconds).')