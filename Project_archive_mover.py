"""
Archive_mover.py
Facilitates moving archived projects from analysis computers
to a dedicated storage computer for long term archival- 8/22/2013, BR

Copies files in an archive folder onto the pocket drive or a RAID backup
volume. Checks to make sure copy was successful, repeats if it
was not. Deletes all successfully moved files. Also organizes multiple
analyses of the same project into sub-project folders, keeping the top level
of the archive folder cleaner. Also checks for duplicate files in situations
where likelihood of 

Billy Rathje, OHSU, 2013
finished by Phil Wilmarth, OHSU, 2013.
"""

import os
import sys
import shutil
import filecmp
import subprocess
import platform
import hashlib
import time
import re
import win32api

from Tkinter import *
import tkMessageBox
import tkFileDialog

# Set paths for each computer HERE:
# these are the important data structures with volume names (not letters which change), and folder names.
# These two data structures should be in sync. Note that the "psr_core_-690" computer has a longer tuple.
VOLUME_NAMES = {'psrcore-mrba608': ('PSR_Data_Volume', 'LaCie'),
                'psrcore-mrba610': ('PSR_Data_Volume', 'LaCie'),
                'psrcore-mrba611': ('PSR_Data_Volume', 'LaCie'),
                'psr_core-690': ('LaCie', 'PSR_RAID_7', 'BUP_PSR_RAID_7')}

FOLDER_NAMES = {'psrcore-mrba608': ('PSR_Core_Analysis', 'from_608'),
                'psrcore-mrba610': ('PSR_Core_Analysis', 'from_610'),
                'psrcore-mrba611': ('PSR_Core_Analysis', 'from_611'),
                'psr_core-690': ('', 'Projects_20180614-present', 'Projects_20180614-present')}

ARCHIVE_NAME = 'zzz_TO_ARCHIVE'

### NOTE: These types of tuples are now computed since drive letters are not always constant
### (source, destination) folder names for each computer (put in typical pocket drive letters)
##COMPUTERS = {'analysis_5': (r'D:\PSR_Core_analysis', r'G:\from_4'),
##             'newdatapc': (r'D:\Temp_Data_Analysis', r'H:\from_3'),
##             'analysis_4': (r'D:\PSR_Core_analysis', r'G:\from_2'),
##             'analysis_6': (r'D:\PSR_Core_analysis', r'H:\from_1'),
##             'psrcore-mrba608': (r'F:\PSR_Core_Analysis', r'G:\from_608'),
##             'psrcore-mrba610': (r'F:\PSR_Core_Analysis', r'G:\from_610'),
##             'psrcore-mrba611': (r'F:\PSR_Core_Analysis', r'E:\from_611'),
##             'psr_core-690': (r'Q:', r'K:\Projects_20141224-present')}

##ARCHIVE_BACKUP = r'H:\Projects_20141224-present'   # location of RAID volume backup (computed now)

def no_hidden(files):
    """Removes files that start with periods.
    """
    return([x for x in files if not x.startswith('.')])

def print_error(log_file_list, error, left_path, right_path):
    """Prints any errors being trapped.
    """
    for obj in log_file_list:
        print >>obj, 80*"="
        print >>obj, 'WARNING:', left_path
        print >>obj, '...', right_path
        print >>obj, error
        print >>obj, 80*"="

def compare_directories(left, right, write, CHECK_CONTENTS=True):
    """Compares two folders for identical contents.

    written by Phil Wilmarth, OHSU, 2013.
    """
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
            # Return Flase if any differences, else True
            if left_only or right_only or common_funny or diff_files \
               or funny_files or mismatch or errors:
                return False
            else:
                return True
                    
        # report IOError or OSError and continue
        except IOError, e:
            print_error(write, e, left, right)
        except OSError, e:
            print_error(write, e, left, right)

        return False
    
def calc_md5_hash(file_path):
    """Taken from: http://stackoverflow.com/questions/18538201/python-script-throws-memory-error
    Calculates hashes on large files.
    """
    md5hash = hashlib.md5()
    with open(file_path, 'rb') as file_to_check:
        for chunk in iter(lambda: file_to_check.read(4096), ''):
            md5hash.update(chunk)

    return md5hash.hexdigest()

def find_duplicates(root, write):
    """Finds duplicate files in a root directory. Returns folders containing duplicates.
    Algorithm adapted from:
        http://www.endlesslycurious.com/2011/06/01/finding-duplicate-files-using-python/

    Does a 3-pass search for duplicate files. First pass are files that
    are the same size. Second pass is files with identical MD5 hashes. Third
    pass is checking actual file contents.


    Billy Rathje, OHSU, 2013
    Phil Wilmarth, OHSU, 2013
    """
    if not os.path.exists(root):
        for obj in write:
            print >>obj, '...WARNING: folder not found!'
        return
    
    # Makes a dictionary of list of files of identical size, file size is the key
    filesizes = {}
    for path, dirs, files in os.walk(root):
        for f in files:
            fpath = os.path.join(path, f)
            filesizes.setdefault(os.stat(fpath).st_size, []).append(fpath)
    # Remove any single entry lists - file size is unique so it is not a duplicate file
    filesizes_list = [f for f in filesizes.values() if len(f) > 1]


    # Hash all cases where file sizes are the same. Uses dictionary with hash as key.
    hashed_files = {}
    for f in filesizes_list:
        for fpath in f:
            # skip SEQUEST.PARAMS files (we have lots of duplicates that are OK)
            if os.path.basename(fpath).upper() == 'SEQUEST.PARAMS':
                continue
            # Add to dictionary of files with the same hashes
            hashed_files.setdefault(calc_md5_hash(fpath), []).append(fpath)
    # Remove any single entry lists - MD5 hash is unique so it is not a duplicate file
    hashed_files = [x for x in hashed_files.values() if len(x) > 1]

    # now check actual file contents for identity
    duplicate_files = []
    for possible_list in hashed_files:
        test_list = list(possible_list)     # make a copy of the file list
        while test_list:
            first = test_list[0]
            same = [first]  # list of true duplicates
            diff = []       # list of other non-identical files
            for other in test_list[1:]:     # compare first to the rest
                if filecmp.cmp(first, other, False):
                    same.append(other)  # other is a duplicate
                else:
                    diff.append(other)  # other is different
            if len(same) > 1:
                duplicate_files.append(same)
            if len(diff) > 1:
                test_list = list(diff)  # diff list also needs to be tested for duplcates
            else:
                test_list = []          # this ends the while loop

    # open a log file in root if duplicates
    if duplicate_files:
        dup_log_obj = open(os.path.join(root, 'Duplicate_files.log'), 'w')
        write.append(dup_log_obj)

    for obj in write:
        print >>obj, '+..Duplicate checking in:', root
    dup_tot_size = 0
    orig_tot_size = 0
    for duplicate_list in duplicate_files:
        if duplicate_list[0].lower().endswith('.apar'):     # skip MaxQuant apar files
            continue
        for obj in write:
            print >>obj, '+.....%s has duplicates:' % (os.path.basename(duplicate_list[0]),)
        orig_tot_size += os.stat(duplicate_list[0]).st_size
        for duplicate in duplicate_list:
            for obj in write:
                print >>obj, '+........%s' % (duplicate.replace(root, '~'),)
            dup_tot_size += os.stat(duplicate).st_size

    if duplicate_files:
        for obj in write:
            print >>obj, '  [%0.2f MB wasted in duplicates]' % ((dup_tot_size - orig_tot_size)/1024.0/1024.0,)
        write.remove(dup_log_obj)
        dup_log_obj.close()
            
    # return list of lists of duplicates
    return duplicate_files

def get_folder(default, message='Select a Directory'):
    """Puts up dialog box to browse to a folder -
    'default' is the default location.

    written by Phil Wilmarth, OHSU, 2011.
    """
    root = Tk()
    root.withdraw()
    folder_path = tkFileDialog.askdirectory(parent=root,initialdir=default,\
                                       title=message)
    return(folder_path)

def check_path_lengths(source, destination, write):
    """Checks if any paths in source will exceed maximum path
    length (260 chars) if moved to destination. Prints warnings
    and bad paths. Returns True of False accordingly. source and
    destination must be full paths.

    written by Phil Wilmarth, OHSU, 2013.
    """
    print '\n#################################'
    print 'inside path length checker module'
    print 'source:', source
    print 'destination:', destination
    print 'path length difference:', (len(destination)-len(source))
    exceed_max = False
    longest = 0
    new_diff = len(destination) - len(source)
    for path, dirs, files in os.walk(source):
        for f in files:
            if (len(os.path.join(path, f)) + new_diff) > longest:
                longest = len(os.path.join(path, f)) + new_diff
                if longest >= 259:
                    print '...filename will be too long', longest
                    exceed_max = True
                    for obj in write:
                        print >>obj, '\n', 50*'#'
                        print >>obj, '...WARNING: file path will exceed maximum after move'
                        print >>obj, '......', os.path.join(path, f).lstrip(source)
                        print >>obj, 50*'#', '\n'
                        break
    print 'longest path was:', longest
    return exceed_max    

def get_folder_size(folder):
    '''
    Returns the size of folder in MB.
    
    Billy Rathje, OHSU, 2013
    '''
    size = 0
    for path, dirs, files in os.walk(folder):
        for f in files:
            size += os.stat(os.path.join(path, f)).st_size
    return float(size)/1024/1024

def get_volume_free_space(volume):
    ''' Returns free space on disk 'volume'

    Billy Rathje, OHSU, 2013
    '''
    volume = os.path.splitdrive(volume)[0]                              

    
    # Ensures we are passing in a character and a : only. See below.
    if len(volume.rstrip(':')) != 1:
        sys.exit(1)
    
    # NOTE: Setting shell = True is *potentially* dangerous if input parameters
    # are not trusted because it can lead to shell injections running arbitrary commands.
    # The classic example is to supply something like: ['cd', 'file; rm -rf /'].
    # I'll check the inputs - I think the odds of bad input is really low since we set the flag
    # for volume. Worst case there's another module in ctypes                   
    # that may be able to do the free space check.
    stdout = subprocess.Popen(['dir', volume], shell = True, stdout = subprocess.PIPE)
    stdout, stderr = stdout.communicate()
    stdout = stdout.split('bytes free')[0].split()
    size = float(stdout[-1].replace(',', '')) # Get the number at the end
    return size/1024/1024

def copy_project_folder(from_project, to_project, write, success_list, move=False):
    """Copies one project folder contents from "from_project" to "to_project".
    "from_project" and "to_project" should be full paths. Original and copy
    are compared for identity and up to 3 retries are attempted. Failure
    triggers a hard program exit!

    written by Billy Rathje and Phil Wilmarth, OHSU, 2013.
    """
    # next-to-last safety check - we still have a name conflict to resolve
    if os.path.exists(to_project):                              
        if compare_directories(from_project, to_project, write):
            for obj in write:
                print >>obj, '...WARNING:', os.path.basename(from_project), 'has already been archived.\n'
            success_list.append(os.path.basename(from_project))
            return
        else:
            to_project = to_project + '_2'

    # last safety check - make sure new path lengths do not exceed maximum length
    do_not_copy = check_path_lengths(from_project, to_project, write)
    if do_not_copy:
        for obj in write:
            print >>obj, '...WARNING: %s was NOT copied' % os.path.basename(from_project)
            print >>obj, '......Some file path names are too long! Manually fix then manually archive.\n'
        reply = raw_input('>>> Continue with moving (y or n)? ')
        if reply.lower().startswith('n'):
            sys.exit(0)

    # should be safe to try and copy now
    if not do_not_copy:
        shutil.copytree(from_project, to_project)

        TRY_COUNT = 3
        i = 0
        while (not compare_directories(from_project, to_project, write)) and (i < TRY_COUNT):
            for obj in write:
                print >>obj, '...WARNING: file copy did not occur successfully... retrying...'
                print >>obj, '......(Try %i of %i )' % (i, TRY_COUNT)
            shutil.rmtree(to_project)
            time.sleep(5)
            shutil.copytree(from_project, to_project)
            i += 1                              

        if i > 2:
            for obj in write:
                print >>obj, '...WARNING: Unable to copy folder ' + from_project
                print >>obj, '...Exiting!'
            sys.exit(0)
        else:
            if move:
                shutil.rmtree(from_project)
                for obj in write:
                    print >>obj, '...%s moved to:\n......%s' % (from_project, to_project)
            else:
                for obj in write:
                    print >>obj, '...%s copied to:\n......%s' % (from_project, to_project)
                success_list.append(os.path.basename(from_project))

    return                             


def copy_all_project_folders(from_folder, to_folder, write):
    '''

    Copies all project folders in from_folder to to_folder.
 
    Billy Rathje, OHSU, 2013
    '''
    project_list = [x for x in os.listdir(from_folder) if os.path.isdir(os.path.join(from_folder, x))]

    if project_list:
        for obj in write:
            print >>obj, '...Moving these projects in %s:' % from_folder
            for p in project_list:
                print >>obj, '......%s' % p
            print >>obj, '...To: %s' % to_folder
        
    dummy = []
    for project in project_list:
        copy_project_folder(os.path.join(from_folder, project),
                            os.path.join(to_folder, project), write, dummy)
    return

def clean_out_previous_projects(folder, log_file_path, write, mode):
    """Removes any projects logged to the successfully moved log file.
    "log_file_path" is path to location of the successfully archived log file.

    written by Phil Wilmarth, OHSU, 2013
    """
    try:
        with open(os.path.join(log_file_path, 'Archive_mover_success.log')) as infile:
            contents = infile.readlines()
    except IOError:
        print '...WARNING: Archive_mover_success.log not found'
        return  # no file present so nothing to do

    # skip to the last set of project names
    start = 0
    for i, line in enumerate(contents):
        if line.strip().startswith('#'):
            start = i

    # parse out the project names
    success_list = []
    for line in contents[start:]:
        project = line.split('#')[0].strip()
        if project:
            success_list.append(project)

    # get list of projects in folder ("zzz_TO_ARCHIVE" or pocket drive)
    project_list = [x for x in os.listdir(folder) if os.path.isdir(os.path.join(folder, x))]

    if project_list:
        for obj in write:
            print >>obj, '\n...Cleaning up:', folder

        # delete any that are in the success list
        del_count = 0
        for project in project_list:
            if project in success_list:
                shutil.rmtree(os.path.join(folder, project))
                del_count += 1
                for obj in write:
                    print >>obj, '......deleting:', project

        # update success log file when original projects are deleted from analysis computers
        if mode == 'TO_POCKET_DRIVE' and del_count > 0:
            with open(os.path.join(log_file_path, 'Archive_mover_success.log'), 'a') as logfile:
                logfile.write(50*'#' + '\n')
                logfile.write('#    ' + time.ctime() + '\n')
                logfile.write(50*'#' + '\n')
                logfile.write('# %s projects deleted in zzz_TO_ARCHIVE\n' % del_count)
                          
    return

def get_basenames(project_name):
    """Splits on common separators and
 returns a list of project codes.
    The lists can have zero, one, or more than one project code.

    written by Phil Wilmarth, OHSU, 2013.                              

    """
    # split on common separators (any non letter/number)
    items = re.split(r'[^a-zA-Z0-9\-]', project_name)   # iLab uses "dash" in project codes (no longer splits on those)

    # look for project code patterns (2-4 letters; optional dash; followed by 2-4 numbers)
    projects = []
    for item in items:
##        match_list = re.findall(r'\b[a-zA-Z]{3}[0-9]{3,4}\b', item)
        match_list = re.findall(r'\b[a-zA-Z]{2,4}-?[0-9]{2,4}', item) # updated for iLab formats; Deb used lower case letters as suffixes w/o separators
        projects += match_list
                     
    return projects

def create_container_folder(existing_path, write):

    """Time stamps "existing_path", creates a container folder, and moves
    time-stamped folder into container. Returns container path.

    written by Phil Wilmarth, OHSU, 2013.
    """
    # time stamp existing folder
    new_existing = time_stamp_folder(existing_path)
    new_existing_path = os.path.join(os.path.dirname(existing_path),
                                     time_stamp_folder(existing_path))
    i = 2
    while i < 100:      # extra check since time stamp may not be unique
        if os.path.exists(new_existing_path):
            suffix = '_%d' % i
            new_existing_path = new_existing_path + suffix
            i += 1
        else:
            break
    print 'old name:', existing_path
    print 'new name:', new_existing_path
    os.rename(existing_path, new_existing_path)

    # create container folder
    if len(get_basenames(existing_path)) == 1:
        existing_basename = get_basenames(existing_path)[0]
    else:
        existing_basename = os.path.basename(existing_path)
    container = os.path.join(os.path.dirname(existing_path), existing_basename)
    os.mkdir(container)
    with open(os.path.join(container, 'container_folder.txt'), 'w') as fout:
        fout.write('This is a complex project container folder.\n')

    # move time-stamped existing folder into container folder
    dummy = []
    copy_project_folder(new_existing_path, os.path.join(container, new_existing),
                        write, dummy, move=True)                    
    for obj in write:
        print >>obj, '...WARNING: creating new base project folder to avoid conflicts'
        print >>obj, '......%s renamed to %s' % (os.path.basename(existing_path), new_existing)
        print >>obj, '......%s moved to %s' % (os.path.basename(existing_path),
                                               os.path.join(existing_basename, new_existing))

    return container
                                                              
def copy_projects_with_conflict_check(from_here, to_here, write, logfileflag=True):
    """Copies projects from pocket drive to RAID location.
    Makes sure that multiple analyses of same project end up
    as subprojects within the main project folder. Also traps
    the same project trying to replace itself. Uses time stamps
    to distinguish analyses.
    
    written by Phil Wilmarth, OHSU, 2013.
    """
    success_list = []
    
    # get lists of incoming projects and lists of existing projects
    incoming_projects = [x for x in os.listdir(from_here) if os.path.isdir(os.path.join(from_here, x))]

    # loop over projects and test for collisions                          
    for project in incoming_projects:
        existing_projects = [x for x in os.listdir(to_here) if os.path.isdir(os.path.join(to_here, x))]
        existing_basenames = [get_basenames(x)[0] for x in existing_projects if len(get_basenames(x)) == 1]
        # extract project codes from project names (if any)
        if len(get_basenames(project)) == 1:     # single project code found
            incoming = get_basenames(project)[0]
        else:   # non-standard name or meta analysis (multiple projects)
            incoming = None

        # if no name collision, add project to the archive volume
        collision = False
        if incoming in existing_basenames or project in existing_projects:
            collision = True
        if not collision:            
            copy_project_folder(os.path.join(from_here, project),
                                os.path.join(to_here, project), write, success_list)
            success_list.append(project)
            
        # name collision so resolve conflict - check if destination is already a container folder            
        else:
            incoming_path = os.path.join(from_here, project)
            existing_path = None
            # look for existing folder with same name as incoming project
            match = 0
            for existing in existing_projects:
                if project == existing: 
                    existing_path = os.path.join(to_here, existing)
                    print '\nConflict with full name:', existing
                    match += 1
            if match > 1:
                print 'WARNING: project matched multiple:', project
                
            # next look for basename conflicts
            if not existing_path:
                match = 0
                for existing in existing_projects:
                    if len(get_basenames(existing)) == 1:
                        basename = get_basenames(existing)[0]
                    else: # need to trap when there is not a single basename
                        basename = None
                        print 'existing:', existing
                        print 'basenames:', get_basenames(existing)
                    if incoming == basename:
                        existing_path = os.path.join(to_here, existing)
                        print '\nConflict with basename:', existing
                        match += 1
                if match > 1:
                    print 'WARNING: incoming matched multiple:', incoming
                    """
                    Need to add some logic here to deal with this case
                    """

            # existing is not a container folder with subprojects
            if not os.path.exists(os.path.join(existing_path, 'container_folder.txt')):

                # see if incoming is a duplcate of existing
                if compare_directories(incoming_path, existing_path, write):
                    duplicate = True
                    
                # incoming folder different: create container folder, move into container
                else:
                    duplicate = False
                    container = create_container_folder(existing_path, write)
                    
            # existing is a container with subprojects
            else:
                # get list of subproject folders
                container = existing_path
                subproject_list = [x for x in os.listdir(container) if os.path.isdir(os.path.join(container, x))]

                # see if incoming is a duplicate of any existing subprojects
                duplicate = False
                for subproject in subproject_list:
                    if compare_directories(incoming_path, os.path.join(container, subproject), write):
                        duplicate = True
                        break

            # do not copy if duplicate, warn user
            if duplicate:                
                for obj in write:
                    print >>obj, '...WARNING:', project, 'has already been archived'
                success_list.append(project)

            # OK to copy incoming with time stamp to container folder and then check for duplicates                
            else:
                new_incoming = time_stamp_folder(incoming_path)
                copy_project_folder(incoming_path, os.path.join(container, new_incoming),
                                    write, success_list)
                find_duplicates(container, write)

    # update success log file on pocket drive
    if logfileflag:
        with open(os.path.join(from_here, 'Archive_mover_success.log'), 'a') as logfile:
            if success_list:
                success_list = sorted(list(set(success_list))) # trying to remove duplicates
                logfile.write(50*'#' + '\n')
                logfile.write('#    ' + time.ctime() + '\n')
                logfile.write('#    %s projects were sucessfully archived\n' % len(success_list))
                logfile.write(50*'#' + '\n')
                for success in success_list:
                    logfile.write(success + '\n')
                logfile.write('\n')

def check_file_dates(folder, creation=True):
    """Returns oldest and newest dates of all files in folder walk.
    Dates can be creation dates or modification dates (creation=False).
    Returns (oldest, newest) as floating point time in seconds since epoch.

    written by Phil Wilmarth, OHSU, 2013.
    """
    oldest = time.time()
    newest = 0
    
    for path, dirs, files in os.walk(folder):
        for f in files:
            if creation:
                _time = os.stat(os.path.join(path, f)).st_ctime
            else:
                _time = os.stat(os.path.join(path, f)).st_mtime
            if _time > newest:
                newest = _time
            if _time < oldest:                              
                oldest = _time

    return oldest, newest
                          
def time_stamp_folder(folder):
    """Gets oldest and newest file dates (either creation or modification)
    and adds an appropriate time stamp to the basename from "folder".
    "folder" should be a full path.

    written by Phil Wilmarth, OHSU, 2013.
    """
    oldest, newest = check_file_dates(folder, creation=False)
    x = time.localtime(oldest)
    old = '_%04d%02d%02d' % (x.tm_year, x.tm_mon, x.tm_mday)
    x = time.localtime(newest)
    new = '_%04d%02d%02d' % (x.tm_year, x.tm_mon, x.tm_mday)

    return os.path.basename(folder) + new                          
               
def main():
    """Main function of Archive_mover.py
    """
##    global ARCHIVE_BACKUP
    global VOLUME_NAMES
    global FOLDER_NAMES
    global ARCHIVE_NAME
    # get name of computer where program is running (network name)
    computer_name = platform.node().lower()
    
    # drive letters can change so we will update above information dynamically
    drive_letters = win32api.GetLogicalDriveStrings().split('\00')     # list of all mounted volumes on current computer
    drive_map = {}
    for drive in drive_letters:
        try:
            drive_map[win32api.GetVolumeInformation(drive)[0]] = drive
        except:
            pass

    # get source location and test if OK
    from_folder = os.path.join(drive_map[VOLUME_NAMES[computer_name][0]], FOLDER_NAMES[computer_name][0])
    print 'from_folder:', from_folder
    from_folder = get_folder(from_folder, 'Please select main folder to process')
    if not from_folder: sys.exit(1)    # cancel response
    if computer_name != 'psr_core-690':
        from_folder = os.path.join(from_folder, ARCHIVE_NAME)
        if not os.path.exists(from_folder):
            print 'ERROR:', from_folder, 'does not exist!'
            sys.exit(1)

    # get destination location and test if OK
    to_folder = os.path.join(drive_map[VOLUME_NAMES[computer_name][1]], FOLDER_NAMES[computer_name][1])
    print 'to_folder:', to_folder
    if not os.path.exists(to_folder):
        to_folder = get_folder(os.getcwd(), 'Please select location to copy files to')
    if not to_folder: sys.exit(1)    # cancel response

    # set mode and log file location (outgoing transfer or incoming transfer)
    if computer_name == 'psr_core-690':
        MODE = 'FROM_POCKET_DRIVE'
        log_obj = open(os.path.join(to_folder, 'Archiver_mover_console.log'), 'a')
    else:
        MODE = 'TO_POCKET_DRIVE'
        log_obj = open(os.path.join(from_folder, 'Archiver_mover_console.log'), 'a')
    write = [None, log_obj]

    if MODE == 'FROM_POCKET_DRIVE':        
        # make sure backup volume is ready
        ARCHIVE_BACKUP = os.path.join(drive_map[VOLUME_NAMES[computer_name][2]], FOLDER_NAMES[computer_name][2])
        print 'backup_folder:', ARCHIVE_BACKUP
        if not os.path.exists(ARCHIVE_BACKUP):
            print ARCHIVE_BACKUP, 'does not exist'
            ARCHIVE_BACKUP = get_folder(os.getcwd(), 'Please select RAID backup folder')
        if not ARCHIVE_BACKUP: sys.exit(1)

    for obj in write:
        print >>obj, '\n================================================================='
        print >>obj, ' Archive mover utility v1.0, written by Billy Rathje, OHSU, 2013 '
        print >>obj, '================================================================='
        print >>obj, 'Ran on:', str(time.ctime())

    if MODE == 'TO_POCKET_DRIVE':
        # remove any successfully transferred projects from previous run
        clean_out_previous_projects(from_folder, to_folder, write, MODE)

        # copy files onto pocket drive if there is enough free space
        if get_folder_size(from_folder) < get_volume_free_space(to_folder):
            # Copy files from zzz_TO_ARCHIVE to pocket drive/from_n
            copy_all_project_folders(from_folder, to_folder, write)
        else:
            for obj in write:
                print >>obj, 'Not enough space on destination volume to copy projects. Aborting.'
                print >>obj, 'Projects are %i MB, destination volume has %i MB free.' % (get_folder_size(from_folder),get_volume_free_space(to_folder))

    if MODE == 'FROM_POCKET_DRIVE':        
        # List of folders on pocket drive (should be four - one per computer)
##        system_files = ['$RECYCLE.BIN', 'RECYCLER', 'System Volume Information']
##        folders_on_pocket_drive = [os.path.join(from_folder,x) for x in os.listdir(from_folder)
##                                   if os.path.isdir(os.path.join(from_folder,x)) and x not in system_files]
        folders_on_pocket_drive = [os.path.join(from_folder, x) for x in os.listdir(from_folder)
                                   if os.path.isdir(os.path.join(from_folder,x)) and x.startswith('from_')]
        
        # Get the combined size of all folders
        size = 0
        for folder in folders_on_pocket_drive:
                size += get_folder_size(folder)
                
        if size < get_volume_free_space(to_folder):
                              
            # Copy files from all folders on pocket drive to RAID location
            for folder in folders_on_pocket_drive:
                for obj in write:
                    print >>obj, '\nProcessing:', folder
                
                # copy to RAID volume
                copy_projects_with_conflict_check(folder, to_folder, write)        

                # copy to RAID backup also. This makes sure all folder renames and moves stay in sync
                copy_projects_with_conflict_check(folder, ARCHIVE_BACKUP, write, logfileflag=False)

                # remove successfully achived projects from pocket drive
                clean_out_previous_projects(folder, folder, write, MODE)                         
        
        else:
            for obj in write:
                print >>obj, 'Not enough space on destination volume to copy projects. Aborting.'
                print >>obj, 'Pocket drive has %i MB of data, dest. volume has %i MB free.' % (size, get_volume_free_space(to_folder))
    try:
        log_obj.close()
    except:
        pass
    return

if __name__ == '__main__':
    main()
