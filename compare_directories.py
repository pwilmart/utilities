"""compare_directories.py
Compares all of the files and directories between the two paths.
written by Phil Wilmarth, OHSU, 2012
updated for Python 3, Feb. 2018

added filtering of non-ASCII characters - 2/18/2017 -PW
"""
import os
import sys
import time
import filecmp
import tkinter
from tkinter import filedialog

LEVELS = 4              # how many subfolder levels for printing
CHECK_CONTENTS = True   # checks actual contents of files
VERBOSE = True          # if True, prints "no difference" folders

def strip(s):
    """Strips non-Ascii characters from strings."""
    return "".join(i for i in s if ord(i)<128)

def get_folder(default_location, title_string=None):
    """Dialog box to browse to a folder.  Returns folder path.

    Usage: full_folder_name = get_folder(default_location, [title]),
        where "default_location" is a starting folder location,
        "title" is an optional message to list in the dialog box,
        and "full_folder_name" is the complete selected folder name.
    Written by Phil Wilmarth, 2008, 2016
    """
    # set up GUI elements
    root = tkinter.Tk()
    root.withdraw()
    try:
        root.tk.call('console', 'hide')
    except:
        pass
    
    # set default title string and location if not passed
    if title_string is None:   
        title_string = 'Select a folder with desired files/dirs'
    if not default_location:
        default_location = os.getcwd()
    
    # create dialog box for folder selection
    root.update()   # helps make sure dialog box goes away after selection
    full_folder_name = filedialog.askdirectory(parent=root, initialdir=default_location, 
                                               title=title_string, mustexist=True)    
    # return full folder name
    return full_folder_name

def no_hidden(files):
    """Removes files that start with periods.
    """
    return([x for x in files if not x.startswith('.')])

def print_files(log_file_list, prefix, title, file_list):
    """Prints list of file with leading title.
    """
    if len(file_list) == 1:
        for obj in log_file_list:
            print('%s%s %s' % (prefix, title, strip(file_list[0])), file=obj)
    else:
        for obj in log_file_list:
            print('%s%s' % (prefix, title), file=obj)
            for f in sorted(file_list):
                print('%s%s%s' % (prefix, prefix, strip(f)), file=obj)
    return

def print_error(log_file_list, error):
    """Prints any errors being trapped.
    """
    for obj in log_file_list:
        print(80*"=", file=obj)
        print('WARNING:', strip(left_path), file=obj)
        print('...', strip(right_path), file=obj)
        print(error, file=obj)
        print(80*"=", file=obj)


default = os.getcwd()
default = 'C:\\'
left = get_folder(default, 'Select first directory')
if not left: sys.exit()
right = get_folder(default, 'Select second directory')
if not right: sys.exit()
log_file = open('compare_dir_log.txt', 'a')
write = [None, log_file]

for obj in write:
    print('\n\n=================================================================', file=obj)
    print('  compare_directories.py, v1.4, Phil Wilmarth, OHSU, 2012, 2017  ', file=obj)
    print('=================================================================', file=obj)
    print('   Ran on: %s\n' % (time.ctime(),), file=obj)
    if CHECK_CONTENTS:
        print('File contents and attributes will be verified.', file=obj)
    else:
        print('File attributes only will be checked.', file=obj)
    print('Comparing:', strip(left), file=obj)
    print('       To:', strip(right), '\n', file=obj)

sep = os.path.sep
top = os.path.normpath(left).count(sep)

for (dirpath, subdirs, files) in os.walk(left):
    left_path = dirpath
    right_path = left_path.replace(left, right)
    dc = filecmp.dircmp(left_path, right_path)

    # trap IOErrors
    try:
        # ignore hidden files (start with periods)
        common_files = no_hidden(dc.common_files)
        left_only = no_hidden(dc.left_only)
        right_only = no_hidden(dc.right_only)
        common_funny = no_hidden(dc.common_funny)
        diff_files = no_hidden(dc.diff_files)
        funny_files = no_hidden(dc.funny_files)

        # check common files for identity
        match, mismatch, errors = [], [], []
        if CHECK_CONTENTS:
            (match, mismatch, errors) = filecmp.cmpfiles(left_path, right_path,
                                                         common_files, shallow=False)
        # only print if there was a difference
        pflag = False
        if (left_only or right_only or common_funny or diff_files or funny_files
            or mismatch or errors):
            pflag = True

        # print what was different
        if pflag:
            prefix = '   '
            for obj in write:
                print('\n-->', strip(left_path), strip(right_path), file=obj)
            if left_only:
                print_files(write, prefix, 'left_only:', left_only)
            if right_only:
                print_files(write, prefix, 'right_only:', right_only)
            if common_funny:
                print_files(write, prefix, 'common_funny:', common_funny)
            if diff_files:
                print_files(write, prefix, 'diff_files:', diff_files)
            if funny_files:
                print_files(write, prefix, 'funny_files:', funny_files)
            if mismatch:
                print_files(write, prefix, '\nmismatches:', mismatch)
            if errors:
                print_files(write, prefix, 'file errors:', errors)
            print(file=obj)

        else:
            depth = os.path.normpath(left_path).count(sep) - top
            if depth <= LEVELS and VERBOSE:
                prefix = '...' * depth
                for obj in write:
                    print('%s%s: %s' % (prefix, os.path.basename(strip(left_path)),
                                               '-OK-'), file=obj)
                
    # report IOError or OSError and continue
    except IOError as e:
        print_error(write, e)
    except OSError as e:
        print_error(write, e)
#
try:    # wait for user to end program if not running from IDLE
    # what __file__ is under XP IDLE: 'C:\\Python26\\Lib\\idlelib\\idle.pyw'
    if not __file__.endswith('idle.pyw'):
        raw_input('\n...hit any key to end program...')
except NameError:
    pass
for obj in write:
    try:
        obj.close()
    except AttributeError:
        pass
#
# end
#

        
