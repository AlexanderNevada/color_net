import os
import traceback

import torch
import torch.nn.functional as F
import torch.nn as nn
import torch.optim as optim
from torch.autograd import Variable
from torchvision import transforms
import numpy as np

from myimgfolder import TrainImageFolder
from colornet import ColorNet

original_transform = transforms.Compose([
    transforms.Scale(256),
    transforms.RandomCrop(224),
    transforms.RandomHorizontalFlip(),
    #transforms.ToTensor()
])

have_cuda = torch.cuda.is_available()
epochs = 32

data_dir = '/cluster/scratch/qimaqi/data_5k/colorization/'  # "../images256/"
train_set = TrainImageFolder(data_dir, original_transform)
train_set_size = len(train_set)
print('train_set_size',train_set_size)

train_set_classes = train_set.classes
train_loader = torch.utils.data.DataLoader(train_set, batch_size=32, shuffle=True, num_workers=4)
color_model = ColorNet()
if os.path.exists('./colornet_params.pth'):
    color_model.load_state_dict(torch.load('colornet_params.pth'))
if have_cuda:
    color_model.cuda()
optimizer = optim.Adadelta(color_model.parameters())


def train(epoch):
    color_model.train()
    print('Epoch',epoch)
    l2_loss = nn.MSELoss()

    try:
        for batch_idx, (data, classes) in enumerate(train_loader):
            messagefile = open('./message.txt', 'a')
            original_img = data[0].unsqueeze(1).float()
            img_ab = data[1].float()
            if have_cuda:
                original_img = original_img.cuda()
                img_ab = img_ab.cuda()
                classes = classes.cuda()
            original_img = Variable(original_img)
            img_ab = Variable(img_ab)
            classes = Variable(classes)
            optimizer.zero_grad()
            class_output, output = color_model(original_img, original_img)
            # ems_loss = torch.pow((img_ab - output), 2).sum() / torch.from_numpy(np.array(list(output.size()))).prod()
            ems_loss = l2_loss(output,img_ab)

            # cross_entropy_loss = 1/300 * F.cross_entropy(class_output, classes)
            loss = ems_loss # + cross_entropy_loss
            print('*a*b l2 normalized loss',loss)
            #lossmsg = 'loss: %.9f\n' % (loss.data[0])
            #messagefile.write(lossmsg)
            ems_loss.backward(retain_graph=True) # retrain varaibale
            # cross_entropy_loss.backward()
            optimizer.step()
            if batch_idx % 1000 == 0:
                message = 'Train Epoch:%d\tPercent:[%d/%d (%.0f%%)]\tLoss:%.9f\n' % (
                    epoch, batch_idx * len(data), len(train_loader.dataset),
                    100. * batch_idx / len(train_loader), loss.item())
                messagefile.write(message)
                torch.save(color_model.state_dict(), 'colornet_params.pth')
            messagefile.close()
            print('Train Epoch: {}[{}/{}({:.0f}%)]\tLoss: {:.9f}\n'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                100. * batch_idx / len(train_loader), loss.item()))
    except Exception:
        logfile = open('log.txt', 'w')
        logfile.write(traceback.format_exc())
        logfile.close()
    finally:
        torch.save(color_model.state_dict(), 'colornet_params_20_5.pth')


for epoch in range(1, epochs + 1):
    train(epoch)
