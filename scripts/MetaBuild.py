
# SYSTEM IMPORTS
import os
import platform
import tarfile
import xml.etree.ElementTree as ET

# PYTHON PROJECT IMPORTS
import Utilities
import FileSystem
# import DBManager
import Graph
# import HTTPRequest


# the parent class of the build process. It contains methods common to all build processes as well
# as the ability to run methods in user specified order with user given arguments.
class MetaBuild(object):
    def __init__(self):
        self._project_name = ""
        self._project_namespace = ""
        self._source_dirs = ["cpp"]
        self._build_steps = []
        self._project_build_number = "0.0.0.0"  # major.minor.patch.build
        self._configurations = ["debug", "release"]
        self._build_directory = FileSystem.getDirectory(FileSystem.WORKING)
        self._tests_to_run = []
        self._dbManager = None
        self._httpRequest = None
        self._cover = False
        self._buildGraph = Graph.Graph()
        self._globalDeps = {}

    def findProjectsInWorkspace(self):
        workspaceDir = FileSystem.getDirectory(FileSystem.WORKSPACE_DIR)
        fullSubDirPath = None
        packagesToBuild = {}
        for subdir in os.listdir(workspaceDir):
            fullSubDirPath = os.path.join(workspaceDir, subdir)
            if os.path.islink(fullSubDirPath):
                # handle symbolic link: follow it and continue searching
                continue
            else:
                if os.path.exists(os.path.join(fullSubDirPath, "CMakeLists.txt")) and\
                   os.path.exists(os.path.join(fullSubDirPath, "package.xml")):
                    # this directory has a project I assume you want to build
                    packagesToBuild[subdir] = fullSubDirPath
        return packagesToBuild

    def packageAvailable(self, packageName):
        self._dbManager.openCollection("available_packages")
        return len(self._dbManager.query(
            {
                "package_name": packageName,
                "config": self._config.lower(),
            },
            returnOne=True)) > 0

    def parsePackageFile(self, packageFilePath, packagesToBuild, depsToDownload):
        tree = ET.parse(packageFilePath)
        root = tree.getroot()
        packageDict = {}
        packageName = None
        packageDeps = []
        if root.tag != "package":
            Utilities.failExecution("package file error. Top level tag should be <package>")
        for childElement in root:
            # deal with the children. Might as well collect build information about every package here.
            if "name" == childElement.tag:
                packageName = childElement.text
            elif "robos_package_dependency" == childElement.tag:
                if childElement.text not in packagesToBuild and\
                   self.packageAvailable(childElement.text) and childElement not in depsToDownload:
                    # download this dep
                    depsToDownload[childElement.text] = None
                    if "externalDeps" not in packageDict:
                        packageDict["externalDeps"] = [childElement.text]
                    else:
                        packageDict["externalDeps"].append(childElement.text)
                elif childElement.text in packagesToBuild:
                    packageDeps.append(childElement.text)
                else:
                    Utilities.failExecution("Not sure what to do with package dependency: %s." +
                                            "Cannot download it and it is not present on system")
            else:
                packageDict[childElement.tag] = childElement.text
        if packageName is None:
            Utilities.failExecution("package.xml found in %s is missing a name tag" % packageFilePath)
        print("Required packages for project [%s] are %s" % (self._project_name, packageDeps))
        return packageName, packageDeps, packageDict

    def createGraph(self, packagesToBuild):
        # need to open all packages.xmls and get the associated data
        for packageDirName, packagePath in packagesToBuild.items():
            packageName, packageDeps, packageInfo =\
                self.parsePackageFile(os.path.join(packagePath, "package.xml"), packagesToBuild, self._globalDeps)
            packageInfo["packageMainPath"] = packagePath
            self._buildGraph.AddNode(packageName, outgoingEdges=packageDeps, extraInfo=packageInfo)

    def loadGlobalPackageDependencies(self):
        globalDepsDir = FileSystem.getDirectory(FileSystem.GLOBAL_DEPENDENCIES, self._config)
        if os.path.exists(globalDepsDir):
            Utilities.rmTree(globalDepsDir)
        Utilities.mkdir(globalDepsDir)
        for package in self._globalDeps:
            print("Downloading package [%s]" % package)
            self._dbManager.openCollection(package)
            mostRecentRecord = [x for x in self._dbManager.query(
                {
                    "config": self._config.lower(),
                    "OS": platform.system().lower(),
                },
                sortScheme="build_num"
            )][-1]
            self._httpRequest.download(os.path.join(globalDepsDir, mostRecentRecord["fileName"] +
                                       mostRecentRecord["filetype"]),
                                       urlParams=[mostRecentRecord["relativeUrl"]])
            self._globalDeps[package] = os.path.join(globalDepsDir, mostRecentRecord["fileName"] +
                                                     mostRecentRecord["filetype"])

    # removes previous builds so that this build
    # is a fresh build (on this machine). This
    # guarentees that this build uses the most recent
    # source files.
    def cleanBuildWorkspace(self, node):
        print("Cleaning build directory for project [%s]" % node._name)
        buildDirectory = FileSystem.getDirectory(FileSystem.WORKING, self._config, node._name)
        if os.path.exists(buildDirectory):
            Utilities.rmTree(buildDirectory)

    def findDependencyVersions(self, requiredProjects):
        projectRecords = []
        buildDepPath = FileSystem.getDirectory(FileSystem.BUILD_DEPENDENCIES, self._config, self._project_name)
        for project in requiredProjects:
            self._dbManager.openCollection(project[0])
            # find correct configuration and version
            mostRecentVersion = [x for x in self._dbManager.query(
                {
                    "config": self._config.lower(),
                    "OS": platform.system().lower()
                },
                sortScheme="build_num"
            )][-1]
            if not os.path.exists(os.path.join(buildDepPath, mostRecentVersion["fileName"])):
                projectRecords.append([project[0], mostRecentVersion])
        return projectRecords

    def loadDependencies(self, node):
        buildDepPath = FileSystem.getDirectory(FileSystem.BUILD_DEPENDENCIES, self._config, node._name)
        globalDepsDir = FileSystem.getDirectory(FileSystem.GLOBAL_DEPENDENCIES, self._config)
        if not os.path.exists(buildDepPath):
            Utilities.mkdir(buildDepPath)
        binDir = os.path.join(FileSystem.getDirectory(FileSystem.INSTALL_ROOT,
                                                      self._config, node._name), "bin")
        libDir = os.path.join(FileSystem.getDirectory(FileSystem.INSTALL_ROOT,
                                                      self._config, node._name), "lib")
        outIncludeDir = os.path.join(FileSystem.getDirectory(FileSystem.INSTALL_ROOT,
                                                             self._config, node._name), "include")
        if not os.path.exists(binDir):
            Utilities.mkdir(binDir)
        if not os.path.exists(libDir):
            Utilities.mkdir(libDir)
        if not os.path.exists(outIncludeDir):
            Utilities.mkdir(outIncludeDir)

        # copy packages that have already been built locally
        for package in node._outgoingEdges:
            # this name is wacky. It refers to the directory where a package that this package is dependent
            # on stored its .tar.gz file (also called a "package")
            depPackagePackageDir = FileSystem.getDirectory(FileSystem.PACKAGE, self._config, package)
            packagePackageName = package + "_" + self._project_build_number + "_" +\
                self._config.lower() + "_" + platform.system.lower()

            # standardize the process...copy the .tar.gz file, extract, and copy results
            Utilities.copyTree(os.path.join(depPackagePackageDir,
                                            packagePackageName + ".tar.gz"), buildDepPath)
            with tarfile.open(os.path.join(depPackagePackageDir,
                                           packagePackageName + ".tar.gz"), "r:gz") as tarFile:
                tarFile.extractall(buildDepPath)

            # copy to appropriate directories
            Utilities.copyTree(os.path.join(buildDepPath, packagePackageName, "include", package),
                               os.path.join(outIncludeDir, package))

            if platform.system() == "Windows":
                Utilities.copyTree(os.path.join(buildDepPath, packagePackageName, "bin"), binDir)
            Utilities.copyTree(os.path.join(buildDepPath, packagePackageName, "lib"), libDir)
            Utilities.copyTree(os.path.join(buildDepPath, packagePackageName, "cmake"),
                               os.path.join(FileSystem.getDirectory(FileSystem.WORKING), "cmake"))

        # copy packages that were downloaded
        for package in node._extraInfo["externalDeps"]:
            packageName = self._globalDeps[package].replace(globalDepsDir, "").replace(".tar.gz", "")
            with tarfile.open(self._globalDeps[package], "r:gz") as tarFile:
                tarFile.extractall(globalDepsDir)
            # copy directories
            # copy to appropriate directories
            Utilities.copyTree(os.path.join(globalDepsDir, packageName, "include", package),
                               os.path.join(outIncludeDir, package))

            if platform.system() == "Windows":
                Utilities.copyTree(os.path.join(globalDepsDir, packageName, "bin"), binDir)
            Utilities.copyTree(os.path.join(globalDepsDir, packageName, "lib"), libDir)
            Utilities.copyTree(os.path.join(globalDepsDir, packageName, "cmake"),
                               os.path.join(FileSystem.getDirectory(FileSystem.WORKING), "cmake"))

    def defaultSetupWorkspace(self, node):
        print("Setting up workspaces for project [%s]" % node._name)
        self.cleanBuildWorkspace(node)
        Utilities.mkdir(FileSystem.getDirectory(FileSystem.WORKING, self._config, node._name))

    def generateProjectVersion(self, node):
        outIncludeDir = os.path.join(
            FileSystem.getDirectory(FileSystem.OUT_ROOT),
            'include'
        )
        print("making directory %s" % outIncludeDir)
        Utilities.mkdir(outIncludeDir)
        with open(os.path.join(outIncludeDir, 'Version.hpp'), 'w') as file:
            file.write("#pragma once\n"
                       "#ifndef VERSION_H\n"
                       "#define VERSION_H\n\n"
                       "#define VERSION       " + self._project_build_number + "\n"
                       "#define VERSION_STR  \"" + self._project_build_number + "\"\n\n"
                       "#endif  // end of VERSION_H\n\n")

    def checkConfigArgsAndFormat(self, offset, configArgs):
        formattedHeader = ""
        formattedSrc = ""
        for arg in configArgs:
            if arg[2] == "dir":
                if os.path.exists(arg[3]):
                    if os.path.isdir(arg[3]):
                        Utilities.rmTree(arg[3])
                    else:
                        Utilities.failExecution("Path [%s] was assumed to be a directory" % arg[3])
                Utilities.mkdir(arg[3])
            elif arg[2] == "file":
                if not os.path.exists(arg[3]) or not os.path.isfile(arg[3]):
                    Utilities.failExecution("Path [%s] does not exist or is not a file" % arg[3])
            elif arg[2] is not None:
                Utilities.failExecution("unknown config variable value specifier [%s]" % arg[2])

            formattedHeader += offset + "extern const " + arg[0] + " " + arg[1] + ";\n\n"
            formattedSrc += offset + "const " + arg[0] + " " + \
                arg[1] + " = " + ("\"" + str(arg[3]) + "\"" if "string" in arg[0] else str(arg[3])) + \
                ";\n\n"

        return formattedHeader, formattedSrc

    def defaultPreBuild(self, node):
        self.defaultSetupWorkspace(node) if not hasattr(self, "customSetupWorkspace")\
            else self.customSetupWorkspace(node)
        self.generateProjectVersion(node)

    def getCMakeArgs(self, node, pathPrefix, workingDirectory, test, logging, python):
        CMakeProjectDir = node._extraInfo["packageMainPath"]
        relCMakeProjectDir = os.path.relpath(CMakeProjectDir,
                                             workingDirectory)

        outRoot = FileSystem.getDirectory(FileSystem.OUT_ROOT, self._config, node._name)

        # projectWorkingDir = getDirectory(FileSystemDirectory.ROOT, self._config, self._project_name)
        installRootDir = FileSystem.getDirectory(FileSystem.INSTALL_ROOT, self._config,  node._name)

        # all of these are relative paths that are used by CMake
        # to place the appropriate build components in the correct
        # directories.
        binDir = os.path.relpath(
            os.path.join(FileSystem.getDirectory(FileSystem.INSTALL_ROOT, self._config, node._name), "bin"),
            outRoot
        )

        libDir = os.path.relpath(
            os.path.join(FileSystem.getDirectory(FileSystem.INSTALL_ROOT, self._config, node._name), "lib"),
            outRoot
        )
        outIncludeDir = os.path.join(FileSystem.getDirectory(FileSystem.OUT_ROOT, self._config, node._name),
                                     "include")

        toolchainDir = os.path.relpath(os.path.join(FileSystem.getDirectory(FileSystem.WORKING),
                                                    "cmake", "toolchains"),
                                       workingDirectory)
        allBuiltOutDir = FileSystem.getDirectory(FileSystem.OUT_ROOT, self._config)
        if platform.system() == "Windows":
            installRootDir = "\"%s\"" % installRootDir.replace("\\", "/")
            outIncludeDir = "\"%s\"" % outIncludeDir.replace("\\", "/")
            # toolchain = "\"%s\"" % toolchainDir.replace("\\", "/")

        if self._config == "release":
            cmake_config = "Release"
        else:
            cmake_config = "Debug"

        fullToolchainPath = None
        if platform.system() == "Windows":
            fullToolchainPath = os.path.join(toolchainDir, "toolchain_windows_%s.cmake" % Utilities.getMachineBits())
            # "x86")
        else:
            fullToolchainPath = os.path.join(toolchainDir, "toolchain_unix_%s.cmake" % Utilities.getMachineBits())

        monoPath = os.environ.get("MONO_BASE_PATH").replace("\\", "/") \
            if os.environ.get("MONO_BASE_PATH") is not None else ""
        pythonPath = os.environ.get("PYTHON_BASE_PATH").replace("\\", "/") \
            if os.environ.get("PYTHON_BASE_PATH") is not None else ""
        pythonVer = os.environ.get("PYTHON_VERSION") if os.environ.get("PYTHON_VERSION") is not None else 0

        # remember CMake paths need to be relative to the top level
        # directory that CMake is called (in this case projects/<project_name>)
        CMakeArgs = [
            relCMakeProjectDir,
            "-DCMAKE_RUNTIME_OUTPUT_DIRECTORY=%s%s" % (pathPrefix, binDir),
            "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=%s%s" % (pathPrefix, libDir),
            "-DCMAKE_ARCHIVE_OUTPUT_DIRECTORY=%s%s" % (pathPrefix, libDir),
            "-DCMAKE_PREFIX_PATH=%s" % (installRootDir),  # absolute path
            "-DCMAKE_BUILD_TYPE=%s" % cmake_config,
            "-DPROCESSOR=%s" % Utilities.getProcessorInfo()[1],
            "-DBITS=%s" % Utilities.getMachineBits(),
            "-DCMAKE_TOOLCHAIN_FILE=%s" % fullToolchainPath,  # toolchain file path (relative)
            "-DBUILD_%s=ON" % self._project_name.upper(),
            "-DCMAKE_INSTALL_PREFIX=%s" % allBuiltOutDir,  # install root dir
            "-DENABLE_COVER=%s" % ("ON" if self._cover else "OFF"),
            "-DRUN_UNIT_TESTS=%s" % test,
            "-DENABLE_LOGGING=%s" % logging,
            "-DMONO_PATH=\"%s\"" % monoPath,
            "-DPYTHON_PATH=\"%s\"" % pythonPath,
            "-DPYTHON_VERSION=%s" % pythonVer,
            "-DPYTHON_ENABLED=%s" % python,
        ]
        return CMakeArgs

    # this method will generate documentation
    # of the project. We are using Doxygen
    # to fulfill this.
    def document(self, node):
        print("generating documentation for project [%s]" % node._name)

    # this method will package the project into
    # a gzipped tarball (tar.gz) file.
    def package(self, node):
        print("packaging project [%s]" % node._name)
        packageDir = FileSystem.getDirectory(FileSystem.PACKAGE,
                                             configuration=self._config,
                                             projectName=node._name)
        packageFileName = node._name + "_" + self._project_build_number +\
            "_" + self._config.lower() + "_%s" % platform.system().lower()
        if os.path.exists(packageDir):
            Utilities.rmTree(packageDir)
        Utilities.mkdir(os.path.join(packageDir, packageFileName))
        outRoot = FileSystem.getDirectory(FileSystem.OUT_ROOT, self._config)
        for outDir in os.listdir(outRoot):
            Utilities.copyTree(os.path.join(outRoot, outDir), os.path.join(packageDir, packageFileName, outDir))
        Utilities.copyTree(FileSystem.getDirectory(FileSystem.CMAKE_BASE_DIR, projectName=node._name),
                           os.path.join(packageDir, packageFileName, "cmake"))
        Utilities.copyTree(os.path.join(node._extraInfo["packageMainPath"], "LICENSE"),
                           os.path.join(packageDir, packageFileName))
        Utilities.copyTree(os.path.join(node._extraInfo["packageMainPath"], "README.md"),
                           os.path.join(packageDir, packageFileName))
        Utilities.copyTree(os.path.join(node._extraInfo["packageMainPath"], "package.xml"),
                           os.path.join(packageDir, packageFileName))

        with tarfile.open(os.path.join(packageDir, packageFileName + ".tar.gz"),
                          "w:gz") as tarFile:
            tarFile.add(os.path.join(packageDir, packageFileName), arcname=packageFileName)

    def runUnitTests(self, node, iterations=1, test="OFF", valgrind="OFF"):
        print("Running unit tests for project [%s]" % node._name)
        if test == "OFF":
            print("Unit tests disables for project [%s]" % node._name)
            return
        installRoot = FileSystem.getDirectory(FileSystem.INSTALL_ROOT, self._config,  node._name)
        args = []
        testReportDir = FileSystem.getDirectory(FileSystem.TEST_REPORT_DIR, self._config, node._name)
        if not os.path.exists(testReportDir):
            Utilities.mkdir(testReportDir)

        for iteration in range(1, int(iterations) + 1):
            print("Running unit tests [%s/%s]" % (iteration, iterations))
            for testToRun in self._tests_to_run:
                args = ["--gtest_output=xml:%s.JUnit.xml" % os.path.join(testReportDir, testToRun)]
                executablePath = os.path.join(installRoot, "bin", testToRun)
                if platform.system() == "Windows":
                    executablePath += ".exe"
                else:
                    if valgrind == "ON":
                        args = ['valgrind', '--leak-check=yes', executablePath]
                if os.path.exists(executablePath):
                    Utilities.PFork(appToExecute=executablePath,
                                    argsForApp=args if iteration == 1 else [], failOnError=True)
                else:
                    print("%s does NOT exist!" % executablePath)
            if iterations > 1:
                print("\n\n")

    def coverWindows(self, node, iterations=1, test="OFF"):
        # run opencppcoverage
        # but for now just run the unit tests
        self.runUnitTests(iterations, test)

    def coverLinux(self, node, iterations=1, test="OFF", valgrind="OFF"):
        self.runUnitTests(iterations, test, valgrind)
        # get cobertura reports from gcovr
        # reportDir = FileSystem.getDirectory(FileSystem.TEST_REPORT_DIR, self._config, self._project_name)
        # sourceRoot = FileSystem.getDirectory(FileSystem.CPP_SOURCE_DIR)
        # Utilities.PFork(appToExecute="gcovr",
        #                 argsForApp=["--branches", "--xml-pretty", "--root=%s" % sourceRoot,
        #                             "--output=%s" % os.path.join(reportDir, self._project_name + ".coverage.xml")],
        #                 failOnError=True)
        # Utilities.PFork(appToExecute="gcovr",
        #                 argsForApp=["--branches", "--root=%s" % sourceRoot, "--html", "--html-details",
        #                             "--output=%s" % os.path.join(reportDir,
        #                                                          self._project_name + ".coverage_html_report.html")],
        #                 failOnError=True)

    def coverWithUnit(self, node, iterations=1, test="OFF", valgrind="OFF"):
        testReportDir = FileSystem.getDirectory(FileSystem.TEST_REPORT_DIR, self._config, node._name)
        if not os.path.exists(testReportDir):
            Utilities.mkdir(testReportDir)
        if self._cover:
            if platform.system().lower() == "windows":
                self.coverWindows(node, iterations, test)
            else:
                self.coverLinux(node, iterations, test, valgrind)
        else:
            self.runUnitTests(node, iterations, test, valgrind)

    # executes a particular part of the build process and fails the build
    # if that build step fails.
    def executeStep(self, buildStep):
        print("-Executing build step [%s]" % buildStep.__name__)
        success = Utilities.call(buildStep, self._custom_args)
        if not success:
            Utilities.failExecution("Build step [%s] failed" % buildStep)

    # executes all build steps
    def executeBuildSteps(self, buildSteps):
        for buildStep in buildSteps:
            self.executeStep(buildStep)

    # entry point into the build process. At this point, user supplied
    # methods and arguments will have been entered and parsed. If no methods
    # are present, then the default build steps will be run.
    # (note that the default steps will be left to the child (LocalBuild) of
    #  GlobalBuild to define so that the default build steps can be unique
    #  for each project).
    def run(self, parsedCommandLine):
        (buildSteps, self._custom_args) = (parsedCommandLine[0], parsedCommandLine[1])
        # convert to function pointers
        buildSteps = [getattr(self, buildStep) for buildStep in buildSteps if hasattr(self, buildStep)]

        # this build MUST have a project name to run
        if self._project_name == "":
            Utilities.failExecution("Project name not set")

        # if the user has not specified any build steps, run the default
        if len(buildSteps) == 0:
            buildSteps = self._build_steps

        self.createGraph(self.findProjectsInWorkspace())
        buildOrder = self._buildGraph.TopologicalSort()
        maxPackageLenth = len("---------------------------------------")
        for packageToBuild in buildOrder:
            if len(packageToBuild._name) > maxPackageLenth:
                maxPackageLenth = len(packageToBuild._name)
        print("-" * (maxPackageLenth + 4))
        print("| Building Packages in Topological Order: |")
        print("-" * (maxPackageLenth + 4))
        for packageToBuild in buildOrder:
            print("| " + (" " * (maxPackageLenth - len(packageToBuild._name))) + packageToBuild._name + " |")
        print("-" * (maxPackageLenth + 4))

        # run the build for the user specified configuration else run for
        # all configurations (the user can restrict this to build for
        # debug or release versions)
        if "configuration" in self._custom_args:
            self._config = self._custom_args["configuration"]
            if self._config != "release" and self._config != "debug":
                Utilities.failExecution("Unknown configuration [%s]" % self._config)
            print("\nbuilding configuration [%s]\n" % self._config)
            self.loadGlobalPackageDependencies()
            for packageToBuild in buildOrder:
                self._custom_args["node"] = packageToBuild
                self.executeBuildSteps(buildSteps)
        else:
            for configuration in self._configurations:
                print("\nbuilding configuration [%s]\n" % configuration)
                self._config = configuration
                self.loadGlobalPackageDependencies()
                for packageToBuild in buildOrder:
                    self._custom_args["node"] = packageToBuild
                    self.executeBuildSteps(buildSteps)

        print("-----------------------")
        print("|   BUILD SUCCESSFUL  |")
        print("-----------------------")

    def help(self):
        print("global commands:")
        print("     global build steps:")
        print("         defaultSetupWorkspace       removed previous project build files and directories.")
        print("         document                    generates documentation for all project source files.")
        print("         package                     packages up project binaries and public headers for")
        print("                                     distribution.")
        print("         runUnitTests                runs the project unit tests.")
        print("     global custom variables:")
        print("         -configuration <project>    the configuration of the build (debug or release).")
        print("         -projects  <projects...>    the projects that will be built and the order in which")
        print("                                     they are built.")
        print("         -iterations <num>           the number of times that unit tests will be run as part")
        print("                                     or the build process.")
        print("         -logging <ON|OFF>           enables or disables logging capabilites (default = OFF).")
        print("         -test <ON|OFF>              enables or disables running unit tests as part of build")
        print("                                     process.")
        print("         -python <ON|OFF>            enables or disables Python embedding (default = OFF).")
        print("     UNIX custom variables:")
        print("         -valgrind <ON|OFF>          enables valgrind for executable testing support")
        print("                                     (default = OFF).")
        print("")
        print("")
