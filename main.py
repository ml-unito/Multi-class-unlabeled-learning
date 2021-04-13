import os
import time
import tensorflow as tf
import numpy as np
import argparse
import datetime
from SVM import LinearSVM, RbfSVM
from UREA import UREA
from AREA import AREA
from MPU import MPU
from SDEC import SDEC
import datasets as ds

tf.get_logger().setLevel('ERROR')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
time.sleep(2)
np.random.seed(0)
format_acc = "{:5.3f}"

if __name__ == '__main__':

    n_runs = 5
    perc_ds = 1
    perc_labeled = 0.5
    negative_class_modes = ["two_in_one", "three_in_one", "last",]

    datasets = ["semeion", "optdigits", "pendigits", "har", "usps", "mnist",]
    classifiers = ['linearSVM', 'rbfSVM', "sdec", 'area', 'urea', ]

    data_preparations = ['z_norm']

    # argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset')
    parser.add_argument('--classifier')
    parser.add_argument('--data_prep')
    parser.add_argument('--n_runs')
    parser.add_argument('--negative_class_mode')
    args = parser.parse_args()

    if args.n_runs:
        n_runs = int(n_runs)
    if args.dataset:
        datasets = [args.dataset]
    if args.classifier:
        classifiers = [args.classifier]
    if args.data_prep:
        data_preparations = [args.data_prep]
    if args.negative_class_mode:
        negative_class_modes = [args.negative_class_mode]
    # end arguments parsing

    # print info
    print("Classifiers:", classifiers)
    print("Datasets:", datasets)
    print("Data preps:", data_preparations)
    print("Negative class modes:", negative_class_modes)

    print("Perc. labeled:", perc_labeled, ", total:", perc_ds)
    print("Number of Runs:", n_runs)
    print()
    for dataset in datasets:
        ds.get_dataset_info(dataset)

    # start execution
    for data_preparation in data_preparations:
        print("\n\nDATA PREPARATION:", data_preparation)

        for negative_class_mode in negative_class_modes:
            print("\nNEGATIVE CLASS MODE:", negative_class_mode)

            prefix_path = datetime.datetime.now().strftime("%m_%d_%H") + "_" + negative_class_mode + "_"

            total_test_accuracies = []
            for dataset_name in datasets:
                for name in classifiers:

                    # get model
                    if name == "linearSVM":
                        model = LinearSVM(name, dataset_name, perc_ds, perc_labeled, data_preparation, n_runs, prefix_path, negative_class_mode)
                    elif name == "rbfSVM":
                        model = RbfSVM(name, dataset_name, perc_ds, perc_labeled, data_preparation, n_runs, prefix_path, negative_class_mode)
                    elif name == "area":
                        model = AREA(name, dataset_name, perc_ds, perc_labeled, data_preparation, n_runs, prefix_path, negative_class_mode)
                    elif name == "urea":
                        model = UREA(name, dataset_name, perc_ds, perc_labeled, data_preparation, n_runs, prefix_path, negative_class_mode)
                    elif name == "mpu":
                        model = MPU(name, dataset_name, perc_ds, perc_labeled, data_preparation, n_runs, prefix_path, negative_class_mode)
                    elif name == "sdec":
                        model = SDEC(name, dataset_name, perc_ds, perc_labeled, data_preparation, n_runs, prefix_path, negative_class_mode)

                    # get test accuracies
                    test_accuracies, train_accuracies = model.run_experiments()
                    total_test_accuracies.append(test_accuracies)

            # print results
            print("\n\n --- RESULTS ---")

            # header
            print("\t\t\t\t", end='')
            for clf_name in classifiers:
                print(clf_name, end='')
                [print("\t", end='') for _ in range(4 - len(clf_name) // 4)]
            print()

            index = 0
            for dataset_name in datasets:
                print(dataset_name, end='')
                [print("\t", end='') for _ in range(4 - len(dataset_name) // 4)]

                for clf_name in classifiers:
                    curr_test_acc = total_test_accuracies[index]
                    index += 1

                    print(format_acc.format(np.mean(curr_test_acc)) + "±" + format_acc.format(np.std(curr_test_acc)) + "\t\t", end='')

                print()

            print("---------------")


