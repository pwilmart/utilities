"""copy_raw_files.py written by Phil Wilmarth, OHSU, 2016-2017.

Copies Thermo RAW files (and other files) selected by the
user to a destination folder. A new filder is created if
needed. Destination will typically be on an external drive.
File contents are checked to ensure that copies are intact,
and copies are repeated (user settable limit) until file and
copy match.

The MIT License (MIT)

Copyright (c) 2017 Phillip A. Wilmarth and OHSU

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

Direct questions to:
Technology & Research Collaborations, Oregon Health & Science University,
Ph: 503-494-8200, FAX: 503-494-4729, Email: techmgmt@ohsu.edu.

updated for Python 3 -PW 20171211
"""
# global imports
import os
import filecmp
import sys
import shutil
import time
import string
import re
from ctypes import windll
import tkinter
from tkinter import filedialog

# how many times to try copying before moving to next file
RETRY = 3
# make extra raw_files folder on destination
RAW_FOLDER = True
# test and remove any spaces in file paths
NO_SPACES = True

def get_files(default_location, extension_list, title_string=""):
    """Dialog box to browse for files.  Returns a list of file names.

    Usage: full_file_name = get_file(default_location, extension_list, [title]),
        where "default_location" is a starting folder location,
        extension_list is a list of (label, pattern) tuples,
        e.g. extension_list = [('Text files', '*.txt')],
        "title" is an optional message to list in the dialog box, and
        "full_file_name" is the complete name of the selected file.
    """

    # set up GUI elements
    root = tkinter.Tk()
    root.withdraw()

    # set default title string if not passed
    if title_string == "":
        title_string = 'Select one or more FILE(s)'

    # create dialog box for file selection
    filenames = filedialog.askopenfilenames(parent=root, initialdir=default_location,
                                            filetypes=extension_list, multiple=True,
                                            title=title_string)
    print(filenames)

    # return fixed full filenames
    if NO_SPACES:
        filenames = [re.sub(' ', '_', f) for f in filenames]
    print(filenames)

    return filenames
    # end

def get_folder(default_location, title_string=""):
    """Dialog box to browse to a folder.  Returns folder path.

    Usage: full_folder_name = get_folder(default_location, [title]),
        where "default_location" is a starting folder location,
        "title" is an optional message to list in the dialog box,
        and "full_folder_name" is the complete selected folder name.
    """

    # set up GUI elements
    root = tkinter.Tk()
    root.withdraw()

    # set default title string if not passed
    if title_string == "":
        title_string = 'Please select a FOLDER'

    # create dialog box and return folder selection
    return filedialog.askdirectory(parent=root, initialdir=default_location,
                                   title=title_string, mustexist=False)
    # end

def get_drives():
    """From "http://stackoverflow.com/
    questions/827371/is-there-a-way-to-list-all-the-available-drive-letters-in-python"
    Gets drive letters without using win32api module (not part of standard dist.).
    """
    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(letter)
        bitmask >>= 1

    return drives

################################################
# program starts here
################################################

# general console message
print('====================================================')
print(' copy_raw_files, v1.0, Phil Wilmarth, OHSU, 2016-17 ')
print('====================================================')

# set up log file
log_obj = open('copy_raw_files_log.txt', 'a')
obj_list = [None, log_obj]

# set up things to get the list of RAW files
default_loc = r'E:\PSR_data'
extensions = [('All File(s)', '*.*'),
              ('RAW File(s)', '*.RAW')]
title_message = 'Select RAW files(s)'

# check default_location
if not os.path.exists(default_loc):
    default_loc = os.getcwd()

# let user browse for files
raw_file_list = get_files(default_loc, extensions, title_message)
if not raw_file_list:
    sys.exit() # cancel button repsonse

# get the folder name that contains the raw files
container_path = os.path.split(raw_file_list[0])[0]
folder_name = os.path.basename(container_path)
if 'RAW' in folder_name.upper():
    container_path = os.path.split(container_path)[0]
    folder_name = os.path.basename(container_path)

# try to get list of all drives so browsing starts somewhere sensible
external_drives = get_drives()

internal_drives = []
for device in ['A', 'C', 'D', 'E', 'F']:
    for i, drive in enumerate(external_drives):
        if drive.startswith(device):
            internal_drives.append(i)
internal_drives.sort(reverse=True)
for index in internal_drives:
    external_drives.pop(index)  # remove 'A', 'C', 'D', 'E', 'F' drives from list

# have user select/create destination folder
print('External drive list:', external_drives)
title_message = 'Select a top-level folder'
default_loc = external_drives[0]
destination_folder = get_folder(default_loc, title_message)
if not destination_folder:
    sys.exit()

# add project folder to destination and optional raw_files subfolder
if RAW_FOLDER:
    destination_folder = os.path.join(destination_folder, folder_name, 'raw_files')
else:
    destination_folder = os.path.join(destination_folder, folder_name)

# create the destination location folder
if not os.path.exists(destination_folder):
    os.makedirs(destination_folder)

# copy files with a number of retries
copied_files = 0
for obj in obj_list:
    print('processing: %s on %s' %
          (os.path.split(raw_file_list[0])[0], time.ctime()), file=obj)
for source in raw_file_list:
    raw_basename = os.path.split(source)[1]
    destination = os.path.join(destination_folder, raw_basename)
    try_count = 0
    redo = True
    while redo:
        shutil.copy2(source, destination)
        try_count += 1
        if filecmp.cmp(source, destination, shallow=False):
            for obj in obj_list:
                print('...COPY OK:', raw_basename, file=obj)
            copied_files += 1
            redo = False
        elif try_count > RETRY:
            for obj in obj_list:
                print('...WARNING: could not copy:', raw_basename, file=obj)
            redo = False
        else:
            for obj in obj_list:
                print('...RETRYING COPY:', raw_basename, file=obj)

# print some summaries
for obj in obj_list:
    print('\n%s files read from: %s' % (len(raw_file_list), folder_name), file=obj)
    print('%s files copied to: %s' % (copied_files, destination_folder), file=obj)
    print(time.ctime(), file=obj)

log_obj.close()
# end
