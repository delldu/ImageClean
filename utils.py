import numpy as np
import cv2
import os
import math
import scipy.io as sio
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

import pdb


# https://www.cs.columbia.edu/CAVE/software/softlib/dorf.php

# def load_CRF():
#     CRF = scipy.io.loadmat('matdata/201_CRF_data.mat')
#     iCRF = scipy.io.loadmat('matdata/dorfCurvesInv.mat')
#     B_gl = CRF['B']
#     I_gl = CRF['I']

#     if os.path.exists('matdata/201_CRF_iCRF_function.mat')==0:
#         CRF_para = np.array(CRF_function_transfer(I_gl, B_gl))
#         iCRF_para = 1. / CRF_para
#         scipy.io.savemat('matdata/201_CRF_iCRF_function.mat', {'CRF':CRF_para, 'iCRF':iCRF_para})
#     else:
#         Bundle = scipy.io.loadmat('matdata/201_CRF_iCRF_function.mat')
#         CRF_para = Bundle['CRF']
#         iCRF_para = Bundle['iCRF']

#     return CRF_para, iCRF_para

    
class AverageMeter(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def ReadImg(filename):
    img = cv2.imread(filename)
    img = img[:, :, ::-1] / 255.0
    img = np.array(img).astype('float32')

    return img


def hwc_to_chw(img):
    return np.transpose(img, axes=[2, 0, 1])


def chw_to_hwc(img):
    return np.transpose(img, axes=[1, 2, 0])


####################################################
#################### noise model ###################
####################################################

def func(x, a):
    return np.power(x, a)

def CRF_curve_fit(I, B):
    popt, pcov = curve_fit(func, I, B)
    return popt

def CRF_function_transfer(x, y):
    para = []
    for crf in range(201):
        temp_x = np.array(x[crf, :])
        temp_y = np.array(y[crf, :])
        para.append(CRF_curve_fit(temp_x, temp_y))

        # (Pdb) pp temp_x.shape, temp_y.shape
        # ((1024,), (1024,))
        # pdb.set_trace()
        # (Pdb) pp para[0]
        # array([0.34269688])
        # (Pdb) pp para[1]
        # array([0.33438498])
    return para


def mosaic_bayer(rgb, pattern, noiselevel):

    w, h, c = rgb.shape
    if pattern == 1:
        num = [1, 2, 0, 1]
    elif pattern == 2:
        num = [1, 0, 2, 1]
    elif pattern == 3:
        num = [2, 1, 1, 0]
    elif pattern == 4:
        num = [0, 1, 1, 2]
    elif pattern == 5:
        return rgb

    B = np.zeros((w, h))

    # Path is like N ?
    B[0:w:2, 0:h:2] = rgb[0:w:2, 0:h:2, num[0]]
    B[0:w:2, 1:h:2] = rgb[0:w:2, 1:h:2, num[1]]
    B[1:w:2, 0:h:2] = rgb[1:w:2, 0:h:2, num[2]]
    B[1:w:2, 1:h:2] = rgb[1:w:2, 1:h:2, num[3]]

    gauss = np.random.normal(0, noiselevel / 255., (w, h))
    # gauss = gauss.reshape(w, h)
    B = B + gauss

    return B

def CRF_Map_opt(Img, popt):
    # w, h, c = Img.shape
    output_Img = Img.copy()

    output_Img = np.power(output_Img, *popt)
    return output_Img


def Demosaic(B_b, pattern):

    B_b = B_b * 255
    B_b = B_b.astype(np.uint16)

    if pattern == 1:
        lin_rgb = cv2.demosaicing(B_b, cv2.COLOR_BayerGB2BGR)
    elif pattern == 2:
        lin_rgb = cv2.demosaicing(B_b, cv2.COLOR_BayerGR2BGR)
    elif pattern == 3:
        lin_rgb = cv2.demosaicing(B_b, cv2.COLOR_BayerBG2BGR)
    elif pattern == 4:
        lin_rgb = cv2.demosaicing(B_b, cv2.COLOR_BayerRG2BGR)
    elif pattern == 5:
        lin_rgb = B_b

    lin_rgb = lin_rgb[:, :, ::-1] / 255.

    # pdb.set_trace()
    # pattern = 2
    # (Pdb) pp B_b.shape
    # (512, 512)
    # (Pdb) pp lin_rgb.shape
    # (512, 512, 3)

    return lin_rgb

# CRF: Modeling the space of camera response functions
# http://www-cs.ccny.cuny.edu/~grossberg/publications/Modeling_the_Space_of_Camera_Response_Functions_Images.pdf
def AddNoiseMosai(x,
                  CRF_para,
                  iCRF_para,
                  sigma_s,
                  sigma_c,
                  crf_index,
                  pattern):
    w, h, c = x.shape
    temp_x = CRF_Map_opt(x, iCRF_para[crf_index])

    # pdb.set_trace()
    # (Pdb) pp x.shape
    # (512, 512, 3)

    # (Pdb) pp CRF_para.shape
    # (201, 1)
    # (Pdb) pp CRF_para.mean()
    # 0.5285327803038496
    # (Pdb) pp CRF_para.std()
    # 0.3079649125807247

    # CRF_para*iCRF_para == 1
    # (Pdb) pp B.shape
    # (201, 1024)
    # (Pdb) pp I.shape
    # (201, 1024)

    sigma_s = np.reshape(sigma_s, (1, 1, c))
    noise_s_map = np.multiply(sigma_s, temp_x)
    noise_s = np.random.randn(w, h, c) * noise_s_map
    temp_x_n = temp_x + noise_s

    noise_c = np.zeros((w, h, c))
    for chn in range(3):
        noise_c[:, :, chn] = np.random.normal(0, sigma_c[chn], (w, h))

    temp_x_n = temp_x_n + noise_c
    temp_x_n = np.clip(temp_x_n, 0.0, 1.0)
    temp_x_n = CRF_Map_opt(temp_x_n, CRF_para[crf_index])

    # pdb.set_trace()
    # (Pdb) pp temp_x_n.shape
    # (512, 512, 3)

    B_b_n = mosaic_bayer(temp_x_n[:, :, ::-1], pattern, 0)
    # pdb.set_trace()
    # (Pdb) pp B_b_n.shape
    # (512, 512)

    lin_rgb_n = Demosaic(B_b_n, pattern)
    # pdb.set_trace()

    # (Pdb) lin_rgb.shape
    # (512, 512, 3)    

    result = lin_rgb_n

    # pdb.set_trace()
    # (Pdb) pp result.shape
    # (512, 512, 3)

    return result


def AddRealNoise(image, CRF_para, iCRF_para):
    # array([0.0923482, 0.0048792, 0.1523728])
    sigma_s = np.random.uniform(0.0, 0.16, (3, ))
    sigma_c = np.random.uniform(0.0, 0.06, (3, ))

    CRF_index = np.random.choice(201)
    pattern = np.random.choice(4) + 1
    noise_img = AddNoiseMosai(image, CRF_para, iCRF_para, sigma_s, sigma_c, CRF_index, pattern)
    noise_level = sigma_s * np.power(image, 0.5) + sigma_c

    # pdb.set_trace()

    return noise_img, noise_level
