#!/usr/bin/env python3

import os
import io
import sys
import tempfile
import shutil
import subprocess
import json
import argparse
import numpy as np
import pandas as pd
import asyncio
from datetime import datetime

import matplotlib
# force matplotlib not to use x window system,
# must be before any other matplotlib import
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors



DPI = 90
FIGSIZE_WIDE = (12,7)
FIGSIZE_RECT = (12,9)

LINEWIDTH = 4.0


EXCLUDE_LANGUAGES = ("SUM", "header", "HTML")




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
        return toplist

    def __plot_lines(self, filename, labels, ccn, nloc):
        fig = plt.figure(figsize=FIGSIZE_WIDE)
        ax1 = fig.add_subplot(211)
        ax2 = fig.add_subplot(212)
        ax2.plot(nloc, color=plt.cm.viridis(0), linewidth=LINEWIDTH)
        ax2.grid(color='lightgrey', linestyle=':', linewidth=1.0)
        ax1.plot(ccn, color=plt.cm.viridis(.5), linewidth=LINEWIDTH)
        ax1.grid(color='lightgrey', linestyle=':', linewidth=1.0)
        ax2.set_xticks(np.arange(len(nloc)))
        ax1.set_xticks(np.arange(len(nloc)))
        ax2.set_xticklabels([])
        ax1.set_xticklabels(labels)
        ax2.set_ylabel('NLOC')
        ax1.set_ylabel('CCN')
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
        cmd = 'cloc --exclude-lang=\"XML\" --json {}'.format(self.directory)
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
        ax.plot(x, y, label='Sum', linewidth=LINEWIDTH)
        plt.xticks(x, labels, rotation='vertical')
        # Pad margins so that markers don't get clipped by the axes
        # Tweak spacing to prevent clipping of tick-labels
        ax.margins(.2)
        fig.subplots_adjust(bottom=0.15)
        ax.set_ylabel('Lines of Code')
        ax.set_xlabel('Release')
        ax.grid(color='lightgrey', linestyle=':', linewidth=1.0)
        filename = os.path.join(self.outdir, "cloc-sum.png")
        fig.savefig(filename, dpi=DPI, bbox_inches='tight')
        plt.close(fig)

    def _graph_remain(self):
        dpi = 300
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
            ax.plot(x, y, label=language, linewidth=LINEWIDTH)

        legend = ax.legend(loc='upper left', frameon=True, prop={'size': 8})
        legend.get_frame().set_facecolor('#FFFFFF')
        legend.get_frame().set_linewidth(0.0)

        plt.xticks(x, labels, rotation='vertical')
        ax.margins(.2)
        fig.subplots_adjust(bottom=0.15)
        ax.set_ylabel('Lines of Code')
        ax.set_xlabel('Release')
        ax.grid(color='lightgrey', linestyle=':', linewidth=1.0)
        filename = os.path.join(self.outdir, "cloc-detail.png")
        fig.savefig(filename, dpi=DPI, bbox_inches='tight')
        plt.close(fig)



async def git_clone(tmpdir, repo):
    # with async_timeout.timeout(FETCH_TIMEOUT):
    cmd = "git -c http.sslVerify=false clone {} {}".format(repo, tmpdir)
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
    cmd = "git -c http.sslVerify=false -C {} submodule sync".format(tmpdir)
    print(cmd)
    process = await asyncio.create_subprocess_exec(*cmd.split())
    await process.wait()
    cmd = "git -c http.sslVerify=false -C {} submodule update --init --recursive".format(tmpdir)
    print(cmd)
    process = await asyncio.create_subprocess_exec(*cmd.split())
    await process.wait()

def sanitize_file(app, filename):
    # get rid of full (/tmp/tmp9x9/repo) path
    return filename[len(app['GIT-DIR']) + 1:]

def cc_prepare_func_list_data(app, liz):
    d = ""
    for i, data in enumerate(liz.top100()):
        data['file'] = sanitize_file(app, data['file'])
        d += "<tr>"
        d +=   "<td>{}</td>".format(data['CCN'])
        d +=   "<td>{}</td>".format(data['NLOC'])
        d +=   "<td>{}</td>".format(data['function'])
        d +=   "<td>{}</td>".format(data['file'])
        d += "</tr>"
        if i > app['CONF']['cc_top_list_max']:
            break
    return d


def cc_prepare_html(app, ctx, liz):
    html_snippet = cc_prepare_func_list_data(app, liz)
    status = "@repo:{}, @buildtime:{:.1f}sec".format(app['CONF']['repo'], ctx['duration'])
    return dict(STATUS=status,
                CCN_TABLE=html_snippet,
                CCLIMIT=app['CONF']['cc_top_list_max'],
                REPOURL=app['CONF']['repo'])

def cc_generate_page(app, ctx, liz):
    subst = cc_prepare_html(app, ctx, liz)
    # convert to byte object
    app['PAGE-CC'] = str.encode(app['PAGE-CC-TEMPLATE'].safe_substitute(subst))

def cloc_prepare_html(app, ctx, liz):
    status = "@repo:{}, @buildtime:{:.1f}sec".format(app['CONF']['repo'], ctx['duration'])
    return dict(STATUS=status)

def cloc_generate_page(app, ctx, liz):
    subst = cloc_prepare_html(app, ctx, liz)
    # convert to byte object
    app['PAGE-CLOC'] = str.encode(app['PAGE-CLOC-TEMPLATE'].safe_substitute(subst))


async def worker(app):
    t1 = datetime.now()
    # just the IO hogs are awaited
    app['GIT-DIR'] = os.path.join(app['TMPDIR'], "repo")
    git_dir = app['GIT-DIR']
    if os.path.isdir(git_dir):
        shutil.rmtree(git_dir)
        os.mkdir(git_dir)
    await git_clone(git_dir, app['CONF']['repo'])
    tags_sorted = tags(git_dir)

    loc = Loc(git_dir, app['APP-DATA'])
    liz = LizardWrapper(git_dir, app['APP-DATA'])

    for tag in tags_sorted:
        await git_checkout(git_dir, tag)
        loc.feed(tag)
        liz.feed(tag)
    loc.finalize()
    liz.finalize()

    ctx = dict()
    duration = (datetime.now() - t1).total_seconds()
    ctx['duration'] = duration

    cc_generate_page(app, ctx, liz)
    cloc_generate_page(app, ctx, liz)


def main(app):
    # create task
    asyncio.ensure_future(worker(app))
