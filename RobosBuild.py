# SYSTEM IMPORTS
import os
# import platform
import pymongo
import requests
import shutil
import subprocess
import sys
import tarfile
import traceback


currentDir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(currentDir, "scripts"))  # now we can import modules from <currentDirectory>/scripts
# PYTHON PROJECT IMPORTS


def urljoin(url, *urls):
    urlList = [url]
    urlList.extend([urlPart for urlPart in urls])
    unrefinedUrl = '/'.join(urlList).strip()
    unrefinedUrl = unrefinedUrl.replace("//", "/")
    return unrefinedUrl.replace("http:/", "http://")


def failExecution(errorMsg):
    print("Failed Build Stack:")
    traceback.print_stack(file=sys.stdout)

    print("********************\n*   BUILD FAILED   * %s\n********************\n" % errorMsg)
    sys.exit(1)


def PFork(appToExecute=None, argsForApp=[], wd=None, failOnError=False, environment={}):

    # a list that will contain all arguments with the application to
    # execute as the first element. This is to invoke Popen with,
    # which takes as an argument the commands that will be executed.
    app_and_args = list(argsForApp)
    if appToExecute is not None:
        app_and_args.insert(0, appToExecute)

    # get the current environment and update it with custom environment
    # variables injected into this method.
    real_environment = dict(os.environ)
    real_environment.update(environment)

    # execute the code. This method does not use the shell for safety
    # reasons. It will store the result in a pipe and default write all
    # errors to the console (later we can ignore the pipe and safe time
    # on the builds). Tidbit: "Popen" stands for "process open" also known as "fork."
    # note that this DOES NOT create a new console process (no new window will pop up)
    # when this executes.
    print("Executing %s" % ' '.join(app_and_args))
    childProcess = subprocess.Popen(app_and_args, cwd=wd, shell=False, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, env=real_environment, bufsize=1)

    # (for now) write the messages of the process execution to the console.
    for line in iter(childProcess.stdout.readline, b''):
        print line.rstrip() + '\n',

    # wait for childProcess and let all childProcess values settle
    # (like the returncode variable)
    childProcess.communicate()

    print("RETURN CODE FOR APP %s IS: %s" % (appToExecute, childProcess.returncode))

    if childProcess.returncode != 0 and failOnError:
        failExecution("PFork failed to execute [%s]" % ' '.join(app_and_args))
    return childProcess.returncode


def copyTree(srcPath, destPath):
    if os.path.isdir(srcPath):
        if os.path.isdir(destPath):
            failExecution("cannot copy directory [%s]: %s exists!" %
                          (srcPath, destPath))
        elif os.path.isfile(destPath):
            failExecution("Cannot copy directory [%s]: %s is a File!" %
                          (srcPath, destPath))
        shutil.copytree(srcPath, destPath)
    else:
        shutil.copy2(srcPath, destPath)  # copy2() copies file metaData


if __name__ == "__main__":
    # run flake8 on scripts/ directory
    PFork(appToExecute="flake8",
          argsForApp=[".", "scripts/",
                      "--config=%s" % (os.path.join(currentDir, "config", "flake8.cfg"))],
          failOnError=True)

    buildString = "%s.%s.%s.%s" % (os.environ["MAJOR_VER"] if os.environ.get("MAJOR_VER") is not None else 0,
                                   os.environ["MINOR_VER"] if os.environ.get("MINOR_VER") is not None else 0,
                                   os.environ["PATCH"] if os.environ.get("PATCH") is not None else 0,
                                   os.environ["BUILD_NUMBER"] if os.environ.get("BUILD_NUMBER") is not None else 0)
    tarFileName = "BuildScripts_%s_src" % buildString
    # bundle all directories and files into a tar.gz file and upload to share
    with tarfile.open(tarFileName + ".tar.gz", "w:gz") as tarFile:
        for item in os.listdir(currentDir):
            if item != "RobosBuild.py" and "readme" not in item.lower() and not item.startswith("."):
                tarFile.add(item)

    # upload tarFile to shared directory
    if buildString != "0.0.0.0":
        productNumbers = [int(x) for x in buildString.split(".")]
        # upload to database
        client = pymongo.MongoClient(os.environ["MONGODB_URI"])
        db = client["BuildScripts"]
        collection = db["src"]
        collection.insert_one(
            {
                "fileName": tarFileName,
                "filetype": ".tar.gz",
                "major_version": productNumbers[0],
                "minor_version": productNumbers[1],
                "patch": productNumbers[2],
                "build_num": productNumbers[3],
                "config": "src",
            })

        # try to post file to file server
        response = requests.post(urljoin(os.environ["FILESERVER_URI"], "BuildScripts/"),
                                 files={"upload_file": open(tarFileName + ".tar.gz", "rb")},
                                 auth=requests.auth.HTTPBasicAuth(os.environ["DBFILESERVER_USERNAME"],
                                                                  os.environ["DBFILESERVER_PASSWORD"]))
        if response.status_code != 200:
            failExecution("Error %s uploading %s to %s" % (response.status_code,
                                                           tarFileName,
                                                           os.environ["FILESERVER_URI"] + "BuildScripts/"))
