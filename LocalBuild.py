# SYSTEM IMPORTS
import os
# import platform
# import shutil
import sys
import tarfile


currentDir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(currentDir, "scripts"))  # now we can import modules from <currentDirectory>/scripts
# PYTHON PROJECT IMPORTS
import Utilities


if __name__ == "__main__":
    # run flake8 on scripts/ directory
    Utilities.PFork(appToExecute="flake8",
                    argsForApp=["scripts/",
                                "--config=%s" % (os.path.join(currentDir, "config", "flake8.cfg"))],
                    failOnError=True)

    buildString = "%s.%s.%s.%s" % (os.environ["MAJOR_VER"] if os.environ.get("MAJOR_VER") is not None else 0,
                                   os.environ["MINOR_VER"] if os.environ.get("MINOR_VER") is not None else 0,
                                   os.environ["PATCH"] if os.environ.get("PATCH") is not None else 0,
                                   os.environ["BUILD_NUMBER"] if os.environ.get("BUILD_NUMBER") is not None else 0)
    tarFileName = "BuildScripts_%s_src.tar" % buildString
    # bundle all directories and files into a tar.gz file and upload to share
    with tarfile.open(tarFileName, "w:gz") as tarFile:
        print("currentDir: %s" % currentDir)
        for item in os.listdir(currentDir):
            print("\titem in %s" % item)
            if item != "LocalBuild.py" and "readme" not in item.lower() and not item.startswith("."):
                tarFile.add(item)

    with tarfile.open(tarFileName, "r:gz") as tarFile:
        for file in tarFile:
            print("entry in tarFile: %s" % file)

    # upload tarFile to shared directory
    if buildString != "0.0.0.0":
        # upload
        Utilities.copyTree(tarFileName, os.path.join(os.environ["SHARE_PATH"], "BuildScripts_dev"))
