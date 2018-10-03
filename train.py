import os
import json
import argparse
import sys
import logging
import logging.handlers

from pathlib import Path

import numpy as np

from model import build_model, save_weights, load_weights
from keras.utils.vis_utils import plot_model

DATA_DIR = './data'
LOG_DIR = './logs'
MODEL_DIR = './model'

BATCH_SIZE = 16
SEQ_LENGTH = 64

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

logger = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])
logger.addHandler(ch)
logger.setLevel(logging.INFO)


class TrainLogger(object):
    def __init__(self, file, resume_at=0):
        self.file = os.path.join(LOG_DIR, file)
        self.epochs = resume_at
        if self.epochs == 0:
            with open(self.file, 'w') as f:
                f.write('epoch,loss,acc\n')
        else:
            with open(self.file, 'a') as f:
                f.write('resume training at epoch {}\n'.format(self.epochs))

    def add_entry(self, loss, acc):
        self.epochs += 1
        s = '{},{},{}\n'.format(self.epochs, loss, acc)
        with open(self.file, 'a') as f:
            f.write(s)


def read_batches(T, vocab_size):
    # the full text length
    length = T.shape[0]
    # number of character per batch
    batch_chars = length // BATCH_SIZE

    for start in range(0, batch_chars - SEQ_LENGTH, SEQ_LENGTH):
        X = np.zeros((BATCH_SIZE, SEQ_LENGTH))
        Y = np.zeros((BATCH_SIZE, SEQ_LENGTH, vocab_size))
        for batch_idx in range(0, BATCH_SIZE):
            for i in range(0, SEQ_LENGTH):
                X[batch_idx, i] = T[batch_chars * batch_idx + start + i]
                Y[batch_idx, i, T[batch_chars * batch_idx + start + i + 1]] = 1
        yield X, Y


def train(text, epochs=100, save_freq=10, resume=False):

    if resume:
        logger.info("Trying to resume last training...")
        # try to resume previous training
        model_dir = Path(MODEL_DIR)
        # load the dictionary (character to idx file)
        c2ifile = model_dir.joinpath('char_to_idx.json')
        if not c2ifile.exists():
            logger.fatal("Dictionary file <%s> not found.", c2ifile)
            logger.fatal("Cannot resume. Abort")
            sys.exit(1)
        with c2ifile.open('r') as f:
            char_to_idx = json.load(f)
        # list checkpoints files
        lfw = model_dir.glob('weights.*.h5')
        # get the list of saved epochs
        lcp = map(lambda p: int(p.name.split('.h5')[0]
                                      .split('weights.')[1]),
                  lfw)
        # the biggest one is the last one
        last_epoch_checkpointed = max(lcp)
        logger.info("Resuming from epoch %d", last_epoch_checkpointed)
    else:
        last_epoch_checkpointed = 0
        char_to_idx = {ch: i for (i, ch) in enumerate(sorted(list(set(text))))}
        with open(os.path.join(MODEL_DIR, 'char_to_idx.json'), 'w') as f:
            json.dump(char_to_idx, f)

    vocab_size = len(char_to_idx)

    logger.info("batch_size=%d, seq_length=%d, vocab_size=%d",
                BATCH_SIZE, SEQ_LENGTH, vocab_size)
    model = build_model(BATCH_SIZE, SEQ_LENGTH, vocab_size)
    model.summary()
    if last_epoch_checkpointed > 0:
        load_weights(last_epoch_checkpointed, model)
    model.compile(loss='categorical_crossentropy',
                  optimizer='adam', metrics=['accuracy'])

    if not resume:
        json.dump(json.loads(model.to_json()),
                Path(MODEL_DIR).joinpath('model.json').open('w'),
                sort_keys=True,
                indent=1
                )

        plot_model(model, to_file=os.path.join(MODEL_DIR, 'model_plot.svg'), show_shapes=True, show_layer_names=True)

    T = np.asarray([char_to_idx[c] for c in text], dtype=np.int32)
    steps_per_epoch = (len(text) / BATCH_SIZE - 1) / SEQ_LENGTH
    logger.info("steps_per_epoch=%d", steps_per_epoch)
    log = TrainLogger('training_log.csv', last_epoch_checkpointed)

    for epoch in range(last_epoch_checkpointed, epochs):
        print('\nEpoch {}/{}'.format(epoch + 1, epochs))
        losses, accs = [], []

        for i, (X, Y) in enumerate(read_batches(T, vocab_size)):
            loss, acc = model.train_on_batch(X, Y)
            print('Batch {}: loss = {}, acc = {}'.format(i + 1, loss, acc))
            losses.append(loss)
            accs.append(acc)

        log.add_entry(np.average(losses), np.average(accs))
        logger.info("Passed epoch %d", epoch+1)

        if (epoch + 1) % save_freq == 0:
            save_weights(epoch + 1, model)
            print('Saved checkpoint to', 'weights.{}.h5'.format(epoch + 1))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Train the model on some text.')
    parser.add_argument('--input', default='input.txt',
                        help='name of the text file to train from')
    parser.add_argument('--epochs', type=int, default=100,
                        help='number of epochs to train for')
    parser.add_argument('--freq', type=int, default=10,
                        help='checkpoint save frequency')
    parser.add_argument('--resume', action='store_true',
                        help='Try to resume from previously interrupted training and continue to train until epoch')
    args = parser.parse_args()

    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    logger.info("Beginning to train...")
    train(open(os.path.join(DATA_DIR, args.input)).read(), args.epochs, args.freq, args.resume)

    logger.info("End of training.")
