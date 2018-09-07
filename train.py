# coding: utf-8

# A Convolutional Network implementation example using TensorFlow library.
# This example is using the MNIST database of handwritten digits
# (http://yann.lecun.com/exdb/mnist/)
# 
# Author: Aymeric Damien
# Project: https://github.com/aymericdamien/TensorFlow-Examples/

import os
from argparse import ArgumentParser
import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data
import shutil

def build_parser():
    parser = ArgumentParser()
    
    parser.add_argument('--learning_rate', type=float,
                        dest='learning_rate', help='Learning rate',
                        default=0.001)
    
    parser.add_argument('--training_iters', type=int,
                        dest='training_iters', help='Number of training iterations',
                        default=200000)
    
    parser.add_argument('--batch_size', type=int,
                        dest='batch_size', help='Batch size',
                        default=128)
    
    parser.add_argument('--display_step', type=int,
                        dest='display_step', help='Print metrics every display_step',
                        default=10)
    
    parser.add_argument('--dropout', type=float,
                        dest='dropout', help='Dropout',
                        default=0.75)
    
    parser.add_argument('--mnist_data', type=str,
                        dest='mnist_data', help='Path of MNIST train and test dataset',
                        default='/floyd/input/mnist')
    
    return parser

def check_opts(opts):
    assert os.path.exists(opts.mnist_data), "MNIST data not found at {}".format(opts.mnist_data)
    
    assert opts.learning_rate >= 0, "Please provide a positive learning_rate"
    assert opts.training_iters > 0
    assert opts.batch_size > 0
    assert opts.display_step > 0
    assert (opts.dropout >= 0 and opts.dropout <= 1.0), "dropout should be between 0.0 and 1.0"

# Parse command line arguments
parser = build_parser()
options = parser.parse_args()
check_opts(options)


# Check if GPU is available
if tf.test.is_gpu_available():
    print("GPU available.")
else:
    print("No GPU found... Defaulting to CPU.")

# Read MNIST data from local dataset
mnist = input_data.read_data_sets(options.mnist_data, one_hot=True)

# Network Parameters
n_input = 784 # MNIST data input (img shape: 28*28)
n_classes = 10 # MNIST total classes (0-9 digits)

logs_path = '/output/tensorflow_logs/'

# tf Graph input
x = tf.placeholder(tf.float32, [None, n_input], name="x")
y = tf.placeholder(tf.float32, [None, n_classes], name="y")
keep_prob = tf.placeholder(tf.float32, name="keep_prob") #dropout (keep probability)

# Create some wrappers for simplicity
def conv2d(x, W, b, strides=1):
    # Conv2D wrapper, with bias and relu activation
    x = tf.nn.conv2d(x, W, strides=[1, strides, strides, 1], padding='SAME')
    x = tf.nn.bias_add(x, b)
    return tf.nn.relu(x)


def maxpool2d(x, k=2):
    # MaxPool2D wrapper
    return tf.nn.max_pool(x, ksize=[1, k, k, 1], strides=[1, k, k, 1],
                          padding='SAME')


# Create model
def conv_net(x, weights, biases, dropout):
    # Reshape input picture
    x = tf.reshape(x, shape=[-1, 28, 28, 1])

    # Convolution Layer
    conv1 = conv2d(x, weights['wc1'], biases['bc1'])
    # Max Pooling (down-sampling)
    conv1 = maxpool2d(conv1, k=2)

    # Convolution Layer
    conv2 = conv2d(conv1, weights['wc2'], biases['bc2'])
    # Max Pooling (down-sampling)
    conv2 = maxpool2d(conv2, k=2)

    # Fully connected layer
    # Reshape conv2 output to fit fully connected layer input
    fc1 = tf.reshape(conv2, [-1, weights['wd1'].get_shape().as_list()[0]])
    fc1 = tf.add(tf.matmul(fc1, weights['wd1']), biases['bd1'])
    fc1 = tf.nn.relu(fc1)
    # Apply Dropout
    fc1 = tf.nn.dropout(fc1, dropout)

    # Output, class prediction
    out = tf.add(tf.matmul(fc1, weights['out']), biases['out'])
    return out


# Store layers weight & bias
weights = {
    # 5x5 conv, 1 input, 32 outputs
    'wc1': tf.Variable(tf.random_normal([5, 5, 1, 32])),
    # 5x5 conv, 32 inputs, 64 outputs
    'wc2': tf.Variable(tf.random_normal([5, 5, 32, 64])),
    # fully connected, 7*7*64 inputs, 1024 outputs
    'wd1': tf.Variable(tf.random_normal([7*7*64, 1024])),
    # 1024 inputs, 10 outputs (class prediction)
    'out': tf.Variable(tf.random_normal([1024, n_classes]))
}

biases = {
    'bc1': tf.Variable(tf.random_normal([32])),
    'bc2': tf.Variable(tf.random_normal([64])),
    'bd1': tf.Variable(tf.random_normal([1024])),
    'out': tf.Variable(tf.random_normal([n_classes]))
}

# Construct model
pred = conv_net(x, weights, biases, keep_prob)

# Define loss and optimizer
cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=pred, labels=y))
optimizer = tf.train.AdamOptimizer(learning_rate=options.learning_rate).minimize(cost)

# Evaluate model
correct_pred = tf.equal(tf.argmax(pred, 1), tf.argmax(y, 1))
accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32), name="accuracy")

# Create a summary to monitor cost tensor
tf.summary.scalar("loss", cost)
# Create a summary to monitor accuracy tensor
tf.summary.scalar("accuracy", accuracy)
# Merge all summaries into a single op
merged_summary_op = tf.summary.merge_all()

# Delete ./model dir if exists to avoid SavedModelBuilder error
if os.path.exists('./model'):
    shutil.rmtree('./model', ignore_errors=True)

# Initializing the variables
init = tf.global_variables_initializer()
builder = tf.saved_model.builder.SavedModelBuilder("./model")


# Launch the graph
with tf.Session() as sess:
    sess.run(init)

    # op to write logs to Tensorboard
    summary_writer = tf.summary.FileWriter(logs_path, graph=tf.get_default_graph())

    step = 1
    # Keep training until reach max iterations
    while step * options.batch_size < options.training_iters:
        batch_x, batch_y = mnist.train.next_batch(options.batch_size)
        # Run optimization op (backprop), cost op (to get loss value) and summary nodes
        _, c, summary = sess.run([optimizer, cost, merged_summary_op], 
                                    feed_dict={x: batch_x, y: batch_y, keep_prob: options.dropout})

        # Write logs at every iteration
        summary_writer.add_summary(summary, step * options.batch_size)

        if step % options.display_step == 0:    
            # Calculate batch loss and accuracy
            loss, acc = sess.run([cost, accuracy], feed_dict={x: batch_x,
                                                              y: batch_y,
                                                              keep_prob: 1.})
            # print("Iter " + str(step*options.batch_size) + ", Minibatch Loss= " + \
            #      "{:.6f}".format(loss) + ", Training Accuracy= " +                   "{:.5f}".format(acc))
            print('{{"metric": "Minibatch loss", "value": {:.6f}}}'.format(loss))
            print('{{"metric": "Training accuracy", "value": {:.5f}}}'.format(acc))
        step += 1
    print("Optimization Finished!")

    builder.add_meta_graph_and_variables(sess, ["EVALUATING"])

builder.save()


with tf.Session() as sess:
    sess.run(init)
    
    # Calculate accuracy for 256 mnist test images
    print("Testing Accuracy:", sess.run(accuracy, feed_dict={x: mnist.test.images[:256], y: mnist.test.labels[:256], keep_prob: 1.}))

