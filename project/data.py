"""Data loader."""
# coding=utf-8
#
# /************************************************************************************
# ***
# ***    Copyright Dell 2020, All Rights Reserved.
# ***
# ***    File Author: Dell, 2020年 09月 09日 星期三 14:24:21 CST
# ***
# ************************************************************************************/
#

import os
import glob
import torch
import random
from PIL import Image
import torch.utils.data as data
import torchvision.transforms as T
import torchvision.utils as utils

train_dataset_rootdir = "dataset/Renoir/Aligned"
CROP_SIZE = 512

def get_transform(train=True):
    """Transform images."""
    ts = []
    # if train:
    #     ts.append(T.RandomHorizontalFlip(0.5))

    ts.append(T.ToTensor())
    return T.Compose(ts)

class ImageCleanDataset(data.Dataset):
    """Define dataset."""

    def __init__(self, root, transforms=get_transform()):
        """Init dataset."""
        super(ImageCleanDataset, self).__init__()

        self.root = root
        self.transforms = transforms

        # load all images, sorting for alignment
        # dataset/Renoir/Aligned/Batch_001
        # ├── IMG_20160202_015216Reference.bmp
        # ├── IMG_20160202_015247Noisy.bmp
        # └── IMG_20160202_015252Noisy.bmp
        dirs = list(sorted(os.listdir(root)))
        self.noise_images = []
        self.clean_images = []
        for d in dirs:
            clean_files = glob.glob(root + "/" + d + "/*Reference.bmp")
            noise_files = glob.glob(root + "/" + d + "/*Noisy.bmp")
            for n in noise_files:
                self.noise_images.append(n)
                self.clean_images.append(clean_files[0])

    def __getitem__(self, idx):
        """Load images."""
        noise_image = Image.open(self.noise_images[idx]).convert("RGB")
        clean_image = Image.open(self.clean_images[idx]).convert("RGB")

        # left, top, right, bottom = 0, 0, 512, 512
        H, W = noise_image.height, noise_image.width
        left = random.randint(0, W - CROP_SIZE)
        top = random.randint(0, H - CROP_SIZE)
        box = (left, top, left + CROP_SIZE, top + CROP_SIZE)
        noise_image = noise_image.crop(box)
        clean_image = clean_image.crop(box)

        if self.transforms is not None:
            noise_image = self.transforms(noise_image)
            clean_image = self.transforms(clean_image)

        return noise_image, clean_image

    def __len__(self):
        """Return total numbers of images."""
        return len(self.noise_images)

    def __repr__(self):
        """
        Return printable representation of the dataset object.
        """
        fmt_str = 'Dataset ' + self.__class__.__name__ + '\n'
        fmt_str += '    Number of samples: {}\n'.format(self.__len__())
        fmt_str += '    Root Location: {}\n'.format(self.root)
        tmp = '    Transforms: '
        fmt_str += '{0}{1}\n'.format(tmp, self.transforms.__repr__().replace('\n', '\n' + ' ' * len(tmp)))
        return fmt_str

def train_data(bs):
    """Get data loader for trainning & validating, bs means batch_size."""

    train_ds = ImageCleanDataset(train_dataset_rootdir, get_transform(train=True))
    print(train_ds)

    # Split train_ds in train and valid set
    valid_len = int(0.2 * len(train_ds))
    indices = [i for i in range(len(train_ds) - valid_len, len(train_ds))]

    valid_ds = data.Subset(train_ds, indices)
    indices = [i for i in range(len(train_ds) - valid_len)]
    train_ds = data.Subset(train_ds, indices)

    # Define training and validation data loaders
    train_dl = data.DataLoader(train_ds, batch_size=bs, shuffle=True, num_workers=4)
    valid_dl = data.DataLoader(valid_ds, batch_size=bs * 2, shuffle=False, num_workers=4)

    return train_dl, valid_dl

def test_data(bs):
    """Get data loader for test, bs means batch_size."""
    _, test_dl = train_data(bs)

    return test_dl


def get_data(trainning=True, bs=4):
    """Get data loader for trainning & validating, bs means batch_size."""

    return train_data(bs) if trainning else test_data(bs)

def ImageCleanDatasetTest():
    """Test dataset ..."""

    ds = ImageCleanDataset(train_dataset_rootdir)
    print(ds)
    src, tgt = ds[10]
    grid = utils.make_grid(torch.cat([src.unsqueeze(0), tgt.unsqueeze(0)], dim=0), nrow=2)
    ndarr = grid.mul(255).add_(0.5).clamp_(0, 255).permute(1, 2, 0).to('cpu', torch.uint8).numpy()
    image = Image.fromarray(ndarr)

    image.show()


if __name__ == '__main__':
    """Unit Test ..."""

    ImageCleanDatasetTest()
