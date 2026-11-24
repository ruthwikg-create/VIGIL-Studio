"""A compact real trainable 1D residual convolutional quality research network.
Random initialization is NOT a clinically useful pretrained model.
"""
from __future__ import annotations

def build_network(width=24):
    import torch
    from torch import nn
    class Residual(nn.Module):
        def __init__(self,ch):
            super().__init__();self.net=nn.Sequential(nn.Conv1d(ch,ch,7,padding=3,bias=False),nn.BatchNorm1d(ch),nn.GELU(),nn.Conv1d(ch,ch,5,padding=2,bias=False),nn.BatchNorm1d(ch));self.act=nn.GELU()
        def forward(self,x):return self.act(x+self.net(x))
    class WaveNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.features=nn.Sequential(nn.Conv1d(1,width,11,padding=5,bias=False),nn.BatchNorm1d(width),nn.GELU(),Residual(width),nn.MaxPool1d(4),nn.Conv1d(width,width*2,7,padding=3,bias=False),nn.BatchNorm1d(width*2),nn.GELU(),Residual(width*2),nn.MaxPool1d(4),nn.Conv1d(width*2,width*4,5,padding=2),nn.GELU(),nn.AdaptiveAvgPool1d(1))
            self.head=nn.Sequential(nn.Flatten(),nn.Linear(width*4,width*2),nn.GELU(),nn.Dropout(.15),nn.Linear(width*2,1))
        def forward(self,x):return self.head(self.features(x)).squeeze(-1)
    if not isinstance(width,int) or width<8 or width>256:raise ValueError('Network width must be 8–256')
    return WaveNet()
