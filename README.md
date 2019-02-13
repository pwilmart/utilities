# utilities
Some Python utility scripts for proteomics file management

Collection of tools for some basic proteomics file management activities.

---

## compare_directories.py
Recursively compares two folders or drives. File contents can be compared for identity or just file names and attributes (faster). Provides information about higher-level differences. A text log file is created in the location with the script. Additional log information is appended to the log file each time the script runs.

---

## copy_raw_files.py
Instrument RAW files can be large and can sometimes have errors when being copied. This script will copy files, check the original and the copy, and retry the copy until it matches the original (user set limit on number of retries). It can also check for and replace spaces in folder and filenames during the copying. There are a few flags to control program operation at the top of the script after the import statements.

Work flow is:

- first step
  - select **individual RAW files** from source PC
  - select a **folder** on transport USB drive
- second step
  - select **individual RAW files** from transport USB drive
  - select a **folder** on the destination PC

Selecting individual RAW files (rather than a folder) lets un-needed RAW files (standards and blanks) be skipped if desired. The script gets the name of the folder where the RAW files were located and will create a folder with that name on the USB transport drive inside of the selected folder. A flag (on by default) controls if another `raw_files` subfolder is created.

Our acquisition PC has subfolders that match project codes. Our codes are a few characters of the PI name and an incrementing integer number (example: `PAW-1234`). When we move files to the analysis computers, we also use main subfolders that are named with the project codes. The [PAW pipeline](https://github.com/pwilmart/PAW_pipeline.git) we use adds another level of subfolder names to keep track of the pipeline steps (`raw_files`, `msn_files`, `filtered_files`, and `results_files`). The script tries to help with naming and folder organization. Your naming and organization needs may be different. Feel free to modify the script to suit your needs. The code is structured and has lots of comments.

The script requires a basic Python 3.x installation. The script is probably Windows specific (Thermo instruments only have PCs for control computers). We use the script to copy files from the acquisition PC to removable media (flash and pocket drives), and to transfer those files to computers for analysis.

Python 3 (www.python.org) needs to be installed on the acquisition PC. I recommend the basic distribution from python.org since we do not typically run any analysis on our acquisiton PCs. The script needs to be copied onto the acquistion PC. It is probably a good idea to put the script in a folder on the C: drive (something like "python_scripts"). A shortcut to the script can be created on the desktop (so it is easy to find). There are multiple ways to run the script: try double-clicking on the shortcut icon, or right-click on the shortcut and "edit with IDLE". That opens the standard python IDE with a console window and a souce code window. The script can be run from the menu or with the F5 key. Python.org has nice help and tutorials, if you are new to python. The script creates a text log file in the folder where the script is located.

---

Phil Wilmarth
Dec. 12, 2017
