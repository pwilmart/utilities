#
# Counts number of scans in SQT files. PW. 06/10/08
# updated to count unique scan numbers. PW. 06/22/11
#
import os, sys
import gzip
import tkinter
from tkinter import filedialog
#
# navigate to folder with SQT files
#
root = tkinter.Tk()
root.withdraw()
default = os.getcwd()
default = r'E:\PSR_Core_Analysis'
root.update()
sqt_folder_path = filedialog.askdirectory(parent=root, initialdir=default, mustexist=True,
                                          title='Select a DIR for SQT counting')
if not sqt_folder_path: sys.exit()
#
print(80*'=')
print(' program "SQT_counter.py", v1.3, written by Phil Wilmarth, OHSU, 2011-2, 2019 ')
print(80*'=')
first = os.path.basename(os.path.dirname(sqt_folder_path))
second = os.path.basename(sqt_folder_path)
print('..processing:', os.path.join(first, second))
#
scans_total = 0
s_line_total = 0
z_tot = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
os.chdir(sqt_folder_path)
L = os.listdir(sqt_folder_path)
#
fractions = {}
for f in [x for x in L if '.sqt' in x]:
    s_lines = 0
    scans = {}
    z = [{}, {}, {}, {}, {}, {}, {}, {}, {}, {}]
    if '.sqt.gz' in f:
        f_obj = gzip.open(f, 'rb')
    else:
        f_obj = open(f, 'r')
    for line in f_obj.readlines():
        temp = line.split('\t')
        if temp[0] == 'S':
            s_lines += 1
            scans[temp[1]+'.'+temp[2]] = True
            z[int(temp[3])-1][temp[1]+'.'+temp[2]] = True
    print('....file:',f, 'had %s DTAs and %s scans' % (s_lines, len(scans)))
    #
    # keep track of total scans and DTAs per fraction
    #
    if 'filtered' in f:
        temp = f.split('_')
        key = '_'.join(temp[:-2])
    else:
        key = f
    if fractions.get(key, False):
        (frac_dta, frac_scan) = fractions[key]
        frac_dta += s_lines
        frac_scan += len(scans)
        fractions[key] = (frac_dta, frac_scan)
    else:
        fractions[key] = (s_lines, len(scans))
    #
    scans_total += len(scans)
    s_line_total += s_lines
    for i, d in enumerate(z):
        z_tot[i] += len(d)
#
print('\n..total number of s_lines: %s and scans: %s' % (s_line_total, scans_total))
for i, tot in enumerate(z_tot):
    if tot > 0:
        print('....total number of %s+ scans was %s' % (str(i+1), str(tot)))
print()
items = list(fractions.items())
items.sort()
for key, value in items:
    print('..frac: %s had %s DTAs and %s MS2 scans' % (key, value[0], value[1]))
#
# end
#
                
