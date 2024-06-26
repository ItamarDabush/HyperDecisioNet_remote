from utils.common_tools import set_random_seed, weights_init_kaiming
import functools

import torch.nn as nn
import torch.optim.lr_scheduler
from torchvision.models import vgg11, resnet18

from data.transforms import BasicTransforms, ImageNetTransforms
from models.network_in_network import NetworkInNetwork
from models.wide_resnet import wide_resnet28_10
from models.basic_classifier import BasicClassifier, HyperBasicClassifier, EnsembleBasicClassifier
from trainers.basic_trainer import BasicTrainer
from utils.constants import INPUT_SIZE
from utils.early_stopping import EarlyStopping


class NetworkInNetworkTrainer(BasicTrainer):

    def init_early_stopping(self):
        early_stopping_params = self.early_stopping_params
        if early_stopping_params is None:
            early_stopping_params = {'mode': 'min', 'patience': 50, 'verbose': True}
        return EarlyStopping(**early_stopping_params)

    def _init_model(self):
        num_in_channels = INPUT_SIZE[self.dataset_name][0]
        # model = NetworkInNetwork(num_classes=self.num_classes, num_in_channels=num_in_channels,
        #                          config=[(16, 3, 1, 1), ('M', 2, None, 0), (32, 3, 1, 1), ('M', 2, None, 0),
        #                                  ('V', int(32 * ((INPUT_SIZE[self.dataset_name][1]) / 4) ** 2)),
        #                                  ('fc', 128, True), ('fc', 10, False)])
        model = NetworkInNetwork(num_classes=self.num_classes, num_in_channels=num_in_channels,
                                 config=[(192, 5), (160, 1), (96, 1), 'M', 'D', (192, 5), (192, 1), (192, 1), 'A', 'D', (192, 3), (192, 1), (10, 1)])
        for m in model.modules():
            if isinstance(m, nn.Conv2d):
                m.weight.data.normal_(0, 0.05)
                m.bias.data.normal_(0, 0.0)
        return model


class ResNetTrainer(BasicTrainer):

    def init_optimizer(self):
        optimizer = torch.optim.SGD(self.model.parameters(), lr=self.learning_rate, momentum=0.9, weight_decay=1e-4)
        return optimizer

    def init_transforms(self, padding_mode='constant'):
        if self.dataset_name == 'ImageNet':
            return ImageNetTransforms(self.augment, color_jitter=True)
        return BasicTransforms(self.dataset_name, self.augment, padding_mode=padding_mode)

    def _init_model(self):
        model = resnet18()
        return model


class WideResNetTrainer(BasicTrainer):

    def init_transforms(self, padding_mode='constant'):
        return BasicTransforms(self.dataset_name, self.augment, padding_mode='reflect')

    def init_lr_scheduler(self):
        return torch.optim.lr_scheduler.MultiStepLR(self.optimizer, [60, 120, 160], gamma=0.2, verbose=True)

    def lr_scheduler_step(self, epoch=-1, train_acc=None, train_loss=None, test_acc=None, test_loss=None):
        self.lr_scheduler.step()

    def init_optimizer(self):
        optimizer = torch.optim.SGD(self.model.parameters(), lr=self.learning_rate,
                                    momentum=0.9, weight_decay=5e-4, nesterov=True)
        return optimizer

    def _init_model(self):
        model = wide_resnet28_10(num_classes=self.num_classes)
        return model


class VGG11Trainer(BasicTrainer):

    def init_lr_scheduler(self):
        return torch.optim.lr_scheduler.MultiStepLR(self.optimizer, [60, 120, 160], gamma=0.2, verbose=True)

    def lr_scheduler_step(self, epoch=-1, train_acc=None, train_loss=None, test_acc=None, test_loss=None):
        self.lr_scheduler.step()

    def _init_model(self):
        model = vgg11(num_classes=self.num_classes, pretrained=True)
        # model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, self.num_classes)
        return model


class BasicClassifierTrainer(BasicTrainer):

    def __init__(self):
        super(BasicClassifierTrainer, self).__init__()

    def init_early_stopping(self):
        early_stopping_params = self.early_stopping_params
        if early_stopping_params is None:
            early_stopping_params = {'mode': 'min', 'patience': 50, 'verbose': True}
        return EarlyStopping(**early_stopping_params)

    def _init_model(self):
        set_random_seed(0)
        model = BasicClassifier(num_classes=self.num_classes, image_size=self.image_size)
        model.apply(functools.partial(weights_init_kaiming, scale=0.1))
        return model


if __name__ == '__main__':
    trainer = NetworkInNetworkTrainer()
    # trainer = BasicClassifierTrainer()
    # trainer = WideResNetTrainer()
    trainer.train_model()
    # trainer.evaluate()
