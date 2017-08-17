#!/usr/bin/env python

import os
import time
import argparse
import subprocess
import logging as log
from bioblend import galaxy
from subprocess import CalledProcessError


def main( args, data_dir_root = '/project_data' ):
    """
    Load files into a Galaxy data library.
    """

    log.info("Importing data libraries.")

    url = "http://localhost"
    # The environment variables are set by the parent container
    admin_email = os.environ.get('GALAXY_DEFAULT_ADMIN_USER', 'admin@galaxy.org')
    admin_pass = os.environ.get('GALAXY_DEFAULT_ADMIN_PASSWORD', 'admin')

    # Establish connection to galaxy instance
    gi = galaxy.GalaxyInstance(url=url, email=admin_email, password=admin_pass)

    log.info("Looking for project data in %s" % data_dir_root)
    folders = dict()
    for root, dirs, files in os.walk( data_dir_root ):
        file_list = '\n'.join( [ os.path.join(root, filename) for filename in files] )
        folders[ root ] = file_list

    if folders:
        # Delete pre-existing lib (probably created byb a previous call)
        existing = gi.libraries.get_libraries(name='Project Data')
        for lib in existing:
            if lib['deleted'] == False:
                log.info('Pre-existing "Project Data" library %s found, removing it.' % lib['id'])
                gi.libraries.delete_library(lib['id'])

        log.info("Creating new 'Project Data' library.")
        prj_lib = gi.libraries.create_library('Project Data', 'Data for current genome annotation project')
        prj_lib_id = prj_lib['id']

        for fname, files in folders.items():
            if fname and files:
                log.info("Creating folder: %s" % fname)
                folder = gi.libraries.create_folder( prj_lib_id, fname )
                gi.libraries.upload_from_galaxy_filesystem(
                    prj_lib_id,
                    files,
                    folder_id = folder[0]['id'],
                    link_data_only = 'link_to_files'
                )
                time.sleep(1)

        # Wait for uploads to complete
        while True:
            try:
                ret = subprocess.check_output(["qstat"])
                if not len( ret.split('\n') ):
                    break
                time.sleep(3)
            except CalledProcessError as inst:
                if inst.returncode == 153: #queue is empty
                    break
                else:
                    raise

        time.sleep(10)
        log.info("Finished importing data.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Populate the Galaxy data library with files.'
    )
    parser.add_argument("-v", "--verbose", help="Increase output verbosity.",
                    action="store_true")

    args = parser.parse_args()
    if args.verbose:
        log.basicConfig(level=log.DEBUG)

    main( args )
