
import pandas
import matplotlib.pyplot as plt
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description='Plot training history')
parser.add_argument(
    'input',
    type=Path,
    help='File from which to read the text')

args = parser.parse_args()

df = pandas.read_csv(args.input.open('r'))
df = df.set_index('epoch')
fig = df.plot()
plt.show()
