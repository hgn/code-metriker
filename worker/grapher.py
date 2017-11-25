#!/usr/bin/env python3

import os
import sys
import tempfile
import shutil
import subprocess
import json
import matplotlib
import matplotlib.pyplot as plt
import argparse
import io
import matplotlib.colors as mcolors
import numpy as np
import os
import pandas as pd
import asyncio


DPI = 90
FIGSIZE_WIDE = (12,7)
FIGSIZE_RECT = (12,9)


EXCLUDE_LANGUAGES = ("SUM", "header", "HTML")


REPO = "https://github.com/hgn/captcp.git"
REPO = "https://github.com/netsniff-ng/netsniff-ng.git"
REPO = "https://github.com/kernelslacker/trinity.git"


OUTDIR = os.getcwd()

class LizardWrapper(object):

    def __init__(self, workingdir, outdir):
        self.workingdir = workingdir
        self.outdir = outdir
        self.db = list()
        self.labels = list()
        self.headers = ['NLOC', 'CCN', 'token', 'PARAM', 'length', 'location',
                        'file', 'function', 'begin', 'end']
        self.selected_headers = ['NLOC', 'CCN', 'file', 'function',
                                 'begin', 'end']

    def feed(self, label):
        cmd = 'lizard --csv --modified {}'.format(self.workingdir)
        result = subprocess.run(cmd.split(), stdout=subprocess.PIPE)
        csstring = result.stdout.decode('utf-8')
        df = pd.read_csv(io.StringIO(csstring), header=None, names=self.headers)
        df.sort_values(by='CCN', ascending=False, inplace=True)
        self.db.append(df)
        self.labels.append(label)

    def finalize(self):
        mean_nloc = [np.mean(df.loc[df.shape[0] // 20:, 'NLOC'])
                     for df in self.db]
        mean_ccn = [np.mean(df.loc[df.shape[0] // 20:, 'CCN'])
                    for df in self.db]

        self.__plot_lines('nloc-ccn-mean.png', self.labels, mean_ccn, mean_nloc)
        self.__plot_hexbin('nloc-ccn-hexbin.png',
                           self.db[-1]['CCN'], self.db[-1]['NLOC'])

        if len(self.db) < 2:
            return

        diff_df = pd.merge(self.db[-2], self.db[-1],
                           how='outer', indicator=True)
        diff_df = diff_df[diff_df['_merge'] == 'right_only'].copy()
        diff_df.sort_values(by='CCN', ascending=False, inplace=True)

        if diff_df.shape[0] == 0:
            return
        self.__plot_hexbin('nloc-ccn-hexbin.png',
                           diff_df['CCN'], diff_df['NLOC'])

    def top100(self):
        df = self.db[-1][:][:100]
        toplist = [{key: row[1][key]
                    for key in self.selected_headers}
                   for row in df.iterrows()]
        return json.dumps(toplist)

    def __plot_lines(self, filename, labels, ccn, nloc):
        fig = plt.figure(figsize=FIGSIZE_WIDE)
        par1 = fig.add_subplot(211)
        par2 = fig.add_subplot(212)
        par1.plot(nloc, 'o-', color=plt.cm.viridis(0))
        par2.plot(ccn, 'o-', color=plt.cm.viridis(.5))
        par1.set_xticks(np.arange(len(nloc)))
        par2.set_xticks(np.arange(len(nloc)))
        par1.set_xticklabels([])
        par2.set_xticklabels(labels)
        par1.set_ylabel('NLOC')
        par2.set_ylabel('CCN')
        fig.savefig(os.path.join(self.outdir, filename), bbox_inches='tight', dpi=DPI)
        plt.close(fig)

    def __plot_hexbin(self, filename, ccn, nloc):
        fig = plt.figure(figsize=FIGSIZE_RECT)
        plt.hexbin(ccn, nloc,
                   gridsize=20, mincnt=1,
                   norm=mcolors.LogNorm(),
                   cmap='plasma_r')
        plt.colorbar()
        plt.xlabel('CCN')
        plt.ylabel('NLOC')
        fig.savefig(os.path.join(self.outdir, filename), bbox_inches='tight', dpi=DPI)
        plt.close(fig)



class Loc(object):

    def __init__(self, directory, outdir):
        self.directory = directory
        self.sorted_labels = list()
        self.outdir = outdir
        self.db = dict()

    def feed(self, label):
        self.sorted_labels.append(label)
        cmd = 'cloc --json {}'.format(self.directory)
        result = subprocess.run(cmd.split(), stdout=subprocess.PIPE)
        cloc = result.stdout.decode('utf-8')
        self.db[label] = json.loads(cloc)

    def finalize(self):
        self._graph_sum()
        self._graph_remain()

    def _graph_sum(self):
        fig = plt.figure(figsize=FIGSIZE_WIDE)
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
        plt.close(fig)

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

        fig = plt.figure(figsize=FIGSIZE_WIDE)
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
        plt.close(fig)



async def git_clone(tmpdir, repo):
    # with async_timeout.timeout(FETCH_TIMEOUT):
    cmd = "git clone {} {}".format(repo, tmpdir)
    process = await asyncio.create_subprocess_exec(*cmd.split())
    code = await process.wait()
    print('Terminated with code {}'.format(code))

def tags(tmpdir):
    cmd = 'git -C {} tag'.format(tmpdir)
    result = subprocess.run(cmd.split(), stdout=subprocess.PIPE)
    tags = result.stdout.decode('utf-8').splitlines()
    return sorted(tags)

async def git_checkout(tmpdir, tag):
    cmd = "git -C {} checkout {}".format(tmpdir, tag)
    print(cmd)
    process = await asyncio.create_subprocess_exec(*cmd.split())
    await process.wait()
    cmd = "git submodule sync"
    print(cmd)
    process = await asyncio.create_subprocess_exec(*cmd.split())
    await process.wait()
    cmd = "git submodule update --init --recursive"
    print(cmd)
    process = await asyncio.create_subprocess_exec(*cmd.split())
    await process.wait()

async def worker(app):
    # just the IO hogs are awaited
    git_dir = os.path.join(app['TMPDIR'], "repo")
    if os.path.isdir(git_dir):
        shutil.rmtree(git_dir)
        os.mkdir(git_dir)
    await git_clone(git_dir, REPO)
    tags_sorted = tags(git_dir)

    loc = Loc(git_dir, ".")
    liz = LizardWrapper(git_dir, ".")

    for tag in tags_sorted:
        await git_checkout(git_dir, tag)
        loc.feed(tag)
        liz.feed(tag)
    loc.finalize()
    liz.finalize()

    print(liz.top100())

def main(app):
    # create task
    asyncio.ensure_future(worker(app))
