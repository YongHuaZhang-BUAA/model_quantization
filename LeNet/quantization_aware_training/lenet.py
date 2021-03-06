import tensorflow as tf
import tensorflow.contrib.slim as slim
import config as cfg


class Lenet:
    def __init__(self, is_train=True):
        self.raw_input_image = tf.placeholder(tf.float32, [None, 784], "inputs")
        self.input_images = tf.reshape(self.raw_input_image, [-1, 28, 28, 1])
        self.raw_input_label = tf.placeholder("float", [None, 10], "labels")
        self.input_labels = tf.cast(self.raw_input_label, tf.int32)
        self.dropout = cfg.KEEP_PROB
        self.is_train = is_train

        with tf.variable_scope("Lenet") as scope:
            self.train_digits = self.construct_net(True)
            scope.reuse_variables()
            self.pred_digits = self.construct_net(False)

        self.loss = slim.losses.softmax_cross_entropy(self.train_digits, self.input_labels)

        # 获取当前的计算图，用于后续的量化
        self.g = tf.get_default_graph()

        if self.is_train:
            # 在损失函数之后，优化器定义之前，在这里会自动选择计算图中的一些operation和activation做伪量化
            tf.contrib.quantize.create_training_graph(self.g, 80000)
            self.lr = cfg.LEARNING_RATE
            self.train_op = tf.train.AdamOptimizer(self.lr).minimize(self.loss)
        else:
            # 用于预测时，将之前训练时构造的伪量化的operation和activation实际量化，用于后续的推断
            tf.contrib.quantize.create_eval_graph(self.g)

        self.prediction = tf.argmax(self.pred_digits, 1, name="predictions")
        self.correct_prediction = tf.equal(tf.argmax(self.pred_digits, 1), tf.argmax(self.input_labels, 1))
        self.train_accuracy = tf.reduce_mean(tf.cast(self.correct_prediction, "float"))

    def construct_net(self, is_trained=True):
        with slim.arg_scope([slim.conv2d], padding='VALID',
                            weights_initializer=tf.truncated_normal_initializer(stddev=0.01),
                            weights_regularizer=slim.l2_regularizer(0.0005)):
            net = slim.conv2d(self.input_images, 6, [5, 5], 1, padding='SAME', scope='conv1')
            net = slim.max_pool2d(net, [2, 2], scope='pool2')
            net = slim.conv2d(net, 16, [5, 5], 1, scope='conv3')
            net = slim.max_pool2d(net, [2, 2], scope='pool4')
            net = slim.conv2d(net, 120, [5, 5], 1, scope='conv5')
            net = slim.flatten(net, scope='flat6')
            net = slim.fully_connected(net, 84, scope='fc7')
            net = slim.dropout(net, self.dropout, is_training=is_trained, scope='dropout8')
            digits = slim.fully_connected(net, 10, scope='fc9')
        return digits
