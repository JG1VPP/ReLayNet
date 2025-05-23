import torch
import torch.nn as nn
import torch.nn.functional as F
from mmengine import MODELS

from hmeg.model.bilinear import crop_bbox_batch
from hmeg.model.layers import GlobalAvgPool, build_cnn


@MODELS.register_module()
class PatchDiscriminator(nn.Module):
    def __init__(
        self,
        arch,
        normalization="batch",
        activation="leakyrelu-0.2",
        padding="same",
        pooling="avg",
        input_size=(128, 128),
        layout_dim=0,
    ):
        super(PatchDiscriminator, self).__init__()
        input_dim = 3 + layout_dim
        arch = "I%d,%s" % (input_dim, arch)
        cnn_kwargs = {
            "arch": arch,
            "normalization": normalization,
            "activation": activation,
            "pooling": pooling,
            "padding": padding,
        }
        self.cnn, output_dim = build_cnn(**cnn_kwargs)
        self.classifier = nn.Conv2d(output_dim, 1, kernel_size=1, stride=1)

    def forward(self, x, layout=None):
        if layout is not None:
            x = torch.cat([x, layout], dim=1)
        return self.cnn(x)


@MODELS.register_module()
class AcDiscriminator(nn.Module):
    def __init__(
        self,
        vocab,
        arch,
        normalization="none",
        activation="relu",
        padding="same",
        pooling="avg",
    ):
        super(AcDiscriminator, self).__init__()
        self.vocab = vocab

        cnn_kwargs = {
            "arch": arch,
            "normalization": normalization,
            "activation": activation,
            "pooling": pooling,
            "padding": padding,
        }
        cnn, D = build_cnn(**cnn_kwargs)
        self.cnn = nn.Sequential(cnn, GlobalAvgPool(), nn.Linear(D, 1024))
        num_objects = len(vocab["object_idx_to_name"])

        self.real_classifier = nn.Linear(1024, 1)
        self.obj_classifier = nn.Linear(1024, num_objects)

    def forward(self, x, y):
        if x.dim() == 3:
            x = x[:, None]
        vecs = self.cnn(x)
        real_scores = self.real_classifier(vecs)
        obj_scores = self.obj_classifier(vecs)
        ac_loss = F.cross_entropy(obj_scores, y)
        return real_scores, ac_loss


@MODELS.register_module()
class AcCropDiscriminator(nn.Module):
    def __init__(
        self,
        vocab,
        arch,
        normalization="none",
        activation="relu",
        object_size=64,
        padding="same",
        pooling="avg",
    ):
        super(AcCropDiscriminator, self).__init__()
        self.vocab = vocab
        self.discriminator = AcDiscriminator(
            vocab, arch, normalization, activation, padding, pooling
        )
        self.object_size = object_size

    def forward(self, imgs, objs, boxes, obj_to_img):
        crops = crop_bbox_batch(imgs, boxes, obj_to_img, self.object_size)
        real_scores, ac_loss = self.discriminator(crops, objs)
        return real_scores, ac_loss
