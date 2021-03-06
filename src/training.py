import os
import json
import numpy as np
import cv2
import scipy
import os
import matplotlib.pyplot as plt
from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation, Flatten
from keras.layers import Conv2D, MaxPooling2D, Lambda
from keras.layers import Dense
from keras_checkpoint import KerasCheckpoint
from keras.utils import np_utils
from keras.preprocessing.image import ImageDataGenerator
from sklearn.preprocessing import LabelEncoder
from sklearn.cross_validation import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix

epochs = 4

if os.path.exists(os.environ['INPUT_DIR'] + '/config.json'):
    with open(os.environ['INPUT_DIR'] + '/config.json') as f:
        config = json.load(f)

BASE_PATH = os.environ['INPUT_DIR'] + '/'
batch_size = 32


def get_model():
    model = Sequential()
    model.add(Lambda(lambda x: x * 1./255., input_shape=(120, 160, 3), output_shape=(120, 160, 3)))
    model.add(Conv2D(32, (3, 3), input_shape=(120, 160, 3)))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Conv2D(32, (3, 3)))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Conv2D(64, (3, 3)))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Flatten())  # this converts our 3D feature maps to 1D feature vectors
    model.add(Dense(64))
    model.add(Activation('relu'))
    model.add(Dropout(0.7))
    model.add(Dense(1))
    model.add(Activation('sigmoid'))

    model.compile(loss='binary_crossentropy',
                optimizer='rmsprop',
                metrics=['accuracy'])

    return model

model = get_model()
print(model.summary())


def get_data(folder):
    """
    Load the data and labels from the given folder.
    """
    X = []
    y = []

    for wbc_type in os.listdir(folder):
        if not wbc_type.startswith('.'):
            if wbc_type in ['NEUTROPHIL', 'EOSINOPHIL']:
                label = 'MONONUCLEAR'
            else:
                label = 'POLYNUCLEAR'
            for image_filename in os.listdir(folder + wbc_type):
                img_file = cv2.imread(folder + wbc_type + '/' + image_filename)
                if img_file is not None:
                    # Downsample the image to 120, 160, 3
                    img_file = scipy.misc.imresize(arr=img_file, size=(120, 160, 3))
                    img_arr = np.asarray(img_file)
                    X.append(img_arr)
                    y.append(label)
    X = np.asarray(X)
    y = np.asarray(y)
    return X, y

X_train, y_train = get_data(BASE_PATH + 'images/TRAIN/')
X_test, y_test = get_data(BASE_PATH + 'images/TEST_SIMPLE/')

encoder = LabelEncoder()
encoder.fit(y_train)
y_train = encoder.transform(y_train)
y_test = encoder.transform(y_test)


model = get_model()

# Use for datmo tracking
snapshot_path = os.environ['SNAPSHOTS_DIR']
checkpoint = KerasCheckpoint(snapshot_path, label='cnn', monitor='val_acc', verbose=1, save_best_only=True, mode='max')
callbacks_list = [checkpoint]

# fits the model on batches
history = model.fit(
    X_train,
    y_train,
    callbacks=callbacks_list,
    validation_split=0.2,
    epochs=epochs,
    shuffle=True,
    batch_size=batch_size)

model.save_weights('binary_model.h5')


def plot_learning_curve(history):
    plt.plot(history.history['acc'])
    plt.plot(history.history['val_acc'])
    plt.title('model accuracy')
    plt.ylabel('accuracy')
    plt.xlabel('epoch')
    plt.legend(['train', 'test'], loc='upper left')
    plt.savefig(os.environ['SHARED_OUTPUT_DIR'] + '/accuracy_curve.png')
    plt.clf()
    # summarize history for loss
    plt.plot(history.history['loss'])
    plt.plot(history.history['val_loss'])
    plt.title('model loss')
    plt.ylabel('loss')
    plt.xlabel('epoch')
    plt.legend(['train', 'test'], loc='upper left')
    plt.savefig(os.environ['SHARED_OUTPUT_DIR'] + '/loss_curve.png')

plot_learning_curve(history)

print('Predicting on test data')
y_pred = np.rint(model.predict(X_test))
stats = {}
acc_score = accuracy_score(y_test, y_pred)
stats['accuracy_score'] = acc_score
conf_matrix = confusion_matrix(y_test, y_pred)
stats['confusion_matrix'] = str(confusion_matrix)

with open(os.environ['SHARED_OUTPUT_DIR']+'/final_stats.json', 'wb') as f:
    f.write(json.dumps(stats))