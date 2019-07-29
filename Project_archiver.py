"""
Project_archiver.py: written by Billy Rathje, OHSU, 2013.
Conversion to Python 3 by Phil Wilmarth, OHSU, 2019.

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


Project_archiver.py

A utility to check projects to determine if they are ready to archive. Checks that
project sequence has been completed, deletes DTA and OUT files if ZIP counterparts
exist, and moves folders ready to be archived to an archives folder.

Original by Billy Rathje, July-AugustOHSU, 2013
Edits by Phil Wilmarth, August, 2013
improved names of Zip folders to avoid collisions - PW 2/2014
fixed bug in archive checker to skip subfolders - PW 3/2014
"""

"""To do 20130902:
should keep a WARNINGS count for each project
    note projects with no warnings
    note projects with WARNINGs
"""

import sys
import os
import shutil
import tkMessageBox
import gzip
import zipfile
import time
import glob
import platform
from Tkinter import *

#==========   SETUP FLAGS    ===========
# Flag designating when a project is expired (in days).
EXPIRES = 30.0
##EXPIRES = 0.0

# Move files to special folder or leave in place
################################
################################
MOVE_FILES = False

# Auto-compression Size Threshold
SIZE_THRESHOLD = 5242880     # 5 MB
##SIZE_THRESHOLD = 3145728    # 3 MB

# Compress large files flag
GZIP_LARGE_FILES = True

# Do not compress file extension list
DO_NOT_COMPRESS = ['.raw', '.wiff', '.scan', '.zip', '.gz', '.rar', '.sf3', '.sfd', '.srf', '.msf']

# Compress file extension list
COMPRESS = ['.mgf', '.ms2', '.sqt', '.dat']

# default locations for primary project folders
ANALYSIS_FOLDERS = {'analysis_5': r'D:\PSR_Core_analysis',
                    'newdatapc' : r'D:\Temp_Data_Analysis',
                    'analysis_4': r'D:\PSR_Core_Analysis',
                    'analysis_6': r'D:\PSR_Core_analysis',
                    'psrcore-mrba608': r'F:\PSR_Core_Analysis',
                    'psrcore-mrba610': r'F:\PSR_Core_Analysis',
                    'psrcore-mrba611': r'F:\PSR_Core_Analysis'}

# default locations of communication files (one file per computer)
PROJECT_LISTS = {'analysis_5': r'C:\Documents and Settings\PSR_Core\Desktop\Project_Lists.txt',
                 'newdatapc': r'C:\Documents and Settings\PSR Core\Desktop\Project_Lists.txt',
                 'analysis_4': r'C:\Documents and Settings\PSR_Core\Desktop\Project_Lists.txt',
                 'analysis_6': r'C:\Documents and Settings\PSR_Core\Desktop\Project_Lists.txt',
                 'psr_core_spare': r'C:\Documents and Settings\PSR_Core\Desktop\Project_Lists.txt',
                 'psrcore-mrba608': r'C:\Documents and Settings\PSR_Core\Desktop\Project_Lists.txt',
                 'psrcore-mrba610': r'C:\Documents and Settings\PSR_Core\Desktop\Project_Lists.txt',
                 'psrcore-mrba611': r'C:\Documents and Settings\PSR_Core\Desktop\Project_Lists.txt'}

# get the local paths for this computer
computer_name = platform.node().lower()

# Default location to search for files
try:
    DEFAULT = ANALYSIS_FOLDERS[computer_name]
except KeyError:
    DEFAULT = os.getcwd()

####################################
####################################
##DEFAULT = r'H:\\'

# absolute path to configuration file: Project_Lists.txt (should be on the descktop)
try:
    PATH_TO_PROJECT_LISTS = PROJECT_LISTS[computer_name]
except KeyError:
    PATH_TO_PROJECT_LISTS = os.getcwd()

# Name of archive folder (relative path, user selects the root location - it may not be DEFAULT)
ARCHIVE_NAME = 'zzz_TO_ARCHIVE'


#============= GUI related classes and functions ===============
class GUI:
    def __init__(self, completed, ongoing, not_expired_list, expired_list, root_folder, write):
        '''
        GUI constructor
        '''
        self.left = expired_list                    # List of projects ready to archive
        self.right = completed                      # List of projects selected to archive
        self.fail_list = ongoing + not_expired_list # Projects not ready to archive
        self.completed = completed
        self.ongoing = ongoing
        self.not_expired_list = not_expired_list    # Projects not expired
        self.expired_list = expired_list            # Projects old enough to archive
        self.root_folder = root_folder
        self.root = None                            # Tkinter root window
        self.listbox_left = None                    # Box for list of projects ready to archive
        self.listbox_right = None                   # Box for list of projects user has selected to archive
        self.gzip_large_files = IntVar()
        self.move_files = IntVar()
        self.progressbar = None
        self.progresstext = None
        self.cancel = False
        self.write = write

    def archive(self):
        '''
        Response, archive button pressed
        '''
        global MOVE_FILES
        global GZIP_LARGE_FILES
        if(len(self.right) > 0):
            import ttk
            s = '\n'
            for r in self.right:
                s += r + '\n'

            self.progressbar = ttk.Progressbar(self.root)
            self.progressbar.pack(expand = 1, fill = X)
            self.progresstext = Label(self.root, text = 'Initializing')
            self.progresstext.pack()
            self.progressbar.update()
            
            if tkMessageBox.askyesno(title = 'Preview', message = 'Ready to archive the following projects?' + s):
                success_list = process_projects(self.root_folder, self.right, self.fail_list, self.write)
                if MOVE_FILES:
                    clean_project_lists(PATH_TO_PROJECT_LISTS, success_list, self.write)
                g.end()

    def end_now(self):
        '''
        Response, cancel button pressed
        '''
        self.cancel = True
        self.end()
        
    def end(self):
        '''
        Response, cancel button pressed
        '''
        global DEFAULT
        # close the log file and delete it
        for obj in self.write:
            if obj != None:
                f_name = os.path.abspath(obj.name)
                obj.close()
                if self.cancel:
                    os.remove(f_name)
        os.chdir(DEFAULT)
        self.root.destroy()
        sys.stderr = None
        sys.stdout = None
        sys.exit()

    def gzip_check(self):
        '''
        Checkbutton response
        '''
        global GZIP_LARGE_FILES
        self.gzip_large_files.set(int(not(self.gzip_large_files.get())))
        GZIP_LARGE_FILES = bool(self.gzip_large_files.get())

    def move_check(self):
        '''
        Checkbutton response
        '''
        global MOVE_FILES
        self.move_files.set(int(not(self.move_files.get())))
        MOVE_FILES = bool(self.move_files.get())

    def move_to_right(self):
        '''
        Response, move project to right/archive box
        '''
        vals = self.listbox_left.curselection()
        for v in vals:
            self.right.append(self.left[int(v)])
            self.left.remove(self.left[int(v)])
        self.listbox_left.delete(0, END)
        self.listbox_right.delete(0, END)
        for l in self.left:
            self.listbox_left.insert(END, l)
        for r in self.right:
            self.listbox_right.insert(END, r)
            
        if(self.listbox_left.size() == 0):
            self.listbox_right.selection_set(0)
        else:
            self.listbox_left.selection_set(0)

    def move_to_left(self):
        '''
        Response, move project to left/ready to archive box
        '''
        vals = self.listbox_right.curselection()
        for v in vals:
            self.left.append(self.right[int(v)])
            self.right.remove(self.right[int(v)])
        self.listbox_left.delete(0, END)
        self.listbox_right.delete(0, END)
        for l in self.left:
            self.listbox_left.insert(END, l)
        for r in self.right:
            self.listbox_right.insert(END, r)

        if(self.listbox_right.size() == 0):
            self.listbox_left.selection_set(0)
        else:
            self.listbox_right.selection_set(0)
        
    def gui_go(self):
        '''
        Start up GUI
        '''
        global MOVE_FILES
        global GZIP_LARGE_FILES
        # Display results in a GUI
        self.root = Tk()
        self.root.title('Project Archiver GUI')
        self.root.geometry("600x600+500+200")

        container = Frame(self.root)
        container.pack()        
        Label(container, text = 'Ready to Archive:').pack(side=TOP)

        # left project list widget - frame in a frame
        lf_out_frame = Frame(container)
        Label(lf_out_frame, text='Archive Candidates:').pack(side=TOP)
        lf_out_frame.pack(fill=BOTH, expand=YES, side=LEFT)
        left_frame = Frame(lf_out_frame, bd=1, relief='solid', bg='white')
        left_frame.pack(fill=BOTH, expand=YES, side=LEFT, padx=5, pady=5)
        # add scrollbar to inner frame
        leftscroll = Scrollbar(left_frame)
        leftscroll.pack(side=RIGHT, fill=Y)
        # add listbox to inner frame
        self.listbox_left = Listbox(left_frame, bd=0, bg='white')
        self.listbox_left.pack(fill=BOTH, expand=YES, side=LEFT, padx=2, pady=2)
        for s in sorted(self.left):
            self.listbox_left.insert(END, s)
        # attach the scrollbar to the listbox
        self.listbox_left.config(yscrollcommand=leftscroll.set)
        leftscroll.config(command=self.listbox_left.yview)

        # right project list widget - frame in a frame
        rt_out_frame = Frame(container)
        Label(rt_out_frame, text='To be Archived:').pack(side=TOP)
        rt_out_frame.pack(fill=BOTH, expand=YES, side=RIGHT)
        right_frame = Frame(rt_out_frame, bd=1, relief='solid', bg='white')
        right_frame.pack(fill=BOTH, expand=YES, side=RIGHT, padx=5, pady=5)
        # add scrollbar to inner frame
        rightscroll = Scrollbar(right_frame)
        rightscroll.pack(side=RIGHT, fill=Y)
        # add listbox to inner frame
        self.listbox_right = Listbox(right_frame, bd=0, bg='white')
        self.listbox_right.pack(fill=BOTH, expand=YES, side=RIGHT, padx=2, pady=2)
        for r in sorted(self.right):
            self.listbox_right.insert(END, r)
        # attach the scrollbar to the listbox
        self.listbox_right.config(yscrollcommand=rightscroll.set)
        rightscroll.config(command=self.listbox_right.yview)

        r = Button(container, text='>>', command=self.move_to_right)
        l = Button(container, text='<<', command=self.move_to_left)
        r.pack(side=RIGHT)
        l.pack(side=LEFT)

        container.pack(side = TOP, fill = BOTH, expand = 1)

        # bottom project list widget
        Label(self.root, text= 'Not ready to archive, ongoing projects:').pack()
        bottom_frame = Frame(self.root, bd=1, relief='solid', bg='white')
        bottom_frame.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        # add scrollbar
        bottomscroll = Scrollbar(bottom_frame)
        bottomscroll.pack(side=RIGHT, fill=Y)
        # add listbox
        listbox2 = Listbox(bottom_frame, bd=0, bg='white')
        listbox2.pack(fill=BOTH, expand=YES, padx=2, pady=2)
        for f in sorted(set(self.fail_list)):
            listbox2.insert(END, f)
        # attach the scrollbar to the listbox
        listbox2.config(yscrollcommand=bottomscroll.set)
        bottomscroll.config(command=listbox2.yview)

        options = Frame(self.root)
        cgz = Checkbutton(options, text = 'Zip files over ' + str(SIZE_THRESHOLD/1048576) + ' MB?',
                        variable = self.gzip_large_files, command = self.gzip_check)
        cgz.pack(side = LEFT)
        self.gzip_large_files.set(int(GZIP_LARGE_FILES))
        if GZIP_LARGE_FILES:
            cgz.select()
        cmv = Checkbutton(options, text = 'Move archived projects?',
                        variable = self.move_files, command = self.move_check)
        cmv.pack(side = RIGHT)
        self.move_files.set(int(MOVE_FILES))
        if MOVE_FILES:
            cmv.select()
        options.pack(side=TOP, fill=BOTH, expand=YES)

        buttons = Frame(self.root)
        archive = Button(buttons, text = 'Archive', command = self.archive).pack(side=RIGHT, pady=5)
        cancel = Button(buttons, text = 'Cancel', command = self.end_now).pack(side=LEFT, pady=5)
        buttons.pack(side=BOTTOM)
        
        self.root.mainloop()
# end GUI class

def get_folder(default):
    """Puts up dialog box to browse to a folder -
    'default' is the default location.
    """
    import Tkinter, tkFileDialog
    root = Tkinter.Tk()
    root.withdraw()
    folder_path = tkFileDialog.askdirectory(parent=root,initialdir=default,\
                                       title='Please select the FOLDER for archive processing')
    return(folder_path)

def zip_one_folder(info, path_to_project, write):
    """Function "zip_one_folder" - zips up one folder of DTA and OUT files.

    A folder path to DTA and OUT files is passed in via "info" object.
    The folder contents are non-recursively archived into a zip file
    having the same base name as the folder name.

    Written by Phil Wilmarth, OHSU, 2009.

    Adapted for archving utility, OHSU, 2013 -- BR, PW
    """
    # zip up all files (skipping any folders) in each sub directory
    # NOTE: this is NOT recursive by design
    if len(info.dta_path) > 50:
        s = '...' + info.dta_path[len(path_to_project):]
    else:
        s = info.dta_path
    for obj in write:
        print >>obj, '...Zipping DTA and OUT files in %s' % (s,)
    os.chdir(info.dta_path)
    folder = os.path.basename(info.dta_path)
    zip_name = os.path.join(info.dta_path, folder + '.zip')
    file_list, outs, dtas = [], 0, 0
    g.progresstext.configure(text = "Zipping DTA OUT files: " + folder)
    g.progressbar.update()
    # build the file list skipping any folders, print warning about folders
    for item in os.listdir('.'):
        if os.path.isdir(item) or item[-4:] in (DO_NOT_COMPRESS + COMPRESS):
            if item == os.path.basename(zip_name):
                for obj in write:
                    print >>obj, '......WARNING:', zip_name[len(path_to_project):], 'was overwritten'
            else:
                for obj in write:
                    print >>obj, '......WARNING:', os.path.join(info.dta_path, item)[len(path_to_project):], 'not added to Zip archive'
        else:
            if item.endswith('.dta'):
                dtas += 1
            elif item.endswith('.out'):
                outs += 1
            file_list.append(item)
    
    # print warning if SEQUEST search was incomplete
    if outs < dtas:
        for obj in write:
            print >>obj, '......WARNING: OUT files (%s) less than DTA files (%s)' % (outs, dtas)
    
    # skip empty folders
    if len(file_list) == 0:
        info.zip_path = None
        return False

    # print number of files to be zipped
    for obj in write:
        print >>obj, '......%s contains %s DTA and %s OUT files' % (folder, dtas, outs)
    
    # add files to archive. This overwrites any existing archives.
    zip_file = zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED, allowZip64=True)
    for files in file_list:
        try:
            zip_file.write(files, os.path.basename(files))
        except:
            for obj in write:
                print >>obj, '......WARNING: %s could not be added to archive' % (files,)
    zip_file.close()
    info.zip_path = zip_name

    # check that the archiving was sucessful
    if not check_archive(info.zip_path, info, path_to_project, write):
        os.remove(info.zip_path)
        info.zip_path = None
        return False
    else:
        for obj in write:
            print >>obj, '......%s is complete' % (folder + '.zip',)
        return True
    # end

def gzip_file_inplace(the_file, write):
    '''
    gzip_file_inplace(the_file)

    Gzip the_file, compare original and gzip, delete original.
    the_file.gz will replace the_file. the_file is full path name.
    Returns True if all went well, False otherwise (original remains).

    Billy Rathje and Phil Wilmarth, OHSU, 2013
    '''
    # get original file's access and modification times
    atime, mtime = os.stat(the_file).st_atime, os.stat(the_file).st_mtime
    
    # compress the file (read in chunks - old code ran out of memory on large files)
    with open(the_file, 'rb') as f, gzip.GzipFile(the_file + '.gz', mode='wb', mtime=mtime) as zipf:
        chunk = 1024 * 1024
        while True:
            block = f.read(chunk)
            if not block:
                break
            zipf.write(block)

    # set access, modification times on archive to original times
    os.utime(the_file + '.gz', (atime, mtime))

    # check contents of original and compressed files
    identical = True
    with open(the_file, 'rb') as f1, gzip.open(the_file + '.gz') as f2:
        chunk = 1024 * 1024
        while True:
            piece1 = f1.read(chunk)
            piece2 = f2.read(chunk)
            if not piece1:
                if piece2:
                    identical = False
                break
            if not piece2:
                if piece1:
                    identical = False
                break
            if piece1 != piece2:
                identical = False
                break
    if not identical:
        for obj in write:
            print >>obj, '......WARNING: %s and its GZip do not match' % (the_file,)

    # remove original if compression was successfull
    if identical:
        os.remove(the_file)
    return identical


def format_extension_list(ext_list):
    '''
    Formats "ext_list" by removing any starting '*' characters and adding '.'
    to the start of the extension if it is not present.

    Billy Rathje, OHSU, 2013
    '''
    ext_list = [x.lstrip('*.') for x in ext_list]   # NOTE lstrip() is tricky
    ext_list = [('.' + x).lower() for x in ext_list]
    return ext_list

def gzip_and_delete(path_to_project, size, write):
    '''
    Compresses all files larger than size and whose extensions do
    NOT appear in ext_list, then deletes them.
    '''
    g.progresstext.configure(text = "Compressing large files: " + os.path.basename(path_to_project))
    g.progressbar.update()
    zipped_file_log = None
    compress = format_extension_list(COMPRESS)
    do_not_compress = format_extension_list(DO_NOT_COMPRESS)
    for path, dirs, files in os.walk(path_to_project):
        for f in files:
            if ((os.stat(os.path.join(path, f)).st_size > size and GZIP_LARGE_FILES) or
                (os.path.splitext(f)[1].lower() in compress)):
                # Skip file if it's on the extension list
                if os.path.splitext(f)[1].lower() in do_not_compress:
                    continue
                else:
                    if not zipped_file_log:
                        zipped_file_log = open(os.path.join(path_to_project, 'gzipped_files.log'), 'a')
                        zipped_file_log.write(50*'=' + '\n')
                        zipped_file_log.write(' These files were compressed using GZip \n')
                        zipped_file_log.write(50*'=' + '\n\n')                       
                    the_file = os.path.join(path, f)
                    if gzip_file_inplace(the_file, write):
                        zipped_file_log.write(the_file + '\n')
                        for obj in write:
                            print >>obj, "...GZipped and deleted: " + the_file[len(root_folder):]
                    else:
                        for obj in write:
                            print >>obj, "......WARNING! File compression failed:", the_file[len(root_folder):]
    if zipped_file_log:
        zipped_file_log.close()

def cleanup_dta_out_files(path_to_project, success_list, write):
    """Checks project folder for any DTA or OUT files. If DTA/OUTs are found,
    a valid (same files) Zip archive is searched for. If no valid Zip, then
    creation of Zips are attempted. If there was a valid Zip (or one was successfully
    created), then DTA and OUT files are deleted.

    Phil Wilmarth, OHUS, 2013
    """
    project_name = os.path.basename(path_to_project)
    dta_folder_dict = {}    # key - container path, value - list of DtaOutFolderInfo objects
    zip_file_list = []      # list of all zip files in project folder (full paths)

    # look for Zip files and for DTA or OUT files
    g.progresstext.configure(text = "Scanning folder: " + project_name)
    g.progressbar.update()
    for path, dirs, files in os.walk(path_to_project):
        zip_file_list += [os.path.join(path, x) for x in files if x.lower().endswith('.zip')]
        if ([x for x in files if x.lower().endswith('.dta')] or
            [x for x in files if x.lower().endswith('.out')]):
            
            # get information about the folder
            try:
                params = [x for x in files if x.lower() == 'sequest.params'][0]
                params = os.path.join(path, params)
            except IndexError:
                for obj in write:
                    print >>obj, '......WARNING: no sequest.params file in:', path
                params = None
            new_info = DtaOutFolderInfo(path, len(files), params)

            # use the folder that contains the DTA/OUT folder as a dictionary key
            key = os.path.dirname(path)
            if len(key) < len(path_to_project):
                key = path_to_project  # make sure we stay inside the project folder
            if dta_folder_dict.has_key(key):
                dta_folder_dict[key].append(new_info)
            else:
                dta_folder_dict[key] = [new_info] # values are lists of DTA/OUT folder information objects

    # We now have all information about folders that contain DTA/OUT files and all Zip files
    # within the project folder. We want all DTA/OUT folders to have corresponding Zip archives.
    # A corresponding archive should have an identical sequest.params files. There may be zero,
    # one, or more than on possible archive for each DTA/OUT file. We also need a test results
    # dictionary to keep track of the results.
    g.progresstext.configure(text = "Checking archives: " + project_name)
    g.progressbar.update()
    for key in dta_folder_dict:
        for info in dta_folder_dict[key]:
            zip_test_list = [x for x in zip_file_list if os.path.basename(x)[:-4] == os.path.basename(info.dta_path)]
            for zip_file in zip_test_list:
                if check_archive(zip_file, info, path_to_project, write):
                    info.zip_path = zip_file

    # We now know which DTA/OUT folders have archives. We want to group together any
    # DTA/OUT folders located in the same folder. If any DTA/OUT folders in a group
    # do not have archives, we will try and create an archive.
    success_list.append(project_name)
    for key in dta_folder_dict:
        for info in dta_folder_dict[key]:
            if not info.zip_path:
                if zip_one_folder(info, path_to_project, write):
                    delete_dtas_outs(info.dta_path, success_list, write)
                else:
                    success_list = success_list[:-1]
                    for obj in write:
                        print >>obj, '......WARNING: cleaning up %s failed. Manual inspection required!' % (project_name,)
            else:
                delete_dtas_outs(info.dta_path, success_list, write)

        # need to make sure all the zip fles are in the correct location
        reconcile_zip_locations(dta_folder_dict[key], path_to_project, write)
                    
class DtaOutFolderInfo:
    """Holds some information about a folder that contains DTA and/or OUT
    files and its corresponding Zip archive.
    """
    def __init__(self, dta_path, file_count, params_path):
        self.dta_path = dta_path        # full path to folder containing DTA/OUT files
        self.dta_folder_name = os.path.basename(dta_path)   # name of folder with the DTA/OUT files
        self.container_path = os.path.dirname(dta_path)   # full path to container folder
        self.container_folder_name = os.path.basename(self.container_path) # container folder name
        self.file_count = file_count    # total number of files in the folder
        self.params_path = params_path  # full path to SEQUEST.PARAMS file
        self.zip_path = None            # full path to Zip archive location

    def _snoop(self):
        """Diognostic contents dump
        """
        print 'dta_path:', self.dta_path
        print 'dta_folder_name:', self.dta_folder_name
        print 'container_path:', self.container_path
        print 'container_folder_name:', self.container_folder_name
        print 'file_count:', self.file_count
        print 'params_path:', self.params_path
        print 'zip_path:', self.zip_path

    # end class

def reconcile_zip_locations(info_list, path_to_project, write):
    """Checks that all Zip files are located in one correct location,
    moving any if necessary.
    """
    # find any Zips that are not inside the DTA/OUT folders
##    print '\nDiagnostics:', path_to_project
##    for info in info_list:
##        info._snoop()
##    print
    zip_list = [x.zip_path for x in info_list if os.path.dirname(x.zip_path) != x.dta_path]
    zip_locations_to_remove = []

    if zip_list:
        # find the most frequent Zip location
        zip_frequency = {}
        for zip_path in zip_list:
            if zip_frequency.has_key(os.path.dirname(zip_path)):
                zip_frequency[os.path.dirname(zip_path)] += 1
            else:
                zip_frequency[os.path.dirname(zip_path)] = 1
        zip_freq_list = sorted([(y, x) for (x, y) in zip_frequency.items()], reverse=True)
        zip_folder = zip_freq_list[0][1]
        zip_locations_to_remove = [x[1] for x in zip_freq_list[1:]]
        if (len(zip_list) > 1) and not zip_locations_to_remove:
            return  # all Zips already in one folder
    else:
        # all zips are still inside DTA/OUT folders, create a folder to move them to (up 2 levels if possible)
        zip_folder_path = os.path.dirname(os.path.dirname(info_list[0].dta_path))
        if len(zip_folder_path) < len(path_to_project):
            zip_folder_path = path_to_project

        # use DTA/OUT folder container in Zip name (if possible, avoids name conflicts)
        container = os.path.dirname(info_list[0].dta_path)
        if len(container) < len(path_to_project):
            container = os.path.basename(path_to_project)
        else:
            container = os.path.basename(container)
        zip_folder = os.path.join(zip_folder_path, 'zip_of_' + container)

        # if Zip folder exists, make a time-stamped new folder
        if not os.path.exists(zip_folder):
            os.mkdir(zip_folder)
        elif [x for x in os.listdir(zip_folder) if x.lower().endswith('.zip')]: # folder is not empty
            x = time.localtime(time.time()) # get time stamp to append for new folder name
            zip_folder = '%s_%d%02d%02d' % (zip_folder, x.tm_year, x.tm_mon, x.tm_mday)
            for obj in write:
                print >>obj, '......NOTE: creating new folder:', zip_folder
            os.mkdir(zip_folder)

    # move any Zips not already in zip_folder
    for info in info_list:
        if os.path.dirname(info.zip_path) != zip_folder:
            try:
                os.rename(info.zip_path, os.path.join(zip_folder, os.path.basename(info.zip_path)))
            except WindowsError:
                for obj in write:
                    print >>obj, '......WARNING: problem moving archive (name conflict?)',
                    print >>obj, '.........From:', info.zip_path
                    print >>obj, '.........To:', os.path.join(zip_folder, os.path.basename(info.zip_path))
        try:    # try adding a sequest.params file (from container folder)
            shutil.copy2(os.path.join(os.path.basename(info.dta_path), 'sequest.params'),
                         os.path.join(zip_folder, 'sequest.params'))
        except IOError:
            pass

    # remove any empty Zip folders
    for folder in zip_locations_to_remove:
        if not os.listdir(folder):
            os.remove(folder)

    return
        
def check_archive(zip_file, info, path_to_project, write):
    """Checks if zip archive and its corresponding DTA/OUTs folder contents match.
    Returns True if match, False otherwise.
    """
    # do some basic archive testing first
    if zipfile.is_zipfile(zip_file):
        z = zipfile.ZipFile(zip_file)
    else:
        for obj in write:
            print >>obj, '......WARNING: %s is not a Zip file' % (zip_file[len(path_to_project):],)
            return False
    if z.testzip():
        for obj in write:
            print >>obj, '......WARNING: %s is corrupt' % (zip_file[len(path_to_project):],)
            z.close()
            return False
        
    # see if sequest.params file contents are not the same
    if info.params_path != None:
        try:
            archive_params = z.read(os.path.basename(info.params_path)).splitlines()    # end of line chars are a problem
        except KeyError:
            archive_params = ''
        with open(info.params_path, 'r') as f_params:
            original_params = f_params.read().splitlines() 
        if archive_params != original_params:
##            for obj in write:
##                print >>obj, '......%s is NOT an archive of %s' % (zip_file[len(path_to_project):],
##                                                                info.dta_path[len(path_to_project):])
            z.close()
            return False

    # If here, archive is a valid Zip file and sequest.params matched (or did not exist).
    # We will consider the archive a match if file attributes of archive and
    # folder contents match. We do not do a file-by-file contents check.
    z_namelist = z.namelist()
    z_infolist = z.infolist() # get list of information about files in archive
    
    # make tuples (name, size, truncated mod date) with some of the archive info
    z_tuples = [(x.filename, x.file_size, x.date_time[:3]) for x in z_infolist] # get file modification times (drop H,M,S)

    # get info about attributes of files in the folder
##    print 'diagnostics:'
##    print 'folder:', os.getcwd()
##    print 'number of files:', len(os.listdir('.'))
##    print 'info:'
##    info._snoop()
    f_namelist = []
    for f in os.listdir(info.dta_path):
        if os.path.isdir(f) or f[-4:] in (DO_NOT_COMPRESS + COMPRESS):
            continue    # skip subfolders and designated compress/skip files
        else:
            f_namelist.append(f)   # add file to file_list
    f_sizelist = [os.stat(os.path.join(info.dta_path,x)).st_size for x in f_namelist]   # file sizes in folder
    f_modtime = [time.localtime(os.stat(os.path.join(info.dta_path,x)).st_mtime)[:3] for x in f_namelist] # just use Y,M,D for modification times
    f_tuples = zip(f_namelist, f_sizelist, f_modtime)       # make tuples of info for files in folder

    # use set difference to test for identical attributes (empty set if identical)
    z_set = set(z_tuples)
    f_set = set(f_tuples)
    if z_set.symmetric_difference(f_set):
##        for obj in write:
##            print >>obj, '......%s is NOT an archive of %s' % (zip_file[len(path_to_project):],
##                                                            info.dta_path[len(path_to_project):])
        z.close()
        return False
    else:
        for obj in write:
            print >>obj, '......%s has an archive' % (info.dta_path[len(path_to_project):],)
        z.close()
        return True
            
def delete_all_dtas_outs(dta_files, success_list, write, confirm=False):
    '''
    delete_dtas_outs(dta_files, success_list, write)
    
    Recursively delete all dtas and outs in the directory
    dta_files

    Billy Rathje, OHSU, 2013
    '''
    if confirm:
        if not tkMessageBox.askyesno('Delete?', 'Delete dta files in ' + dta_files + '?'):
            for obj in write:
                print >>obj, '......WARNING: deleting DTA/OUT files cancelled for:', dta_files
                success_list = success_list[:-1]
            return

    g.progresstext.configure(text = "Deleting dtas/outs: " + dta_files)
    g.progressbar.update()
    for path, dirs, files in os.walk(dta_files):
        os.chdir(path)
        for dta in glob.glob('*.dta'):
            os.remove(dta)
        for out in glob.glob('*.out'):
            os.remove(out)
            
def delete_dtas_outs(dta_files, success_list, write, confirm=False):
    '''
    delete_dtas_outs(dta_files, success_list, write)
    
    Delete all dtas and outs in the directory dta_files

    Billy Rathje, OHSU, 2013
    '''
    if confirm:
        if not tkMessageBox.askyesno('Delete?', 'Delete dta files in ' + dta_files + '?'):
            for obj in write:
                print >>obj, '......WARNING: deleting DTA/OUT files cancelled for:', dta_files
                success_list = success_list[:-1]
            return

    g.progresstext.configure(text = "Deleting dtas/outs: " + os.path.basename(dta_files))
    g.progressbar.update()
    for obj in write:
        print >>obj, '......deleting DTA/OUT files in %s' % (os.path.basename(dta_files),)
    os.chdir(dta_files)
    for dta in glob.glob('*.dta'):
        os.remove(dta)
    for out in glob.glob('*.out'):
        os.remove(out)

def move_finished_projects(root_folder, success_list, write, confirm=False):
    """Moves all cleaned up projects in success_list to ARCHIVE_NAME for
    transfer to the archive RAID volume on the archive computer. root_folder
    is the folder where projects are located, write is the console and log file
    pointers list.

    Billy Rathje, OHSU, 2013
    """
    if confirm:
        st = '\n'
        for x in sorted(set(success_list)):
            st += x + '\n'
        if not tkMessageBox.askyesno('Ready?', 'Ready to move: ' + st + 'to ' + ARCHIVE_NAME + '?'):
##    if raw_input('Ready to move: ' + str(set(success_list)) + ' to ' + ARCHIVE_NAME + '(Y/N)?') == 'N':
            for obj in write:
                print >>obj, '......WARNING: Completed projects not moved to %s' % (ARCHIVE_NAME,)
                success_list = []
                return
        
    # Make archives folder if it does not exist
    os.chdir(root_folder)
    if ARCHIVE_NAME not in os.listdir('.'):
        for obj in write:
            print >>obj, '......WARNING: archive destination folder not found. New folder created.'
        os.mkdir(os.path.join(root_folder, ARCHIVE_NAME))

    # move projects into ARCHIVE_NAME folder
    for project in set(success_list):
        for obj in write:
            print >>obj, '...project moved:', os.path.join(root_folder, ARCHIVE_NAME, project)
        shutil.move(os.path.join(root_folder, project), os.path.join(root_folder, ARCHIVE_NAME, project))

def make_expired_list(root_folder, completed, ongoing, write):
    '''
    make_expired_list(folder_to_delete, completed, ongoing, write)
    
    Walks directories checking file modified dates. Returns a list of
    projects old enough to consider archiving and a list of more recent
    projects that will not be archived.

    Billy Rathje, OHSU, 2013
    '''
##        # Skip folders listed as ongoing projects, not yet expired, or the ARCHIVE folder
##        if project in ongoing or (project.lower() == (os.path.basename(ARCHIVE_NAME)).lower()):
##            continue

    os.chdir(root_folder)
    project_list = [x for x in os.listdir(root_folder) if os.path.isdir(x)]

    time_limit = EXPIRES * 24.0 * 60.0 * 60.0 # days in seconds
    now = time.time()
    not_expired_list = []
    expired_list = []
    for obj in write:
        print >>obj, '\nChecking project folder modification dates:'
    for project in project_list:
        if project in (completed + ongoing + [os.path.basename(ARCHIVE_NAME)]):
            continue
        if (now - os.stat(project).st_mtime) < time_limit:
            not_expired_list.append(project)
            for obj in write:
                print >>obj, '...%s is not yet expired. Skipping archiving.' % project
        else:
            expired_list.append(project)
            for obj in write:
                print >>obj, '...%s old enough to be considered for archiving.' % project

    return expired_list, not_expired_list
    
def process_projects(root_folder, completed, ongoing, write):
    '''
    process_projects(root_folder, completed, ongoing)
    
    Loops over completed projects, removes un-needed DTA and OUT files
    (if they have been archived) or archives then deletes DTA/OUT files.
    Also compresses (in-place GZip) specified or large files.

    Billy Rathje, OHSU, 2013
    '''
    os.chdir(root_folder)
    project_list = [x for x in os.listdir(root_folder) if x in completed] # get list of projects
    project_list = [x for x in project_list if (x.lower() != (os.path.basename(ARCHIVE_NAME)).lower())] # skip ARCHIVE folder
    success_list = []   # list of project names (basenames) successfully cleaned up and moved

    # echo list of projects to be processed to console and log file
    for obj in write:
        print >>obj, '\nThe following projects will be processed:'
    for project in project_list:
        for obj in write:
            print >>obj, '...%s' % (project,)

    # Walk top level project folders
    step = 100/len(project_list)
    for project in project_list:
        # Progress bar
        g.progressbar.update()
        g.progressbar.step(step)
        
##        # Skip folders listed as ongoing projects, not yet expired, or the ARCHIVE folder
##        if project in ongoing or (project.lower() == (os.path.basename(ARCHIVE_NAME)).lower()):
##            continue

        # console and log file message
        for obj in write:
            print >>obj, '\nProcessing: %s' % (project,)

        # Progress bar
        g.progresstext.update()
        g.progresstext.config(text = 'checking %s for DTA and OUT files' % (project,))

        # Clean project folder
        cleanup_dta_out_files(os.path.join(root_folder, project), success_list, write)
            
        # Finally, zip and delete any large files in any project folder that
        # has been checked. Ignore project folders that failed the check.
        gzip_and_delete(os.path.join(root_folder, project), SIZE_THRESHOLD, write)

    # move successfully archived projects to ARCHIVE folder
    if MOVE_FILES:
        move_finished_projects(root_folder, success_list, write)

    # Done
    for obj in write:
        print >>obj, ''
        if not MOVE_FILES:
            print >>obj, 'WARNING: These projects are sill in original locations!'
    for project in sorted(set(success_list)):
        for obj in write:
            print >>obj, project, 'is ready to be archived'

    os.chdir(root_folder)
    return success_list

def parse_project_lists(path_to_project_lists, root_folder, write):
    '''
    parse_project_lists(path_to_project_lists, root_folder)

    Parses file "Project_Lists.txt" for projects ready to check and projects
    not to check.

    Billy Rathje, OHSU, 2013
    '''
    completed = []
    ongoing = []
    if not os.path.exists(path_to_project_lists) or os.path.isdir(path_to_project_lists):
        return completed, ongoing
    with open(path_to_project_lists, 'r') as project_lists:
        for obj in write:
            print>>obj, 'Reading: ' + path_to_project_lists
        IN_COMPLETED = False
        IN_ONGOING = False
        
        for line in project_lists.readlines():
            line = line.strip()
            # Skip blank lines
            if not line: continue
            # Skip comment lines unless they designate parse areas
            if line.startswith('#'):
                if 'COMPLETED' in line:
                    IN_COMPLETED = True
                if 'ONGOING' in line:
                    IN_COMPLETED = False
                    IN_ONGOING = True
                else:
                    continue
            # else line is a project name (can contain tailing comments) or a comment line
            else:
                line = line.split('#')[0].strip()
                if IN_COMPLETED and line:
                    completed.append(line)
                if IN_ONGOING and line:
                    ongoing.append(line)

        for obj in write:
            print >>obj, '...completed projects:'
            for proj in sorted(completed):
                print >>obj, '......%s' % proj
            print >>obj, '...ongoing projects:'
            for proj in sorted(ongoing):
                print >>obj, '......%s' % proj

        # Check that all project names exist at top level in root_folder
        to_remove = []  # cannot remove items from a list while it is being iterated on
        for project in sorted(completed+ongoing):
            if os.path.exists(os.path.join(root_folder, project)):
                continue
            else:
                to_remove.append(project)
                for obj in write:
                    print>>obj, '...WARNING: ' + project + ' could not be found.'
                    
        # remove any projects that could not be found                   
        for project in to_remove:
            try:
                completed.remove(project)
            except ValueError:
                ongoing.remove(project)

        # remove any projects in both completed and ongoing from completed list and warn the user
        to_remove = []
        for project in completed:
            if project in ongoing:
                to_remove.append(project)
                
        for project in to_remove:
            completed.remove(project)
            for obj in write:
                print >>obj, '...WARNING:', project, 'in completed and ongoing list. Removing from completed.' 
                    
        for obj in write:
            print>>obj, 'Done reading: ', path_to_project_lists
            
        return completed, ongoing

def clean_project_lists(path_to_project_lists, success_list, write):
    '''
    clean_project_lists(path_to_project_lists, success_list)

    Removes any sucessfully archived project names from the completed
    projects section of project lists file

    Billy Rathje, OHSU, 2013
    '''
    if os.path.isdir(path_to_project_lists):
        print '...WARNING: project_lists file not valid'
        return
    with open(path_to_project_lists, 'r') as project_lists:
        for obj in write:
            print>>obj, '\nCleaning: ' + path_to_project_lists
        file_list = project_lists.readlines()

#    success_list = [os.path.basename(x) for x in success_list]

    with open(path_to_project_lists, 'w') as project_lists:
        for line in file_list:
            if line.split('#')[0].strip() not in success_list:
                project_lists.write(line)

    for obj in write:
        print>>obj, 'Done cleaning: ' + path_to_project_lists

#================================================================================
# Project Archiver main program
#================================================================================
"""This is now skipped to support more than one analysis volume on a computer"""
# Gui window for user to locate the root folder for processing
root_folder = get_folder(DEFAULT)
if root_folder == '':
    sys.stderr = None
    sys.stdout = None
    sys.exit()

with open(os.path.join(root_folder, 'project_archiver.log'), 'a') as log_obj:
    write = [None, log_obj] # console and log file
    
    # message to user and timestamp
    for obj in write:
        print >>obj, '\n======================================================='
        print >>obj, ' Project_archiver.py, ver 1.0, OHSU 2013, Billy Rathje '
        print >>obj, '======================================================='
        print >>obj, '     Ran on:', str(time.ctime()), '\n'
        print >>obj, 'Root folder:', root_folder

    # populate user maintained completed and ongoing project lists
    completed, ongoing = parse_project_lists(PATH_TO_PROJECT_LISTS, root_folder, write)

    # find more recent projects that will not be archived at this time
    expired_list, not_expired_list = make_expired_list(root_folder, completed, ongoing, write)

    # launch GUI window for user control over archiving (pass along write for logging)
    g = GUI(completed, ongoing, not_expired_list, expired_list, root_folder, write)
    g.gui_go()
    
