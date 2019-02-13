# utilities
Some Python utility scripts for proteomics file management

Collection of tools for some basic proteomics file management activities.

## compare_directories.py
Recursively compares two folders or drives. File contents can be compared for identity or just file names and attributes (faster). Provides information about higher-level differences. A text log file is created in the location with the script. Log information is appended to the log file.

## copy_raw_files.py
Instrument RAW files can be large and can sometimes have errors when being copied. This script will copy files, check the original and the copy, and retry the copy until it matches the original (user set limit on number of retries). It can also check for and replace spaces in folder and filenames during the copying. There are a few flags to control program operation at the top of the script after the import statements. 

The script requires a basic Python 3.x installation. The script is probably Windows specific (Thermo instruments only have PCs for control computers). We use the script to copy files from the acquisition PC to removable media (flash and pocket drives), and to transfer those files to computers for analysis.

Python 3 (www.python.org) needs to be installed on the acquisition PC. I recommend the basic distribution from python.org since we do not typically run any analysis on our acquisiton PCs. The script needs to be copied onto the acquistion PC. It is probably a good idea to put the script in a folder on the C: drive (something like "python_scripts"). A shortcut to the script can be created on the desktop (so it is easy to find). There are multiple ways to run the script: try double-clicking on the shortcut icon, or right-click on the shortcut and "edit with IDLE". That opens the standard python IDE with a console window and a souce code window. The script can be run from the menu or with the F5 key. Python.org has nice help and tutorials, if you are new to python. The script creates a text log file in the folder where the script is located. 

Phil Wilmarth
Dec. 12, 2017
