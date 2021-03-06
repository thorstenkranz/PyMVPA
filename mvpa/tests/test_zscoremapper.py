# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Unit tests for PyMVPA ZScore mapper"""


from mvpa.base import externals

from mvpa.support.copy import deepcopy
import numpy as np

from mvpa.datasets.base import dataset_wizard
from mvpa.mappers.zscore import ZScoreMapper, zscore
from mvpa.testing.tools import assert_array_almost_equal, assert_array_equal, \
        assert_equal, assert_raises, ok_, nodebug

from mvpa.testing.datasets import datasets

def test_mapper_vs_zscore():
    """Test by comparing to results of elderly z-score function
    """
    # data: 40 sample feature line in 20d space (40x20; samples x features)
    dss = [
        dataset_wizard(np.concatenate(
            [np.arange(40) for i in range(20)]).reshape(20,-1).T,
                targets=1, chunks=1),
        ] + datasets.values()

    for ds in dss:
        ds1 = deepcopy(ds)
        ds2 = deepcopy(ds)

        zsm = ZScoreMapper(chunks_attr=None)
        assert_raises(RuntimeError, zsm.forward, ds1.samples)
        zsm.train(ds1)
        ds1z = zsm.forward(ds1.samples)

        zscore(ds2, chunks_attr=None)
        assert_array_almost_equal(ds1z, ds2.samples)
        assert_array_equal(ds1.samples, ds.samples)

@nodebug(['ID_IN_REPR', 'MODULE_IN_REPR'])
def test_zcore_repr():
    # Just basic test if everything is sane... no proper comparison
    for m in (ZScoreMapper(chunks_attr=None),
              ZScoreMapper(params=(3, 1)),
              ZScoreMapper()):
        mr = eval(repr(m))
        ok_(isinstance(mr, ZScoreMapper))

def test_zscore():
    """Test z-scoring transformation
    """
    # dataset: mean=2, std=1
    samples = np.array((0, 1, 3, 4, 2, 2, 3, 1, 1, 3, 3, 1, 2, 2, 2, 2)).\
        reshape((16, 1))
    data = dataset_wizard(samples.copy(), targets=range(16), chunks=[0] * 16)
    assert_equal(data.samples.mean(), 2.0)
    assert_equal(data.samples.std(), 1.0)
    data_samples = data.samples.copy()
    zscore(data, chunks_attr='chunks')

    # copy should stay intact
    assert_equal(data_samples.mean(), 2.0)
    assert_equal(data_samples.std(), 1.0)
    # we should be able to operate on ndarrays
    # But we can't change type inplace for an array, can't we?
    assert_raises(TypeError, zscore, data_samples, chunks_attr=None)
    # so lets do manually
    data_samples = data_samples.astype(float)
    zscore(data_samples, chunks_attr=None)
    assert_array_equal(data.samples, data_samples)

    # check z-scoring
    check = np.array([-2, -1, 1, 2, 0, 0, 1, -1, -1, 1, 1, -1, 0, 0, 0, 0],
                    dtype='float64').reshape(16, 1)
    assert_array_equal(data.samples, check)

    data = dataset_wizard(samples.copy(), targets=range(16), chunks=[0] * 16)
    zscore(data, chunks_attr=None)
    assert_array_equal(data.samples, check)

    # check z-scoring taking set of labels as a baseline
    data = dataset_wizard(samples.copy(),
                   targets=[0, 2, 2, 2, 1] + [2] * 11,
                   chunks=[0] * 16)
    zscore(data, param_est=('targets', [0, 1]))
    assert_array_equal(samples, data.samples + 1.0)

    # check that zscore modifies in-place; only guaranteed if no upcasting is
    # necessary
    samples = samples.astype('float')
    data = dataset_wizard(samples,
                   targets=[0, 2, 2, 2, 1] + [2] * 11,
                   chunks=[0] * 16)
    zscore(data, param_est=('targets', [0, 1]))
    assert_array_equal(samples, data.samples)

    # these might be duplicating code above -- but twice is better than nothing

    # dataset: mean=2, std=1
    raw = np.array((0, 1, 3, 4, 2, 2, 3, 1, 1, 3, 3, 1, 2, 2, 2, 2))
    # dataset: mean=12, std=1
    raw2 = np.array((0, 1, 3, 4, 2, 2, 3, 1, 1, 3, 3, 1, 2, 2, 2, 2)) + 10
    # zscore target
    check = [-2, -1, 1, 2, 0, 0, 1, -1, -1, 1, 1, -1, 0, 0, 0, 0]

    ds = dataset_wizard(raw.copy(), targets=range(16), chunks=[0] * 16)
    pristine = dataset_wizard(raw.copy(), targets=range(16), chunks=[0] * 16)

    zm = ZScoreMapper()
    # should do global zscore by default
    zm.train(ds)                        # train
    assert_array_almost_equal(zm.forward(ds), np.transpose([check]))
    # should not modify the source
    assert_array_equal(pristine, ds)

    # if we tell it a different mean it should obey the order
    zm = ZScoreMapper(params=(3,1))
    zm.train(ds)
    assert_array_almost_equal(zm.forward(ds), np.transpose([check]) - 1 )
    assert_array_equal(pristine, ds)

    # let's look at chunk-wise z-scoring
    ds = dataset_wizard(np.hstack((raw.copy(), raw2.copy())),
                        targets=range(32),
                        chunks=[0] * 16 + [1] * 16)
    # by default chunk-wise
    zm = ZScoreMapper()
    zm.train(ds)                        # train
    assert_array_almost_equal(zm.forward(ds), np.transpose([check + check]))
    # we should be able to do that same manually
    zm = ZScoreMapper(params={0: (2,1), 1: (12,1)})
    zm.train(ds)                        # train
    assert_array_almost_equal(zm.forward(ds), np.transpose([check + check]))
