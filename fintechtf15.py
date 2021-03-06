# -*- coding: utf-8 -*-
"""FinTechTF15.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1n_jmK6hz-GeJdUulFGhkc-8mHN2-EttT
"""

#CURRENT FUNCTION OF THIS NEURAL NETWORK: 
#Full forward prop with full pvm and bias functionality implemented (including writing back to pvm)
#model function structure in place --> THIS VERSION SUPPORTS A FULL BATCH
#reward function implemented and optimizer implemented 

import math
import numpy as np
import h5py
import matplotlib.pyplot as plt
import scipy
from PIL import Image
from scipy import ndimage
import tensorflow as tf
from tensorflow.python.framework import ops
#from cnn_utils import *

# %matplotlib inline
np.random.seed(1)

#FUNTION THAT CREATES A PLACEHOLDER FOR THE PVM_INDEX
def create_placeholders_pvm(n_H0, n_W0, n_C0, n_y, batch_size):
  X_extra = tf.placeholder(tf.float32, shape=(None, n_H0, n_W0, n_C0))
  #X = tf.placeholder(tf.float32, shape=(None, n_H0 - 1, n_W0, n_C0))
  Y = tf.placeholder(tf.float32, shape=(None, n_y))
  #for the portfolio vector memory:
  #MAGIC NUMBER ALERT! ASSUMING ASSET_NUM EQUALS 11 (EXCLUDING CASH BIAS) AND WINDOW SIZE IS 50
  #pvm_chunk = tf.placeholder(tf.float32, shape=(11, 50, 1, 1))
  #actually this may need to be flipped in order for it to be concatenated properly in forward_prop
  pvm_chunk = tf.placeholder(tf.float32, shape=(batch_size, 11, 1, 1))
  #MAGIC NUMBER ALERT! ASSUMING TRAINABLE NUMBER OF PERIODS IS 100 HERE
  #pvm = tf.placeholder(tf.float32,shape=(11, 100))
  return X_extra, Y, pvm_chunk

def initialize_parameters():
  tf.set_random_seed(1)
  #the new filter shape needs to be [1,3,3,2]
  #W1 = tf.get_variable("W1", [4,4,3,8], initializer=tf.contrib.layers.xavier_initializer(seed = 0))
  W1 = tf.get_variable("W1", [1,3,3,2], initializer=tf.contrib.layers.xavier_initializer(seed = 0))
  #W2 = tf.get_variable("W2", [2,2,8,16], initializer=tf.contrib.layers.xavier_initializer(seed = 0))
  W2 = tf.get_variable("W2", [1,48,2,20], initializer=tf.contrib.layers.xavier_initializer(seed = 0))
  #for the 1x1 convolutional layer with the pvm implemented
  W3 = tf.get_variable("W3", [1,1,21,1], initializer=tf.contrib.layers.xavier_initializer(seed = 0))
  parameters = {"W1": W1,
                "W2": W2,
                "W3": W3}
    
  return parameters

#the version of forward propagation that handles the extra information layer
def forward_propagation_extra(X_extra, parameters, pvm, pvm_chunk):
    # Retrieve the parameters from the dictionary "parameters" 
    W1 = parameters['W1']
    W2 = parameters['W2']
    W3 = parameters['W3']
    
    ### START CODE HERE ###
    # CONV2D: stride of 1, padding 'VALID'
    Z1 = tf.nn.conv2d(X,W1, strides = [1,1,1,1], padding = 'VALID')
    print(str(Z1.shape))
    # RELU
    A1 = tf.nn.relu(Z1)
    # CONV2D: filters W2, stride 1, padding 'VALID'
    Z2 = tf.nn.conv2d(A1,W2, strides = [1,1,1,1], padding = 'VALID')
    print(str(Z2.shape))
    # RELU
    A2 = tf.nn.relu(Z2)
    
    #add another feature map to the output of A2--> use the concat function and join along 4th axis
    A2_pvm = tf.concat([A2, pvm_chunk], 3)
    print("shape of the A2_pvm output:")
    print(A2_pvm)
    # one-by-one convolution
    Z3 = tf.nn.conv2d(A2_pvm,W3, strides = [1,1,1,1], padding = 'VALID')
    print("Shape right before softmax")
    print(Z3.shape)
    #add in the cash bias
    cash = np.array(np.ones((batch_size,1,1)))
    Z3_bias = tf.concat([Z3, cash[:,:,:,np.newaxis]], axis=1)
    print("shape after inserting bias:")
    print(Z3_bias.shape)
    # SOFTMAX
    A3 = tf.nn.softmax(Z3_bias, axis=None, name=None)
    print("behold, the shape of A3!")
    print(A3.shape)
    
    
    #feed output back into the pvm
    #pvm[1:batch_size+1, :num_assets,:,:] = A3[:,:num_assets,:,:]

    #return Z3
    return A3

#REWARD FUNCTION
#computes the reward for an individual time period
def compute_reward(X_train, pvm_index, pvm, num_periods):
  #compute the price relative vector for a period
  #input can either be one price tensor, or a batch of price tensors . . . need to design this flexibly . . . will return the cumulative reward for the batch
  #inut also needs to include a chunk of the pvm
  #iterate throught the first layer of the X_train tensor, one column at a time
  total_reward = []
  print("the shape of the first dim of X_train")
  print(X_train.shape[0])
  for period in range(X_train.shape[0]):
    #print(X_train[period].shape)
    price_thisPer = X_train[period, :11, 0, 0]
    price_lastPer = X_train[period, :11, 1, 0] #I think this is correct . . . the adjacent entry in window size is from the directly preceding period
    price_rel = np.divide(price_thisPer, price_lastPer) #this divide function may truncate decimals which would be bad
    #print("price_rel shape:")
    #print(price_rel.shape)
    #add the price relative vector for this period to the broader array of price relative vectors 
    #why do I need this array again??
    #batch_price_rel.append(price_rel)
    #access the portfolio weights for the current period in the batch from the pvm
    port_weight_per = np.squeeze(np.squeeze(pvm[pvm_index,:X_train.shape[1], :, :], axis = 2), axis = 1)
    #access the portfolio weights from the previous period in the pvm
    #squeezing it to make it one-dimensional so that the following multiplication stuff works
    port_weight_prevper = np.squeeze(np.squeeze(pvm[pvm_index - 1,:X_train.shape[1], :, :], axis=2), axis=1)
    #print("port_weight_prevper shape:")
    #print(port_weight_prevper.shape)
    #calculate the weight_prime, which is the prev portfolio weight multiplied by the price_rel vector 
    weight_prime = np.multiply(port_weight_prevper, price_rel)
    #print(weight_prime)
    #find u_dot which is supposedly close to u_t
    u_dot = np.sum(np.subtract(weight_prime, port_weight_per))*.0025 #MAGIC NUMBER! assuming commission value is .0025
    #print("behold the value of u_dot:")
    #print(u_dot)
    #print("                      ")
    #calculate u_t --> a little unclear on exactly how to do this iteratively, will begin by implementing short cut described in the paper
    #actually, I think this basically needs to be a recursive function in which u_t - u_dot < error is the base case
    u_t = find_ut(u_dot, float('-inf'), weight_prime, port_weight_per) #how do we determine a reasonable error (just plugging in .5 for now)???
    print("this is u_t:")
    print(u_t)
    print("                      ")
    #calculate dot-product of price relative and portfolio weights, then take the natural log of it
    logit = np.dot(price_rel, port_weight_prevper)*u_t #wait why is this sometimes negative????? PROBLEM
    #print("this is what I'm logging:")
    #print(logit)
    num_reward = math.log(logit)
    total_reward.append(num_reward)
    #multiply that dot product by u_t
    #return the resulting reward value for the entire batch (should be a real number!) --> first store the sum in a variable that will hold all of the reward values for entire batch
    #will return only the numerator of the reward for this batch --> need to sum over all periods in all batches and divide by total number of batches outside of this function
  
  return np.sum(total_reward)

#SOLVING FOR U_T ITERATIVELY 
#the recursive part --> this is the function that DYNAMICALLY determines ut --> for training the neural nets, might be better to use a fixed k
def find_ut(u_guess, u_guess_prev, weight_prime, weight):
  #if (abs(u_guess_prev) - abs(u_guess)) < error:
  if round(u_guess_prev, 10) == round(u_guess, 10):
    return u_guess
  else:
    #print("the error:")
    #print(abs(round(u_guess_prev, 2)), abs(round(u_guess, 2)))
    old_guess = u_guess
    print("old guess")
    print(old_guess)
    new_guess = mathy_part(u_guess, weight_prime, weight)
    print("new_guess")
    print(new_guess)
    return find_ut(new_guess, old_guess, weight_prime, weight)

#defining a relu function I'll need for the following
#may need to tweak this to work with a vector
def ReLU(array):
  final_vals = []
  for x in array:
    final = abs(x) * (x > 0)
    final_vals.append(final) 
  print("the final_vals array!")
  print(final_vals)
  return final_vals

#the complex mathematics expression
def mathy_part(num, weight_prime, weight):
  #essentially translating equation(14) from the paper
  #MAGIC NUMBER ALERT!! Assuming purchasing commission = selling commission = 0.0025
  c_s = c_p = .0025
  coeff = 1/(1 - c_p*weight[0])
  print("the coeff!")
  print(coeff)
  #rest = 1 - c_p*weight_prime[0] - (c_s + c_p - c_s*c_p)
  #print("rest!")
  #print(rest)
  #print("weight_prime shape")
  #print(weight_prime.shape)
  #print("weight shape")
  #print(weight.shape)
  #print("mult shape")
  #print(np.multiply(num, weight).shape)
  feed_relu = np.subtract(weight_prime, np.multiply(num, weight))
  print("the feed_relu")
  print(feed_relu)
  nonlinear_part = np.sum(ReLU(feed_relu), axis=0) #check that it's summing across correct axis
  rest = 1 - c_p*weight_prime[0] - (c_s + c_p - c_s*c_p)*nonlinear_part #WHY IS THIS SOMETIMES NEGATIVE???? PROBLEM STEMS FROM HERE
  print("the nonlinear part!")
  print(nonlinear_part)
  print("the rest:")
  print(rest)
  complete = coeff*abs(rest) #putting rest into an absolute value function seems like only a TEMPORARY FIX!!!!
  #print("the end of the mathy part!")
  #print(complete)
  print("what I'm feeding back to the recursive function:")
  print(complete)
  return complete

#FOR TESTING THE ABOVE REWARD FUNCTION
#total number of 30-min periods we have access to in our dataset
total_periods = 150
#number of periods used in each price tensor
window_size = 50
#number of periods we'll be able to produce a price tensor for (total periods minus window size)
num_periods = 100
num_assets = 11
num_channels = 3
batch_size = 50

#print("min possible int:")
#print(float('-inf'))

pvm = np.array(np.random.rand(num_periods, num_assets+1, 1, 1))

X_train_extra = np.array(np.random.rand(num_periods, num_assets+1, window_size, num_channels))
#print(X_train_extra)

#clean up the training example and get the pvm index
X_train, pvm_index = shed_info(X_train_extra)
pvm_index = int(round(pvm_index*100))

#print("the value of u_t!")
tot_rew = compute_reward(X_train, pvm_index, pvm, num_periods)
#summed_rew = np.sum(tot_rew)
print(tot_rew)
print("that was the final reward!")

#print(compute_reward(X_train, pvm))

#CREATE_MINIBATCHES FUNCTION

#SHED THE LAYER OF INFORMATION FROM THE MATRIX
def shed_info(X_extra):
    #shed the extra layer of information from X --> should be accessing the last element in the first asset vector
    #we want the very first batch, the last element in the asset column
    #I think PVM index needs to become a placeholder in order to "store" a value that doesn't quite exist yet 
    pvm_index = X_extra[0, X_extra.shape[1] - 1, 0, 0]
    #print(pvm_index)
    #want everything except the last layer of the asset dimension
    X = X_extra[:,:X_extra.shape[1]- 1,:,:]
    return X, pvm_index

#FOR TESTING THE FORWARD PROP ONLY --> the following function feeds in the FinTech data shape through only the forward propagation part of the algorithm
tf.reset_default_graph()

#total number of 30-min periods we have access to in our dataset
total_periods = 150
#number of periods used in each price tensor
window_size = 50
#number of periods we'll be able to produce a price tensor for (total periods minus window size)
num_periods = 100
num_assets = 11
num_channels = 3
batch_size = 50

#Create the pvm where the data is initially loaded
#set up a regular list in python for the pvm
#right now it's an array of random values so we can test that the pipes are moving . . . going to have to change to become array of 1's in top row and zeros in the rest
#pvm = np.array(np.random.rand(num_assets, num_periods))
#flipped for concatenation purposes
#needs to be 4D in order to be concatenated with forward prop outputs
pvm = np.array(np.random.rand(num_periods, num_assets+1, 1, 1))

#this currently assumes that batch size = one training example
X_train = np.array(np.random.rand(num_periods, num_assets, window_size, num_channels))

#this currently assumes that batch size = one training example
#just adding another layer "below" the price box --> this will include info on the period number (will have to figure out how to parse this from original data--> mayber just insert original index here)
X_train_extra = np.array(np.random.rand(num_periods, num_assets + 1, window_size, num_channels))

#TESTING - confirming the shed_info function works as intended
#X_train_extra[0, X_extra.shape[1] - 1, 0, 0] = 1
#print("this is X_train_extra:")
#print(X_train_extra)
#X_shed_test, pindex_test= shed_info(X_train_extra)
#print("Test of getting index:")
#print(pindex_test)

#the following doesn't actually matter:
Y_train = np.array(np.random.rand(1080, 6))

print("shape of X_extra:")
print(X_train_extra.shape)



with tf.Session() as sess:
    #we start by initializing variables and creating placeholders (not feeding in actual values just yet--> only constructing the pipeline)
    #the version without extra info layer:
    #(m, n_H0, n_W0, n_C0) = X_train.shape
    #the version with the extra info layer:
    (m, n_H0, n_W0, n_C0) = X_train_extra.shape
    n_y = Y_train.shape[1] 
    np.random.seed(1)
    #normal:
    #X, Y = create_placeholders(n_H0, n_W0, n_C0, n_y)
    #create the pvm placeholders without the extra info layer: 
    X, Y, pvm_chunk = create_placeholders_pvm(n_H0 - 1, n_W0, n_C0, n_y, batch_size)
    parameters = initialize_parameters()
    #pass in only the normal shape for X
    Z3 = forward_propagation_extra(X, parameters, pvm, pvm_chunk)
    init = tf.global_variables_initializer()
    sess.run(init)
    
    #Now we start figuring out and passing in actual values
      #This will be in the minibatch creating for-loop in the actual model function
    #just going to experiment with feeding in one minibatch for now . . . 
    X_train_extra_mini = X_train_extra[:batch_size,:,:,:]
    print("here's the pvm!")
    print(pvm)
    #Shed info to glean the index value that we need for accessing the pvm
    X_train_extra_shed, pvm_index = shed_info(X_train_extra_mini)
    pvm_index = int(round(pvm_index*100))
    print("here's the pvm index:")
    print(pvm_index)
    #Use this index value to slice pvm in the correct location
    #needs to be 4D in order to work with the feedict and concat function in forward prop
    #pvm_chunk_values = pvm[:,pvm_index:pvm_index+window_size, np.newaxis, np.newaxis]
    #flipped for concatenation
    pvm_chunk_values = pvm[pvm_index:pvm_index+batch_size,:num_assets, :, :]
    #print("these are the pvm_chunk_values!")
    #print(pvm_chunk_values)
    #pass in the appropriate chunk of the pvm to the feedict, and pass in the lean version of X into forward prop
    
    
 
    #the data into Y doesn't actually matter, matrix without extra layer of info
    #deleted this: Y: np.random.randn(2,6)
    forward_out = sess.run(Z3, {X: X_train_extra_shed, pvm_chunk: pvm_chunk_values})
    print("I've fed the data!")
    print("here is the output of softmax for the first training example:")
    print(forward_out[0])
    #rewrite the next part of the pvm --> rewrite for period t+1
    #this will eventually all be in a for-loop in which counter variable i will keep track of minibatch number, so recognize that in final version "i+" will precede the "+1" statement
    pvm[1:batch_size+1, :num_assets,:,:] = forward_out[:,:num_assets,:,:]
    print("the new pvm!")
    print(pvm)
    #print("Z3 = " + str(a))

#MODEL 
def model(X_train, pvm, batch_size, num_periods, total_periods, num_assets, num_channels, window_size, print_reward = True, num_epochs = 1)
    ops.reset_default_graph()                         # to be able to rerun the model without overwriting tf variables
    tf.set_random_seed(1)                             # to keep results consistent (tensorflow seed)
    seed = 3                                          # to keep results consistent (numpy seed)
    (m, n_H0, n_W0, n_C0) = X_train.shape             
    #n_y = Y_train.shape[1]                            
    rewards = []
    
    #create placeholders
    X, Y, pvm_chunk = create_placeholders_pvm(n_H0 - 1, n_W0, n_C0, n_y, batch_size)
    
    #initialize parameters
    parameters = initialize_parameters()
    
    #set up forward propagation pipeline
    Z3 = forward_propagation_extra(X, parameters, pvm, pvm_chunk)
    
    #call the reward function
    #actually it may not be appropriate to call the reward function here . . . better I think to call it after each training example is fed into the NN
    #reward = compute_reward()
    
    #set up the optimizer --> probably needs to be some sort of gradient ascent optimizer?
    
    # Start the session to compute the tensorflow graph
    with tf.Session() as sess:
        
        # Run the initialization
        sess.run(init)
        
        # Do the training loop --> I'll probably set num_epochs to zero
        for epoch in range(num_epochs):
          
            cum_reward = 0.0
            num_minibatches = int(num_periods / batch_size) # number of minibatches of size minibatch_size in the train set
            seed = seed + 1   #why do I need this?
            minibatches = random_mini_batches(X_train, Y_train, minibatch_size, seed) #FIX THE CALL TO THIS MINIBATCH FUNCTION!!!
            
            #set counter for minibatches
            mini_count = 1
            for minibatch in minibatches:
              
              for X_train_extra_example in minibatch:
                #clean up the training example and get the pvm index
                X_train_extra_shed, pvm_index = shed_info(X_train_extra_example)
                pvm_index = int(round(pvm_index*100))
                #get the appropriate pvm_chunk for the individual training example
                pvm_chunk_values = pvm[pvm_index,:num_assets, :, :]
                
                #feed data into forward-prop only, get the output, and write that into the pvm in the next time-period slot
                forward_out = sess.run(Z3, {X: X_train_extra_shed, pvm_chunk: pvm_chunk_values})
                pvm[pvm_index+1, :num_assets,:,:] = forward_out[:,:num_assets,:,:]
                
                #feed the output of forward prop into the optimizer's feed-dict 
                # Run the session to execute the optimizer and the reward, the feedict should contain a minibatch for (Z3).
                #change of plans! call the reward function here . . . feed in the X_train minibatch into reward function here, feed output of reward into optimizer
                
                reward_batch = compute_reward(X_train_extra_shed, pvm_index, pvm, num_periods)
                cum_reward += reward_batch #we want to sum over the total number of trainable periods
                reward_batch_fin = cum_reward / (mini_count*batch_size) #divide the numerator of the reward by the number of periods the network has seen
                
                #maximizing the reward is apparently the same thing as minimizing the opposite of the reward . . . 
                neg_reward = reward_batch_fin * -1
                
                # may need to change so that forward_out is fed into whatever the optimizer or reward function is called, not Z3 (i think this will be confusing)
                _ , temp_neg_reward = sess.run([optimizer, reward], feed_dict = {Z3:forward_out})
                #calculate average reward from this minibatch
                
              #update the counter
              mini_count = mini_count + 1
            
            #I'LL NEED TO FIX THIS STUFF TO MAKE IT LOOK PRETTY AS IT LOGS REWARD
            # Print the reward every minibatch
            #if print_reward == True and mini_count % 5 == 0:
                #print ("Cost after minibatch %i: %f" % (mini_count, reward_cum))
            #if print_reward == True and mini_count % 1 == 0:
                #rewards.append(reward_cum)
        
        #print the final reward value --> after going though all of the trainable periods
        #final_reward = reward_cum / num_periods
        
        print("the final reward!")
        print(reward_cum)
        
        # plot the reward
        plt.plot(np.squeeze(rewards))
        plt.ylabel('reward')
        plt.xlabel('iterations (per tens)')
        plt.title("Learning rate =" + str(learning_rate))
        plt.show()
    
        #actually I think I'll only need to return the parameters, nothing else
        return train_accuracy, test_accuracy, parameters
