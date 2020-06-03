# Copyright (C) 2020  GreenWaves Technologies, SAS

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging

import numpy as np

from quantization.quantization_record_base import ScalableFilterQuantizationRecordBase

LOG = logging.getLogger("nntool." + __name__)


def linear(params,
           in_tensors,
           qrec: ScalableFilterQuantizationRecordBase,
           details=None):

    in_dims = params.in_dims[0]
    out_dims = params.out_dims[0]
    weights = qrec.prepare_weights(params, params.weights, ktype="symmetric")
    in_tensor = qrec.prepare_inputs(params, in_tensors, ktype="symmetric")[0]

    if details is not None:
        details['min_acc'] = float("Infinity")
        details['max_acc'] = float("-Infinity")

    if params.has_bias:
        biases = qrec.prepare_biases(params, params.biases, params.weights, ktype="symmetric")
        if qrec.acc_q != qrec.biases_q:
            biases = qrec.acc_q.expand_from(biases, qrec.biases_q)
        acc_tensor = np.ones((out_dims.c, out_dims.h, out_dims.w),
                             dtype=qrec.acc_q.dtype) * biases.reshape((out_dims.c, out_dims.h, out_dims.w))
        acc_tensor = acc_tensor.transpose(out_dims.transpose_from_order(('c', 'h', 'w')))
    else:
        acc_tensor = np.zeros(out_dims.shape,
                              dtype=qrec.acc_q.dtype)

    # force the bit dimension of the input tensor to the bit width of the calc
    # so that the dot product occurs in this precision
    in_tensor = in_tensor.astype(qrec.calc_q.dtype)

    in_tensor = in_tensor.reshape((in_dims.size()))
    filt = params.filter.get_filter_dims()
    for out_c in range(out_dims.c):
        # Expand and normalize the accumulator
        if qrec.calc_q != qrec.acc_q:
            acc_tensor = qrec.calc_q.expand_from(acc_tensor, qrec.acc_q)

        w_slice = weights[filt.srange(out_c=out_c)].reshape((in_dims.size()))

        res = np.dot(in_tensor, w_slice)

        if details is not None:
            details['min_acc'] = min(np.sum(res[res < 0]), details['min_acc'])
            details['max_acc'] = min(np.sum(res[res > 0]), details['max_acc'])

        acc_slice = acc_tensor[out_dims.srange(c=out_c, h=0, w=0)]
        acc_slice += res

        if qrec.calc_q != qrec.acc_q:
            acc_tensor = qrec.acc_q.reduce_from(acc_tensor, qrec.calc_q)

        if details is not None:
            details['min_acc'] = min(np.min(acc_slice), details['min_acc'])
            details['max_acc'] = max(np.max(acc_slice), details['max_acc'])

    # details['acc_before'] = acc_tensor.copy()
    acc_tensor = qrec.apply_multiplicative_bias(
        params, acc_tensor, out_dims.get_order_idx('c'), ktype="symmetric")
    # details['acc_after'] = acc_tensor.copy()

    if qrec and qrec.out_qs[0] != qrec.acc_q:
        acc_tensor = qrec.out_qs[0].reduce_from(acc_tensor, qrec.acc_q)

    return qrec.get_outputs(params, [acc_tensor], ktype="symmetric")
