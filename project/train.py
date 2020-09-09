"""Model trainning & validating."""
# coding=utf-8
#
# /************************************************************************************
# ***
# ***    Copyright Dell 2020, All Rights Reserved.
# ***
# ***    File Author: Dell, 2020年 09月 09日 星期三 23:56:45 CST
# ***
# ************************************************************************************/
#

import os
import argparse
import torch
import torch.optim as optim
from data import get_data
from model import get_model, model_load, model_save, train_epoch, valid_epoch, model_setenv

if __name__ == "__main__":
    """Trainning model."""
    
    model_setenv()    

    parser = argparse.ArgumentParser()
    parser.add_argument('--outputdir', type=str, default="output", help="output directory")
    parser.add_argument('--checkpoint', type=str, default="output/ImageClean.pth", help="checkpoint file")
    parser.add_argument('--bs', type=int, default=2, help="batch size")
    parser.add_argument('--lr', type=float, default=1e-4, help="learning rate")
    parser.add_argument('--epochs', type=int, default=10)
    args = parser.parse_args()

    # Create directory to store weights
    if not os.path.exists(args.outputdir):
        os.makedirs(args.outputdir)

    # CPU or GPU ?
    device = torch.device(os.environ["DEVICE"])

    # get model
    model = get_model()
    model_load(model, args.checkpoint)
    model.to(device)

    # construct optimizer and learning rate scheduler,
    # xxxx--modify here
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.Adam(params, lr=args.lr)

    if os.environ["ENABLE_APEX"] == "YES":
        from apex import amp
        model, optimizer = amp.initialize(model, optimizer, opt_level="O1")

    lr_scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=1000, gamma=0.1)

    # get data loader
    train_dl, valid_dl = get_data(trainning=True, bs=args.bs)

    for epoch in range(args.epochs):
        print("Epoch {}/{}, learning rate: {} ...".format(epoch + 1, args.epochs, lr_scheduler.get_lr()))

        train_epoch(train_dl, model, optimizer, device, tag='train')

        valid_epoch(valid_dl, model, device, tag='valid')

        lr_scheduler.step()

        # xxxx--modify here
        if epoch == (args.epochs // 2) or (epoch == args.epochs - 1):
            model_save(model, os.path.join(args.outputdir, "latest-checkpoint.pth"))
