# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Dataset for magnetic resonance imaging (MRI) data.

This module offers functions to import into PyMVPA MRI data from files
in any format supported by NiBabel_ (e.g. NIfTI, MINC, Analyze), and
export PyMVPA datasets back into data formats supported by NiBabel_.

.. _NiBabel: http://nipy.sourceforge.net/nibabel
"""

__docformat__ = 'restructuredtext'

from mvpa.base import externals
externals.exists('nibabel', raise_=True)

import sys
import numpy as np
from mvpa.support.copy import deepcopy
from mvpa.misc.support import Event
from mvpa.base.collections import DatasetAttribute
from mvpa.base.dataset import _expand_attribute

if __debug__:
    from mvpa.base import debug

from mvpa.datasets.base import Dataset
from mvpa.mappers.fx import _uniquemerge2literal
from mvpa.mappers.flatten import FlattenMapper
from mvpa.mappers.boxcar import BoxcarMapper
from mvpa.base import warning


def _data2img(data, hdr=None, imgtype=None):
    # input data is t,x,y,z
    # let's try whether we can get it done with nibabel
    import nibabel
    if imgtype is None:
        # default is NIfTI1
        imgtype = nibabel.Nifti1Image
    else:
        itype = imgtype

def _img2data(src):
    # break early of nothing has been given
    # XXX feels a little strange to handle this so deep inside, but well...
    if src is None:
        return None

    # let's try whether we can get it done with nibabel
    import nibabel
    if isinstance(src, str):
        # filename
        img = nibabel.load(src)
    else:
        # assume this is an image already
        img = src
    if isinstance(img, nibabel.spatialimages.SpatialImage):
        # nibabel image, dissect and return pieces
        return _get_txyz_shaped(img.get_data()), img.get_header(), img.__class__
    else:
        # no clue what it is
        return None


def map2nifti(dataset, data=None, imghdr=None, imgtype=None):
    """Maps data(sets) into the original dataspace and wraps it into an Image.

    Parameters
    ----------
    dataset : Dataset
      The mapper of this dataset is used to perform the reverse-mapping.
    data : ndarray or Dataset, optional
      The data to be wrapped into NiftiImage. If None (default), it
      would wrap samples of the provided dataset. If it is a Dataset
      instance -- takes its samples for mapping.
    imghdr : None or dict, optional
      Image header data. If None, the header is taken from `dataset.a.imghdr`.
    imgtype : None or class, optional
      Image class to be used for the instance. If None, the type is taken
      from `dataset.a.imgtype`.

    Returns
    -------
    Image
      Instance of a class derived from :class:`nibabel.spatialimages.SpatialImage`,
      such as Nifti1Image
    """
    import nibabel
    if data is None:
        data = dataset.samples
    elif isinstance(data, Dataset):
        # ease users life
        data = data.samples

    # call the appropriate function to map single samples or multiples
    if len(data.shape) > 1:
        dsarray = dataset.a.mapper.reverse(data)
    else:
        dsarray = dataset.a.mapper.reverse1(data)

    if imghdr is None:
        if 'imghdr' in dataset.a:
            imghdr = dataset.a.imghdr
        elif __debug__:
            debug('DS_NIFTI', 'No image header found. Using defaults.')

    if imgtype is None:
        if 'imgtype' in dataset.a:
            imgtype = dataset.a.imgtype
        else:
            imgtype = nibabel.Nifti1Image
            if __debug__:
                debug('DS_NIFTI',
                      'No image type found in %s. Using default Nifti1Image.'
                      % (dataset.a))

    if issubclass(imgtype, nibabel.spatialimages.SpatialImage) \
       and (imghdr is None or hasattr(imghdr, 'get_data_dtype')):
        # we can handle the desired image type and hdr with nibabel
        # use of `None` for the affine should cause to pull it from
        # the header
        return imgtype(_get_xyzt_shaped(dsarray), None, imghdr)
    else:
        raise ValueError(
            "Got imgtype=%s and imghdr=%s -- cannot generate an Image"
            % (imgtype, imghdr))
    return RuntimeError("Should have never got here -- check your Python")


def fmri_dataset(samples, targets=None, chunks=None, mask=None,
                 sprefix='voxel', tprefix='time', add_fa=None,):
    """Create a dataset from an fMRI timeseries image.

    The timeseries image serves as the samples data, with each volume becoming
    a sample. All 3D volume samples are flattened into one-dimensional feature
    vectors, optionally being masked (i.e. subset of voxels corresponding to
    non-zero elements in a mask image).

    In addition to (optional) samples attributes for targets and chunks the
    returned dataset contains a number of additional attributes:

    Samples attributes (per each volume):

      * volume index (time_indices)
      * volume acquisition time (time_coord)

    Feature attributes (per each voxel):

      * voxel indices (voxel_indices), sometimes referred to as ijk

    Dataset attributes:

      * dump of the image (e.g. NIfTI) header data (imghdr)
      * class of the image (e.g. Nifti1Image) (imgtype)
      * volume extent (voxel_dim)
      * voxel extent (voxel_eldim)

    The default attribute name is listed in parenthesis, but may be altered by
    the corresponding prefix arguments. The validity of the attribute values
    relies on correct settings in the NIfTI image header.

    Parameters
    ----------
    samples : str or NiftiImage or list
      fMRI timeseries, specified either as a filename (single file 4D image),
      an image instance (4D image), or a list of filenames or image instances
      (each list item corresponding to a 3D volume).
    targets : scalar or sequence
      Label attribute for each volume in the timeseries, or a scalar value that
      is assigned to all samples.
    chunks : scalar or sequence
      Chunk attribute for each volume in the timeseries, or a scalar value that
      is assigned to all samples.
    mask : str or NiftiImage
      Filename or image instance of a 3D volume mask. Voxels corresponding to
      non-zero elements in the mask will be selected. The mask has to be in the
      same space (orientation and dimensions) as the timeseries image
    sprefix : str or None
      Prefix for attribute names describing spatial properties of the
      timeseries. If None, no such attributes are stored in the dataset.
    tprefix : str or None
      Prefix for attribute names describing temporal properties of the
      timeseries. If None, no such attributes are stored in the dataset.
    add_fa : dict or None
      Optional dictionary with additional volumetric data that shall be stored
      as feature attributes in the dataset. The dictionary key serves as the
      feature attribute name. Each value might be of any type supported by the
      'mask' argument of this function.

    Returns
    -------
    Dataset
    """
    # load the samples
    imgdata, imghdr, imgtype = _load_anyimg(samples, ensure=True, enforce_dim=4)

    # figure out what the mask is, but only handle known cases, the rest
    # goes directly into the mapper which maybe knows more
    maskimg = _load_anyimg(mask)
    if maskimg is None:
        pass
    else:
        # take just data and ignore the header
        mask = maskimg[0]

    # compile the samples attributes
    sa = {}
    if not targets is None:
        sa['targets'] = _expand_attribute(targets, imgdata.shape[0], 'targets')
    if not chunks is None:
        sa['chunks'] = _expand_attribute(chunks, imgdata.shape[0], 'chunks')

    # create a dataset
    ds = Dataset(imgdata, sa=sa)
    if sprefix is None:
        space = None
    else:
        space = sprefix + '_indices'
    ds = ds.get_mapped(FlattenMapper(shape=imgdata.shape[1:], space=space))

    # now apply the mask if any
    if not mask is None:
        flatmask = ds.a.mapper.forward1(mask)
        # direct slicing is possible, and it is potentially more efficient,
        # so let's use it
        #mapper = StaticFeatureSelection(flatmask)
        #ds = ds.get_mapped(StaticFeatureSelection(flatmask))
        ds = ds[:, flatmask != 0]

    # load and store additional feature attributes
    if not add_fa is None:
        for fattr in add_fa:
            value = _load_anyimg(add_fa[fattr], ensure=True)[0]
            ds.fa[fattr] = ds.a.mapper.forward1(value)

    # store interesting props in the dataset
    ds.a['imghdr'] = imghdr
    ds.a['imgtype'] = imgtype
    # If there is a space assigned , store the extent of that space
    if sprefix is not None:
        ds.a[sprefix + '_dim'] = imgdata.shape[1:]
        # 'voxdim' is (x,y,z) while 'samples' are (t,z,y,x)
        ds.a[sprefix + '_eldim'] = _get_voxdim(imghdr)
        # TODO extend with the unit
    if tprefix is not None:
        ds.sa[tprefix + '_indices'] = np.arange(len(ds), dtype='int')
        ds.sa[tprefix + '_coords'] = np.arange(len(ds), dtype='float') \
                                     * _get_dt(imghdr)
        # TODO extend with the unit

    return ds


def _get_voxdim(hdr):
    """Get the size of a voxel from some image header format."""
    return hdr.get_zooms()[:-1]


def _get_dt(hdr):
    """Get the TR of a fMRI timeseries from some image header format."""
    return hdr.get_zooms()[-1]


def _get_txyz_shaped(arr):
    # we get the data as x,y,z[,t] but we want to have the time axis first
    # if any
    if len(arr.shape) == 4:
        arr = np.rollaxis(arr, -1)
    return arr


def _get_xyzt_shaped(arr):
    # we get the data as [t,]x,y,z but we want to have the time axis last
    # if any
    if len(arr.shape) == 4:
        arr = np.rollaxis(arr, 0, 4)
    return arr


def _load_anyimg(src, ensure=False, enforce_dim=None):
    """Load/access NIfTI data from files or instances.

    Parameters
    ----------
    src : str or NiftiImage
      Filename of a NIfTI image or a `NiftiImage` instance.
    ensure : bool, optional
      If True, throw ValueError exception if cannot be loaded.
    enforce_dim : int or None
      If not None, it is the dimensionality of the data to be enforced,
      commonly 4D for the data, and 3D for the mask in case of fMRI.

    Returns
    -------
    tuple or None
      If the source is not supported None is returned.  Otherwise a
      tuple of (imgdata, imghdr, imgtype)

    Raises
    ------
    ValueError
      If there is a problem with data (variable dimensionality) or
      failed to load data and ensure=True.
    """
    imgdata = imghdr = imgtype = None

    # figure out whether we have a list of things to load and handle that
    # first
    if (isinstance(src, list) or isinstance(src, tuple)) \
            and len(src)>0:
        # load from a list of given entries
        if enforce_dim is not None: enforce_dim_ = enforce_dim - 1
        else:                       enforce_dim_ = None
        srcs = [_load_anyimg(s, ensure=ensure, enforce_dim=enforce_dim_)
                for s in src]
        if __debug__:
            # lets check if they all have the same dimensionality
            shapes = [s[0].shape for s in srcs]
            if not np.all([s == shapes[0] for s in shapes]):
                raise ValueError, \
                      "Input volumes contain variable number of dimensions:" \
                      " %s" % (shapes,)
        # Combine them all into a single beast
        # will be t,x,y,z
        imgdata = np.array([s[0] for s in srcs])
        imghdr, imgtype = srcs[0][1:3]
    else:
        # try opening the beast; this might yield none in case of an unsupported
        # argument and is handled accordingly below
        data = _img2data(src)
        if not data is None:
            imgdata, imghdr, imgtype = data

    if imgdata is not None and enforce_dim is not None:
        shape, new_shape = imgdata.shape, None
        lshape = len(shape)

        # check if we need to tune up shape
        if lshape < enforce_dim:
            # if we are missing required dimension(s)
            new_shape = (1,)*(enforce_dim-lshape) + shape
        elif lshape > enforce_dim:
            # if there are bogus dimensions at the beginning
            bogus_dims = lshape - enforce_dim
            if shape[:bogus_dims] != (1,)*bogus_dims:
                raise ValueError, \
                      "Cannot enforce %dD on data with shape %s" \
                      % (enforce_dim, shape)
            new_shape = shape[bogus_dims:]

        # tune up shape if needed
        if new_shape is not None:
            if __debug__:
                debug('DS_NIFTI', 'Enforcing shape %s for %s data from %s' %
                      (new_shape, shape, src))
            imgdata.shape = new_shape

    if imgdata is None:
        return None
    else:
        return imgdata, imghdr, imgtype
