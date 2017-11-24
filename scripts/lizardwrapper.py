import argparse
import io
import json
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import subprocess


class LizardWrapper:

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
        cmd = 'lizard --csv --modified'
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

    def get_top100(self):
        df = self.db[-1][:][:100]
        toplist = [{key: row[1][key]
                    for key in self.selected_headers}
                   for row in df.iterrows()]
        return json.dumps(toplist)

    def __plot_lines(self, filename, labels, ccn, nloc):
        fig = plt.figure()
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
        fig.savefig(os.path.join(self.outdir, filename), bbox_inches='tight')

    def __plot_hexbin(self, filename, ccn, nloc):
        fig = plt.figure()
        plt.hexbin(ccn, nloc,
                   gridsize=20, mincnt=1,
                   norm=mcolors.LogNorm(),
                   cmap='plasma')
        plt.colorbar()
        plt.xlabel('CCN')
        plt.ylabel('NLOC')
        fig.savefig(os.path.join(self.outdir, filename), bbox_inches='tight')

