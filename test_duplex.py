import numpy as np
import matplotlib.pyplot as plt
import custom_layers, get_data
import keras
from keras import Model, Input
from keras.layers import Dense
from keras import layers
from keras.optimizers import SGD, Adam
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.manifold import TSNE
from sklearn import metrics
from scipy.optimize import linear_sum_assignment as linear_assignment
import tensorflow as tf
import random, math
import winsound
import datetime

from keras.utils import plot_model
from IPython.display import Image

frequency = 2500  # Set Frequency To 2500 Hertz
duration = 1000  # Set Duration To 1000 ms == 1 second

print(tf.__version__)
print(tf.executing_eagerly())

np.random.seed(0)

positive_classes = [0, 1, 2, 3, 4, 5, 6, 8, 9]
negative_classes = [7]

classes = positive_classes.copy()
classes.extend(negative_classes)

num_classes = len(classes)
num_pos_classes = len(positive_classes)

use_convolutional = False
perc_labeled = 0.1
batch_size_labeled = 256



def get_dataset():
    ds_labeled, y_labeled, ds_unlabeled, y_unlabeled, _, _ = get_data.get_data(positive_classes,negative_classes,
                                                                               perc_labeled, flatten_data=not use_convolutional, perc_size=1)

    # esigenze per la loss
    if len(ds_labeled) % batch_size_labeled != 0:
        ds_labeled = ds_labeled[:-(len(ds_labeled) % batch_size_labeled)]
        y_labeled = y_labeled[:-(len(y_labeled) % batch_size_labeled)]

    # esigenze per la loss
    if len(ds_unlabeled) % batch_size_labeled != 0:
        ds_unlabeled = ds_unlabeled[:-(len(ds_unlabeled) % batch_size_labeled)]
        y_unlabeled = y_unlabeled[:-(len(y_unlabeled) % batch_size_labeled)]

    return ds_labeled, y_labeled, ds_unlabeled, y_unlabeled


def plot_2d(x, y, y_true, centroids, show_fig=False):

    label_color = [index for index in classes]
    cmap = plt.cm.get_cmap("jet", 256)

    # get data in 2D
    x_embedded = TSNE(n_components=2, verbose=1).fit_transform(np.concatenate((x, centroids), axis=0))
    vis_x = x_embedded[:-len(centroids), 0]
    vis_y = x_embedded[:-len(centroids), 1]

    fig, (ax1, ax2) = plt.subplots(1, 2)
    fig.suptitle('Predicted vs True')

    # predicted
    ax1.scatter(vis_x, vis_y, c=y, linewidths=0.2, marker=".", cmap=cmap)
    ax1.scatter(x_embedded[-len(centroids):, 0], x_embedded[-len(centroids):, 1], marker="X", alpha=1, c=label_color,
                edgecolors="#FFFFFF", linewidths=1, cmap=cmap)

    # true
    ax2.scatter(vis_x, vis_y, c=y_true, linewidths=0.2, marker=".", cmap=cmap)
    ax2.scatter(x_embedded[-len(centroids):, 0], x_embedded[-len(centroids):, 1], marker="X", alpha=1, c=label_color,
                edgecolors="#FFFFFF", linewidths=1, cmap=cmap)

    # color bar
    norm = plt.cm.colors.Normalize(vmax=num_classes - 1, vmin=0)
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax1)

    plt.savefig('images/clusters_tsne_' + datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + '.png')
    if show_fig:
        plt.show()


def create_autoencoder(dims, act='relu', init='glorot_uniform'):

    if use_convolutional:
        input_data = Input(shape=dims[0], name='input')

        # ENCODER
        e = layers.Conv2D(32, (3, 3), activation='relu')(input_data)
        e = layers.MaxPooling2D((2, 2))(e)
        e = layers.Conv2D(64, (3, 3), activation='relu')(e)
        e = layers.MaxPooling2D((2, 2))(e)
        e = layers.Conv2D(64, (3, 3), activation='relu')(e)
        l = layers.Flatten()(e)
        l = layers.Dense(49, activation=act)(l)
        l = layers.Dense(10, kernel_initializer=init)(l)

        encoder_model = keras.Model(input_data, l)

        # DECODER
        d = layers.Dense(49, activation=act)(l)
        d = layers.Reshape((7, 7, 1))(d)
        d = layers.Conv2DTranspose(64, (3, 3), strides=2, activation='relu', padding='same')(d)
        d = layers.BatchNormalization()(d)
        d = layers.Conv2DTranspose(64, (3, 3), strides=2, activation='relu', padding='same')(d)
        d = layers.BatchNormalization()(d)
        d = layers.Conv2DTranspose(32, (3, 3), activation='relu', padding='same')(d)
        d = layers.Conv2D(1, (3, 3), activation='sigmoid', padding='same')(d)

        autoencoder_model = keras.Model(input_data, d)
    else:
        n_stacks = len(dims) - 1
        input_data = Input(shape=dims[0], name='input')

        x = input_data

        # internal layers of encoder
        for i in range(n_stacks - 1):
            x = Dense(dims[i + 1], activation=act, kernel_initializer=init, name='encoder_%d' % i)(x)
        # latent hidden layer
        encoded = Dense(dims[-1], kernel_initializer=init, name='encoder_%d' % (n_stacks - 1))(x)
        x = encoded
        # internal layers of decoder
        for i in range(n_stacks - 1, 0, -1):
            x = Dense(dims[i], activation=act, kernel_initializer=init, name='decoder_%d' % i)(x)
        # decoder output
        x = Dense(dims[0][0], kernel_initializer=init, name='decoder_0')(x)

        decoded = x

        autoencoder_model = Model(inputs=input_data, outputs=decoded, name='autoencoder')
        encoder_model = Model(inputs=input_data, outputs=encoded, name='encoder')

    return autoencoder_model, encoder_model


def print_accuracy(x, y, centroids, label, model, encoder):

    # mapping cluster/true
    mapping_indexes = dict()
    for y_class in classes:
        only_x_class, _ = get_data.filter_ds(x, y, [y_class])
        only_x_class = encoder.predict(only_x_class)

        centroid_class = np.mean(only_x_class, axis=0)

        index_nearest_centroid = np.argmin([np.linalg.norm(centroid - centroid_class) for centroid in centroids])

        mapping_indexes[index_nearest_centroid] = y_class

    print(mapping_indexes)

    y_pred, _ = model.predict(x, verbose=0)
    y_pred = y_pred.argmax(1)

    # altro indice di accuratezza basato sulla composizione dei cluster
    acc = 0

    for y_class in classes:
        y_class_predicted, _ = get_data.filter_ds(y_pred, y, [y_class])

        y_pred_count_by_class = dict()
        max_count_for_class = 0
        for yy_class in range(num_classes):
            count = sum([1 for y in y_class_predicted if y == yy_class])
            if count > len(y_class_predicted) / 100:
                y_pred_count_by_class[yy_class] = count
            if count > max_count_for_class:
                max_count_for_class = count

        print("\nClass value:", y_class)
        print("Class composition:", y_pred_count_by_class)

        # per un cluster, il sottogruppo di esempi piu grande (in base all'etichetta reale) è considerato come positivo
        acc += max_count_for_class

    acc = acc * 100 / len(y)
    print("Accuracy (cluster) for " + label + ":" + str(acc))


    # si ottengono i valori delle classi
    y_pred = [mapping_indexes[i] if i in mapping_indexes else -1 for i in y_pred]

    acc = 0
    for i in range(len(y)):
        if y[i] == y_pred[i]:
            acc += 1

    acc = acc * 100 / len(y)
    print("Accuracy (centroid) for " + label + ":" + str(acc))

    return y_pred


def cluster_acc(y_true, y_pred):
    """
    Calculate clustering accuracy. Require scikit-learn installed
    # Arguments
        y: true labels, numpy.array with shape `(n_samples,)`
        y_pred: predicted labels, numpy.array with shape `(n_samples,)`
    # Return
        accuracy, in [0,1]
    """
    y_true = y_true.astype(np.int64)
    assert y_pred.size == y_true.size
    D = max(y_pred.max(), y_true.max()) + 1
    w = np.zeros((D, D), dtype=np.int64)
    for i in range(y_pred.size):
        w[y_pred[i], y_true[i]] += 1

    ind = linear_assignment(w.max() - w)
    return sum([w[i, j] for i, j in enumerate(ind)]) * 1.0 / y_pred.size


def run_duplex(model_unlabeled, model_labeled, ds_labeled, y_labeled, ds_unlabeled, y_unlabeled, y_pred_last,
               mse_weight=1):

    batch_size_unlabeled = 256
    maxiter = 10000
    miniter = 200
    tol = 0.005  # tolerance threshold to stop training

    epochs_labeled = 1
    #labeled_interval = int((len(ds_unlabeled) / batch_size_unlabeled) * epochs_labeled)  #every N epochs do labeled training
    labeled_interval = int((1 / perc_labeled) * (batch_size_labeled / batch_size_unlabeled))
    print("labeled_interval", labeled_interval)

    #update_interval = 140
    #update_interval = labeled_interval

    # compile models
    model_unlabeled.compile(loss=['kld', 'mse'],
                            loss_weights=[gamma_kld, mse_weight], optimizer=Adam())
    model_labeled.compile(loss=[custom_layers.get_my_argmax_loss(batch_size_labeled, ce_function_type), 'mse'],
                          loss_weights=[gamma_ce, mse_weight], optimizer=Adam())

    # bisogna avere anche le etichette per i negativi
    temp_y_for_model_labeled = keras.utils.to_categorical(y_labeled)
    y_for_model_labeled = np.empty((temp_y_for_model_labeled.shape[0], num_classes))

    rm_zeros = np.zeros(num_classes - temp_y_for_model_labeled.shape[1])
    for i, el in enumerate(temp_y_for_model_labeled):
        y_for_model_labeled[i] = np.concatenate((el, rm_zeros), axis=0)

    loss = -1
    index_unlabeled = 0
    index_labeled = 0

    for ite in range(int(maxiter)):

        # labeled training
        if ite % labeled_interval == 0:
            if (index_labeled + 1) * batch_size_labeled > ds_labeled.shape[0]:
                #loss = model_labeled.train_on_batch(x=ds_labeled[index_labeled * batch_size_labeled::],
                #                                      y=[y_for_model_labeled[index_labeled * batch_size_labeled::],
                #                                         ds_labeled[index_labeled * batch_size_labeled::]])
                index_labeled = 0

            loss = model_labeled.train_on_batch(
                x=ds_labeled[index_labeled * batch_size_labeled:(index_labeled + 1) * batch_size_labeled],
                y=[y_for_model_labeled[index_labeled * batch_size_labeled:(index_labeled + 1) * batch_size_labeled],
                   ds_labeled[index_labeled * batch_size_labeled:(index_labeled + 1) * batch_size_labeled]])
            index_labeled += 1

            # print('Iter', ite, "Labeled loss is", loss)

            #model_labeled.fit(ds_labeled, [y_for_model_labeled, ds_labeled], verbose=0, epochs=epochs_labeled, batch_size=batch_size_labeled, shuffle=True)

        # update target probability
        if ite % update_interval == 0:
            q, _ = model_unlabeled.predict(ds_unlabeled, verbose=0)
            p = custom_layers.target_distribution(q)  # update the auxiliary target distribution p

            # evaluate the clustering performance
            y_pred = q.argmax(1)
            if y_unlabeled is not None:
                acc = np.round(cluster_acc(y_unlabeled, y_pred), 5)
                nmi = np.round(metrics.normalized_mutual_info_score(y_unlabeled, y_pred), 5)
                ari = np.round(metrics.adjusted_rand_score(y_unlabeled, y_pred), 5)
                loss = np.round(loss, 5)

                print('Iter', ite, ', nmi', nmi, ', ari', ari, '; loss=', loss)

            # check stop criterion
            delta_label = np.sum(y_pred != y_pred_last).astype(np.float32) / y_pred.shape[0]
            y_pred_last = y_pred
            if ite > miniter and delta_label < tol:
                print('delta_label ', delta_label, '< tol ', tol)
                'Reached tolerance threshold. Stopping training.'
                break

        # unlabeled train on batch
        if (index_unlabeled + 1) * batch_size_unlabeled > ds_unlabeled.shape[0]:
            loss = model_unlabeled.train_on_batch(x=ds_unlabeled[index_unlabeled * batch_size_unlabeled::],
                                                  y=[p[index_unlabeled * batch_size_unlabeled::],
                                                     ds_unlabeled[index_unlabeled * batch_size_unlabeled::]])
            index_unlabeled = 0
        else:
            loss = model_unlabeled.train_on_batch(x=ds_unlabeled[index_unlabeled * batch_size_unlabeled:(index_unlabeled + 1) * batch_size_unlabeled],
                                             y=[p[index_unlabeled * batch_size_unlabeled:(index_unlabeled + 1) * batch_size_unlabeled],
                                                ds_unlabeled[index_unlabeled * batch_size_unlabeled:(index_unlabeled + 1) * batch_size_unlabeled]])
            index_unlabeled += 1

        #print('Iter', ite, "UNlabeled loss is", loss)


def main():
    ds_labeled, y_labeled, ds_unlabeled, y_unlabeled = get_dataset()

    all_ds = np.concatenate((ds_labeled, ds_unlabeled), axis=0)
    all_y = np.concatenate((y_labeled, y_unlabeled), axis=0)

    # PRETRAINING autoencoder
    batch_size = 256
    dims = [all_ds[0].shape, 500, 500, 2000, 10]

    autoencoder, encoder = create_autoencoder(dims)
    autoencoder.compile(optimizer=Adam(), loss='mse')

    # TRAINING (se i parametri sono stati già salvati, li si prende da file system)
    model_loaded = False

    name_file_model = 'parameters/duplex_pretraining_conv' if use_convolutional else 'parameters/duplex_pretraining'

    try:
        autoencoder.load_weights(name_file_model)
        model_loaded = True
    except Exception:
        pass

    if not model_loaded:
        n_epochs = 20 if use_convolutional else 50
        autoencoder.fit(all_ds, all_ds, batch_size=batch_size, epochs=n_epochs, shuffle=True)
        autoencoder.save_weights(name_file_model)

    # CUSTOM TRAINING
    clustering_layer = custom_layers.ClusteringLayer(num_classes, name='clustering')

    # last layer
    unlabeled_last_layer = clustering_layer(encoder.output)
    labeled_last_layer = keras.layers.Softmax()(unlabeled_last_layer)

    # models
    model_unlabeled = Model(inputs=encoder.input, outputs=[unlabeled_last_layer, autoencoder.output])
    model_labeled = Model(inputs=encoder.input, outputs=[labeled_last_layer, autoencoder.output])

    plot_model(model_unlabeled, to_file='model_unlabeled.png', show_shapes=True)
    Image(filename='model_unlabeled.png')
    plot_model(model_labeled, to_file='model_labeled.png', show_shapes=True)
    Image(filename='model_labeled.png')

    # run k means for cluster centers
    if init_kmeans:
        centroids = []
        for y_class in positive_classes:
            only_x_class, _ = get_data.filter_ds(ds_labeled, y_labeled, [y_class])
            centroids.append(np.mean(encoder.predict(only_x_class), axis=0))
        while len(centroids) < num_classes:
            centroids.append(np.random.normal(np.mean(centroids, axis=0), np.std(centroids, axis=0)))
        centroids = np.array(centroids)

        kmeans = KMeans(n_clusters=num_classes,
                        init=centroids)
    else:
        kmeans = KMeans(n_clusters=num_classes,
                        n_init=num_classes * 4)

    y_pred = kmeans.fit_predict(encoder.predict(all_ds))
    model_unlabeled.get_layer(name='clustering').set_weights([kmeans.cluster_centers_])

    # fit
    if True:
        y_pred_last = np.copy(y_pred)

        run_duplex(model_unlabeled, model_labeled, ds_labeled, y_labeled, ds_unlabeled, y_unlabeled, y_pred_last)

        model_unlabeled.save_weights("parameters/11")
        model_labeled.save_weights("parameters/22")
    else:
        model_unlabeled.load_weights("parameters/11")
        model_labeled.load_weights("parameters/22")

    # accuratezza
    centroids = clustering_layer.get_centroids()
    y_pred = print_accuracy(all_ds, all_y, centroids, "", model_unlabeled, encoder)

    # silhouette
    x_embedded_encoder = encoder.predict(all_ds)
    score = silhouette_score(x_embedded_encoder, y_pred, metric='euclidean')
    print("Silouhette score:" + str(score))

    # plot
    plot_2d(x_embedded_encoder, y_pred, all_y, centroids)



# iperparametri
gamma_kld = 0.1
gamma_ce = 0.1
ce_function_type = "all"
update_interval = 140
init_kmeans = False

if True:
    main()
else:
    for cft in ["all", "same", "diff"]:
        for gc in [0, 0.1, 0.5]:
            for gk in [0, 0.1, 0.5]:
                for upi in [100, 140, 200]:
                    for ik in [False, True]:
                        ce_function_type = cft
                        gamma_kld = gk
                        gamma_ce = gc
                        update_interval = upi
                        init_kmeans = ik

                        print("ce_function_type", ce_function_type, "gamma_ce", gamma_ce, "gamma_kld", gamma_kld, "update_interval", update_interval, "init_kmeans", init_kmeans)

                        main()

winsound.Beep(frequency, duration)