from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

from urllib.request import urlretrieve
import tarfile

import pickle
import numpy as np
import random
from sklearn.model_selection import train_test_split

DIR_BINARIES='./cifar-10-batches-py/'

def unpickle(filename):
    f = open(filename, 'rb')
    dic = pickle.load(f)
    f.close()
    return dic

def batch_to_bc01(batch):
    ''' Converts CIFAR sample to bc01 tensor'''
    return batch.reshape([-1, 1, 1, 200])

def batch_to_b01c(batch):
    ''' Converts CIFAR sample to b01c tensor'''
    return batch_to_bc01(batch).transpose(0,2,3,1)

def labels_to_one_hot(labels):
    ''' Converts list of integers to numpy 2D array with one-hot encoding'''
    N = len(labels)
    one_hot_labels = np.zeros([N, 3], dtype=int)
    one_hot_labels[np.arange(N), labels] = 1
    return one_hot_labels

class CIFAR10:
    
    def __init__(self, batch_size=100, validation_proportion=0.1, augment_data=False, file = 'database.csv'):
        
        #Charge data:
        file = open(file,'r')
        train_data = []
        train_labels = []
        test_data = []
        test_labels = []
        dict = {}
        #file.readline()
        for line in file:
            line_data = []
            data = line.split(',')
            
            subclass = data[-1]
            data[0] = data[0].strip('"')
            data[len(data)-2] = data[len(data)-2].strip('"')
            data = np.array(data[0:len(data)-1], dtype = np.float64)
       
            for x in data:
                line_data.append(float(x))
            dict[subclass] = dict.get(subclass,[])+line_data
        labels = list(dict.keys())
        for key in dict.keys():
            a = random.sample(range(int(len(dict[key])/200)),int(len(dict[key])/200*.1))
            for value in range(int(len(dict[key])/200)):
                if value in a:
                    test_labels = test_labels + [labels.index(key)]
                    test_data.append(dict[key][200*value:200*(value+1)])
                else:
                    train_data.append(dict[key][200*value:200*(value+1)])
                    train_labels = train_labels + [labels.index(key)]

        self.train_data = np.asarray(train_data,dtype=np.float32)
        self.train_labels = np.asarray(train_labels,dtype=np.int32)

        self.test_data = np.asarray(test_data, dtype=np.float32)
        self.test_labels = np.asarray(test_labels, dtype = np.int32)

        
        # Training and Test set
        #self.train_data,self.train_labels,self.test_data,self.test_labels = self.import_data('database3.csv')
                
        # Validation set
        assert validation_proportion > 0. and validation_proportion < 1.
        self.train_data, self.validation_data, self.train_labels, self.validation_labels = train_test_split(
            self.train_data, self.train_labels, test_size=validation_proportion, random_state=1)
                
        # Normalize data
        mean = (self.train_data.mean(axis=0) + self.test_data.mean(axis = 0))/2
        std = (self.train_data.std(axis=0) + self.test_data.std(axis=0))/2
        self.train_data = (self.train_data-mean)/std
        self.validation_data = (self.validation_data-mean)/std
        self.test_data = (self.test_data-mean)/std

        # Converting to b01c and one-hot encoding
        self.train_data = batch_to_b01c(self.train_data)
        self.validation_data = batch_to_b01c(self.validation_data)
        self.test_data = batch_to_b01c(self.test_data)
        self.train_labels = labels_to_one_hot(self.train_labels)
        self.validation_labels = labels_to_one_hot(self.validation_labels)
        self.test_labels = labels_to_one_hot(self.test_labels)

        np.random.seed(seed=1)
        self.augment_data = augment_data
            
        # Batching & epochs
        self.batch_size = batch_size
        self.n_batches = len(self.train_labels)//self.batch_size
        self.current_batch = 0
        self.current_epoch = 0
        
    def import_data(self,file):
               
        #Normalize data:
        #mean = train_data.mean(axis=0)
        #std = train_data.std(axis=0)
        #train_data = (train_data-mean)/std
        #validate_data = (validate_data-mean)/std
        #test_data = (test_data-mean)/std

        #train_data.reshape([-1,1,200,1])
        #validate_data.reshape([-1,1,200,1])
        #test_data.reshape([-1,1,200,1])

        return labels,train_data,train_labels,test_data,test_labels
        
    def nextBatch(self):
        ''' Returns a tuple with batch and batch index '''
        start_idx = self.current_batch*self.batch_size
        end_idx = start_idx + self.batch_size 
        batch_data = self.train_data[start_idx:end_idx]
        batch_labels = self.train_labels[start_idx:end_idx]
        batch_idx = self.current_batch

        if self.augment_data:
            if np.random.randint(0, 2) == 0:
                batch_data = batch_data[:, :, ::-1, :]
            batch_data += np.random.randn(self.batch_size, 1, 1, 3)*0.05
            
        # Update self.current_batch and self.current_epoch
        self.current_batch = (self.current_batch+1)%self.n_batches
        if self.current_batch != batch_idx+1:
            self.current_epoch += 1

            # shuffle training data
            new_order = np.random.permutation(np.arange(len(self.train_labels)))
            self.train_data = self.train_data[new_order]
            self.train_labels = self.train_labels[new_order]
            
        return ((batch_data, batch_labels), batch_idx)
    
    def getEpoch(self):
        return self.current_epoch

    # TODO: refactor getTestSet and getValidationSet to avoid code replication
    def getTestSet(self, asBatches=False):
        if asBatches:
            batches = []
            for i in range(len(self.test_labels)//self.batch_size):
                start_idx = i*self.batch_size
                end_idx = start_idx + self.batch_size 
                batch_data = self.test_data[start_idx:end_idx]
                batch_labels = self.test_labels[start_idx:end_idx]
        
                batches.append((batch_data, batch_labels))
            return batches
        else:
            return (self.test_data, self.test_labels)

    def getValidationSet(self, asBatches=False):
        if asBatches:
            batches = []
            for i in range(len(self.validation_labels)//self.batch_size):
                start_idx = i*self.batch_size
                end_idx = start_idx + self.batch_size 
                batch_data = self.validation_data[start_idx:end_idx]
                batch_labels = self.validation_labels[start_idx:end_idx]

                batches.append((batch_data, batch_labels))
            return batches
        else:
            return (self.validation_data, self.validation_labels)

    def reset(self):
        self.current_batch = 0
        self.current_epoch = 0
        
if __name__=='__main__':
    cifar10 = CIFAR10(batch_size=1000)
    while cifar10.getEpoch()<2:
        batch, batch_idx = cifar10.nextBatch()
        print(batch_idx, cifar10.n_batches, cifar10.getEpoch())
    batches = cifar10.getTestSet(asBatches=True)
    print(len(batches))
    data, labels = cifar10.getValidationSet()
    print(labels.sum(axis=0))
    data, labels = cifar10.getTestSet()
    print(labels.sum(axis=0))
