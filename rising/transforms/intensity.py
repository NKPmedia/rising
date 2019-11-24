import torch
import random
from typing import Union, Sequence

from .abstract import BaseTransform, PerSampleTransform, AbstractTransform, PerChannelTransform
from .functional.intensity import *


class ClampTransform(BaseTransform):
    def __init__(self, min: float, max: float, keys: Sequence = ('data',), grad: bool = False, **kwargs):
        """
        Apply augment_fn to keys

        Parameters
        ----------
        augment_fn: callable
            function for augmentation
        dims: tuple
            axes which should be mirrored
        grad: bool
            enable gradient computation inside transformation
        kwargs:
            keyword arguments passed to augment_fn
        """
        super().__init__(augment_fn=torch.clamp, keys=keys, grad=grad, min=min, max=max, **kwargs)


class NormRangeTransform(PerSampleTransform):
    def __init__(self, min: float, max: float, keys: Sequence = ('data',), per_channel: bool = True,
                 grad: bool = False, **kwargs):
        """
        Scale data to provided min and max values

        Parameters
        ----------
        min: float
            minimal value
        max: float
            maximal value
        keys: Sequence
            keys to normalize
        per_channel: bool
            normalize per channel
        grad: bool
            enable gradient computation inside transformation
        kwargs:
            keyword arguments passed to normalization function
        """
        super().__init__(augment_fn=norm_range, keys=keys, grad=grad,
                         min=min, max=max, per_channel=per_channel, **kwargs)


class NormMinMaxTransform(PerSampleTransform):
    def __init__(self, keys: Sequence = ('data',), per_channel: bool = True, grad: bool = False, **kwargs):
        """
        Scale data to [0, 1]

        Parameters
        ----------
        keys: Sequence
            keys to normalize
        per_channel: bool
            normalize per channel
        grad: bool
            enable gradient computation inside transformation
        kwargs:
            keyword arguments passed to normalization function
        """
        super().__init__(augment_fn=norm_min_max, keys=keys, grad=grad,
                         per_channel=per_channel, **kwargs)


class NormZeroMeanUnitStdTransform(PerSampleTransform):
    def __init__(self, keys: Sequence = ('data',), per_channel: bool = True, grad: bool = False, **kwargs):
        """
        Normalize mean to zero and std to one

        Parameters
        ----------
        keys: Sequence
            keys to normalize
        per_channel: bool
            normalize per channel
        grad: bool
            enable gradient computation inside transformation
        kwargs:
            keyword arguments passed to normalization function
        """
        super().__init__(augment_fn=norm_zero_mean_unit_std, keys=keys, grad=grad,
                         per_channel=per_channel, **kwargs)


class NormMeanStdTransform(PerSampleTransform):
    def __init__(self, mean: Union[float, Sequence], std: Union[float, Sequence],
                 keys: Sequence = ('data',), per_channel: bool = True, grad: bool = False, **kwargs):
        """
        Normalize mean and std with provided values

        Parameters
        ----------
        mean: float or Sequence
            used for mean normalization
        std: float or Sequence
            used for std normalization
        keys: Sequence
            keys to normalize
        per_channel: bool
            normalize per channel
        grad: bool
            enable gradient computation inside transformation
        kwargs:
            keyword arguments passed to normalization function
        """
        super().__init__(augment_fn=norm_mean_std, keys=keys, grad=grad,
                         mean=mean, std=std, per_channel=per_channel, **kwargs)


class NoiseTransform(PerChannelTransform):
    def __init__(self, noise_type: str, per_channel: bool = False,
                 keys: Sequence = ('data',), grad: bool = False, **kwargs):
        """
        Add noise to data

        Parameters
        ----------
        noise_type: str
            supports all inplace functions of a pytorch tensor
        per_channel: bool
            enable transformation per channel
        keys: Sequence
            keys to normalize
        grad: bool
            enable gradient computation inside transformation
        kwargs:
            keyword arguments passed to noise function

        See Also
        --------
        :func:`torch.Tensor.normal_`, :func:`torch.Tensor.exponential_`
        """
        super().__init__(augment_fn=add_noise, per_channel=per_channel, keys=keys,
                         grad=grad, noise_type=noise_type, **kwargs)


class ExponentialNoiseTransform(NoiseTransform):
    def __init__(self, lambd: float, keys: Sequence = ('data',), grad: bool = False, **kwargs):
        """
        Add exponential noise to data

        Parameters
        ----------
        lambd: float
            lambda of exponential distribution
        keys: Sequence
            keys to normalize
        grad: bool
            enable gradient computation inside transformation
        kwargs:
            keyword arguments passed to noise function
        """
        super().__init__(noise_type='exponential_', lambd=lambd, keys=keys, grad=grad, **kwargs)


class GaussianNoiseTransform(NoiseTransform):
    def __init__(self, mean: float, std: float, keys: Sequence = ('data',), grad: bool = False, **kwargs):
        """
        Add noise to data

        Parameters
        ----------
        mean: float
            mean of normal distribution
        std: float
            std of normal distribution
        keys: Sequence
            keys to normalize
        grad: bool
            enable gradient computation inside transformation
        kwargs:
            keyword arguments passed to noise function
        """
        super().__init__(noise_type='normal_', mean=mean, std=std, keys=keys, grad=grad, **kwargs)


class GammaCorrectionTransform(AbstractTransform):
    def __init__(self, gamma: Union[float, Sequence] = (0.5, 2),
                 keys: Sequence = ('data',), grad: bool = False, **kwargs):
        """
        Apply gamma correction as augmentation

        Parameters
        ----------
        gamma: float or sequence
            if gamma is float it is always applied. if gamma is a sequence it is interpreted as
            the minimal and maximal value. If the maximal value is greater than one, the transform
            chooses gamma <1 in 50% of the cases and gamma >1 in the other cases.
        keys: Sequence
            keys to normalize
        grad: bool
            enable gradient computation inside transformation
        kwargs:
            keyword arguments passed to superclass
        """
        super().__init__(augment_fn=gamma_correction, keys=keys, grad=grad)
        self.kwargs = kwargs
        self.gamma = gamma
        if not check_scalar(self.gamma):
            if not len(self.gamma) == 2:
                raise TypeError(f"Gamma needs to be scalar or a Sequence with two entries "
                                f"(min, max), found {self.gamma}")

    def forward(self, **data) -> dict:
        """
        Apply transformation

        Parameters
        ----------
        data: dict
            dict with tensors

        Returns
        -------
        dict
            dict with augmented data
        """
        if check_scalar(self.gamma):
            _gamma = self.gamma
        elif self.gamma[1] < 1:
            _gamma = random.uniform(self.gamma[0], self.gamma[1])
        else:
            if random.random() < 0.5:
                _gamma = _gamma = random.uniform(self.gamma[0], 1)
            else:
                _gamma = _gamma = random.uniform(1, self.gamma[1])

        for _key in self.keys:
            data[_key] = self.augment_fn(data[_key], _gamma, **self.kwargs)
        return data


class RandomValuePerChannelTransform(PerChannelTransform):
    def __init__(self, augment_fn: callable, random_mode: str, random_kwargs: dict = None,
                 per_channel: bool = False, keys: Sequence = ('data',),
                 grad: bool = False, **kwargs):
        """
        Apply augmentations which take random values as input by keyword
        :param:`value`

        Parameters
        ----------
        random_mode: str
            specifies distribution which should be used to sample additive value (supports all
            random generators from python random package)
        random_kwargs: dict
            additional arguments for random function
        per_channel: bool
            enable transformation per channel
        keys: Sequence
            keys which should be augmented
        grad: bool
            enable gradient computation inside transformation
        kwargs:
            keyword arguments passed to augment_fn
        """
        super().__init__(augment_fn=augment_fn, per_channel=per_channel,
                         keys=keys, grad=grad, **kwargs)
        self.random_mode = random_mode
        self.random_kwargs = {} if random_kwargs is None else random_kwargs

    def forward(self, **data) -> dict:
        """
        Perform Augmentation.

        Parameters
        ----------
        data: dict
            dict with data

        Returns
        -------
        dict
            augmented data
        """
        if self.per_channel:
            random_seed = random.random()
            for _key in self.keys:
                random.seed(random_seed)
                out = torch.empty_like(data[_key])
                for _i in range(data[_key].shape[1]):
                    rand_value = self.random_fn(**self.random_kwargs)
                    out[:, _i] = self.augment_fn(data[_key][:, _i], value=rand_value,
                                                 out=out[:, _i], **self.kwargs)
                data[_key] = out
            return data
        else:
            self.kwargs["value"] = self.random_fn(**self.random_kwargs)
            return super().forward(**data)

    @property
    def random_mode(self) -> str:
        """
        Get random mode

        Returns
        -------
        str
            random mode
        """
        return self._random_mode

    @random_mode.setter
    def random_mode(self, mode) -> None:
        """
        Set random mode

        Parameters
        ----------
        mode: str
            specifies distribution which should be used to sample additive value (supports all
            random generators from python random package)
        """
        self._random_mode = mode
        self.random_fn = getattr(random, mode)


class RandomAddValue(RandomValuePerChannelTransform):
    def __init__(self, random_mode: str, random_kwargs: dict = None, per_channel: bool = False,
                 keys: Sequence = ('data',), grad: bool = False, **kwargs):
        """
        Increase values additively

        Parameters
        ----------
        random_mode: str
            specifies distribution which should be used to sample additive value (supports all
            random generators from python random package)
        random_kwargs: dict
            additional arguments for random function
        per_channel: bool
            enable transformation per channel
        keys: Sequence
            keys which should be augmented
        grad: bool
            enable gradient computation inside transformation
        kwargs:
            keyword arguments passed to augment_fn
        """
        super().__init__(augment_fn=add_value, random_mode=random_mode,
                         random_kwargs=random_kwargs, per_channel=per_channel,
                         keys=keys, grad=grad, **kwargs)


class RandomScaleValue(RandomValuePerChannelTransform):
    def __init__(self, random_mode, random_kwargs: dict = None, per_channel: bool = False,
                 keys: Sequence = ('data',), grad: bool = False, **kwargs):
        """
        Scale values

        Parameters
        ----------
        random_mode: str
            specifies distribution which should be used to sample additive value (supports all
            random generators from python random package)
        random_kwargs: dict
            additional arguments for random function
        per_channel: bool
            enable transformation per channel
        keys: Sequence
            keys which should be augmented
        grad: bool
            enable gradient computation inside transformation
        kwargs:
            keyword arguments passed to augment_fn
        """
        super().__init__(augment_fn=scale_by_value, random_mode=random_mode,
                         random_kwargs=random_kwargs, per_channel=per_channel,
                         keys=keys, grad=grad, **kwargs)