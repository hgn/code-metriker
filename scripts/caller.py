#!/usr/bin/env python3

import os
import sys
import tempfile
import shutil
import subprocess
import json
import matplotlib
import matplotlib.pyplot as plt

DPI = 90


EXCLUDE_LANGUAGES = ("SUM", "header", "HTML")


REPO = "https://github.com/hgn/captcp.git"


OUTDIR = os.getcwd()



class Loc(object):

    def __init__(self, directory, labels, outdir):
        self.directory = directory
        self.sorted_labels = labels
        self.outdir = outdir
        self.db = dict()

    def feed(self, label):
        cmd = 'cloc --json {}'.format(self.directory)
        result = subprocess.run(cmd.split(), stdout=subprocess.PIPE)
        cloc = result.stdout.decode('utf-8')
        self.db[label] = json.loads(cloc)

    def finalize(self):
        self._graph_sum()
        self._graph_remain()

    def _graph_sum(self):
        fig = plt.figure(figsize=(12,7))
        ax = fig.add_subplot(111)
        x = list(); y = list(); labels = list()
        for i, tag in enumerate(self.sorted_labels):
            x.append(i)
            y.append(self.db[tag]['SUM']['code'])
            labels.append(tag)
        ax.plot(x, y, label='Sum')
        #ax.legend(loc='upper left', frameon=False)
        plt.xticks(x, labels, rotation='vertical')
        # Pad margins so that markers don't get clipped by the axes
        # Tweak spacing to prevent clipping of tick-labels
        ax.margins(.2)
        fig.subplots_adjust(bottom=0.15)
        ax.set_ylabel('Lines of Code')
        ax.set_xlabel('Release')
        ax.grid(color='black', linestyle=':', linewidth=.05)
        filename = os.path.join(self.outdir, "cloc-sum.png")
        fig.savefig(filename, dpi=DPI, bbox_inches='tight')

    def _graph_remain(self):
        dpi = 300
        #style("xkcd")
        #plt.style.use('fivethirtyeight')
        x = list(); y = list(); labels = list()
        all_languages = dict()
        for k1, v1 in self.db.items():
            for k2, v2 in v1.items():
                if k2 not in EXCLUDE_LANGUAGES:
                    all_languages[k2] = list()

        # enumerate over already sorted tags list
        for i, tag in enumerate(self.sorted_labels):
            x.append(i)
            labels.append(tag)

        fig = plt.figure(figsize=(12,7))
        ax = fig.add_subplot(111)

        for language in all_languages:
            y = list()
            for i, tag in enumerate(self.sorted_labels):
                if not language in self.db[tag]:
                    val = 0
                else:
                    val = self.db[tag][language]['code']
                y.append(val)
            ax.plot(x, y, label=language)

        ax.legend(loc='upper left', frameon=False) #, prop={'size': 6})
        plt.xticks(x, labels, rotation='vertical')
        ax.margins(.2)
        fig.subplots_adjust(bottom=0.15)
        ax.set_ylabel('Lines of Code')
        ax.set_xlabel('Release')
        ax.grid(color='lightgrey', linestyle=':', linewidth=.05)
        #for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
        #        ax.get_xticklabels() + ax.get_yticklabels()):
        #    item.set_fontsize(7)
        ax.grid(color='black', linestyle=':', linewidth=.05)
        filename = os.path.join(self.outdir, "cloc-detail.png")
        fig.savefig(filename, dpi=DPI, bbox_inches='tight')




def clone(tmpdir, repo):
    cmd = "git clone {} {}".format(repo, tmpdir)
    w = subprocess.Popen(cmd.split())
    w.wait()

def tags(tmpdir):
    cmd = 'git -C {} tag'.format(tmpdir)
    result = subprocess.run(cmd.split(), stdout=subprocess.PIPE)
    tags = result.stdout.decode('utf-8').splitlines()
    return sorted(tags)

def checkout(tmpdir, tag):
    cmd = "git -C {} checkout {}".format(tmpdir, tag)
    w = subprocess.Popen(cmd.split())
    w.wait()

def exec_loc_grapher(tmpdir, outdir):
    cmd = "./loc-grapher.py --git-dir {} --out-dir {}".format(tmpdir, outdir)
    w = subprocess.Popen(cmd.split())
    w.wait()

def main():
    git_dir = tempfile.TemporaryDirectory().name
    clone(git_dir, REPO)
    tags_sorted = tags(git_dir)

    loc = Loc(git_dir, tags_sorted, ".")

    for tag in tags_sorted:
        checkout(git_dir, tag)
        loc.feed(tag)
    loc.finalize()


if __name__ == "__main__":
    main()
