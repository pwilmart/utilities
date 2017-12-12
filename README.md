# utilities
Some Python utility scripts for proteomics file management

Collection of tools for some basic proteomics file management activities. 

## copy_raw_files.py
Instrument RAW files can be large and can sometimes have errors when being copied. This script will copy files, check the original and the copy, and retry the copy until is matches the original (user set limit on number of retries). It can also check for and replace spaces in folder and filenames during the copying. There are a few flags to control program operation at the top of the script after the import statements. 

The script requires a basic Python 3.x installation. The script is probably Windows specific (Thermo instruments only have PCs for control computers). We use the script to copy files from the acquisition PC to removable media (flash and pocket drives), and to transfer those files to computers for analysis. 

Phil Wilmarth
Dec. 12, 2017
