import os
import torch
import numpy as np
import pickle
from torch_geometric.data import Data, Dataset

class RNAPDBDataset(Dataset):
    backbone_atoms = ['P', 'O5\'', 'C5\'', 'C4\'', 'C3\'', 'O3\'']
    
    def __init__(self,
                 path: str,
                 name: str,
                 file_extension: str='.pkl',
                 mode: str='backbone'
                 ):
        super(RNAPDBDataset, self).__init__(path)
        self.path = os.path.join(path, name)
        self.files = sorted(os.listdir(self.path))
        self.files = os.listdir(self.path)
        self.files = [f for f in self.files if f.endswith(file_extension)]
        self.to_tensor = torch.tensor
        if mode not in ['backbone', 'all', 'coarse-grain']:
            raise ValueError(f"Invalid mode: {mode}")
        self.mode = mode

    def len(self):
        return len(self.files)

    def get(self, idx):
        data_x, batch, name = self.get_raw_sample(idx)
        if self.transform:
            torsions = self.transform(torsions)
        data = Data(
            x=data_x
        )
        return data, name

    def get_raw_sample(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()
        file = self.files[idx]
        path = os.path.join(self.path, file)
        sample = self.load_pickle(path)
        atoms_types = self.to_tensor(sample['atoms']).unsqueeze(1).float()
        atoms_pos = self.to_tensor(sample['pos']).float()
        atoms_pos_mean = atoms_pos.mean(dim=0)
        atoms_pos -= atoms_pos_mean # Center around point (0,0,0)
        atoms_pos /= 10
        indicator = self.to_tensor(sample['indicator'])
        if self.mode == 'backbone':
            atoms_pos, atoms_types = self.backbone_only(atoms_pos, atoms_types, sample['symbols'])
        elif self.mode == 'coarse-grain':
            raise NotImplementedError
        
        name = sample['name'].replace('.pkl', '')
        # convert atom_types to one-hot encoding (C, O, N, P)
        atoms_types = torch.nn.functional.one_hot(atoms_types.to(torch.int64), num_classes=4).float()
        atoms_types = atoms_types.squeeze(1)
        data_x = torch.cat((atoms_pos, atoms_types), dim=1)
        return data_x, indicator, name

    def backbone_only(self, atom_pos, atom_types, atom_symbols):
        mask = [True if atom in self.backbone_atoms else False for atom in atom_symbols]
        return atom_pos[mask], atom_types[mask]

    @property
    def raw_file_names(self):
        return self.files

    @property
    def processed_file_names(self):
        return self.files

    def load_pickle(self, path):
        with open(path, 'rb') as f:
            return pickle.load(f)