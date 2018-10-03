
import pandas
import matplotlib.pyplot as plt
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description='Plot training history')
parser.add_argument(
    'input',
    type=Path,
    help='File from which to read the text')
parser.add_argument(
    '--no_save',
    action='store_true',
    help='Save the figure to pdf file (same name) (default: %(default)s)')

args = parser.parse_args()

df = pandas.read_csv(args.input.open('r'))
df = df.set_index('epoch')
fig = df.plot()
plt.grid(b=True, which='both')
if not args.no_save:
    saved_fig = args.input.with_suffix('.pdf')
    plt.savefig(saved_fig, format='pdf')
    print("Saved figure to: {}".format(saved_fig))
plt.show()