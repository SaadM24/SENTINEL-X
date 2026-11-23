"""Optional torch backend. Serialized networks store CPU tensors."""
import numpy as np


class TorchNet:
    def __init__(self, reconstruct, epochs, batch, seed):
        self.reconstruct, self.epochs, self.batch, self.seed = reconstruct, epochs, batch, seed

    def fit(self, x, y):
        import torch
        from torch import nn
        torch.manual_seed(self.seed)
        dims = [x.shape[1], 16, 3, 16, x.shape[1]] if self.reconstruct else [x.shape[1], 32, 16, 1]
        layers = []
        for a, b in zip(dims[:-1], dims[1:]):
            layers.extend((nn.Linear(a, b), nn.ReLU()))
        self.net = nn.Sequential(*layers[:-1]).to('cuda')
        optimizer = torch.optim.Adam(self.net.parameters())
        cpu_x = torch.as_tensor(x)
        cpu_y = cpu_x if self.reconstruct else torch.as_tensor(y[:, None], dtype=torch.float32)
        criterion = nn.MSELoss() if self.reconstruct else nn.BCEWithLogitsLoss()
        self.net.train()
        for _ in range(self.epochs):
            for ids in torch.randperm(len(x)).split(self.batch):
                optimizer.zero_grad()
                pred = self.net(cpu_x[ids].cuda())
                loss = criterion(pred, cpu_y[ids].cuda())
                loss.backward()
                optimizer.step()
        self.net = self.net.cpu().eval()
        return self

    def predict(self, x):
        import torch
        with torch.no_grad():
            return np.concatenate([self.net(torch.as_tensor(x[i:i+self.batch])).numpy()
                                   for i in range(0, len(x), self.batch)])

    def predict_proba(self, x):
        from scipy.special import expit
        p = expit(self.predict(x).ravel())
        return np.column_stack((1-p, p))
