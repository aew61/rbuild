
# SYSTEM MODULES
import platform

# BUILT IN MODULES
import FileSystem
from MetaBuild import MetaBuild
import Utilities


class ProjectBuild(MetaBuild):
    def __init__(self, projectName):
        super(ProjectBuild, self).__init__()

        # we can override member variables defined in GlobalBuildRules
        self._project_name = projectName
        self._project_namespace = "CWRUBotix"
        self._project_build_number = "%s.%s.%s.%s" % (
            os.environ["MAJOR_VER"] if os.environ.get("MAJOR_VER") is not None else 0,
            os.environ["MINOR_VER"] if os.environ.get("MINOR_VER") is not None else 0,
            os.environ["PATCH"] if os.environ.get("PATCH") is not None else 0,
            os.environ["BUILD_NUMBER"] if os.environ.get("BUILD_NUMBER") is not None else 0
        self._installTarget = True

    # this method will launch CMake.
    # CMake is handling all of our compiling and linking.
    def cmake(self, test="OFF", logging="OFF", python="OFF"):
        # make directory that CMake will dump output to
        wd = FileSystem.getDirectory(FileSystem.WORKING, self._config, self._project_name)
        Utilities.mkdir(wd)

        CMakeArgs = self.getCMakeArgs("", wd, test, logging, python)
        if platform.system() == "Windows":
            CMakeArgs.extend(["-G", "\"NMake Makefiles\""])
            Utilities.PForkWithVisualStudio(appToExecute="cmake",
                                            argsForApp=CMakeArgs,
                                            wd=wd)
        else:
            CMakeArgs.extend(["-G", "Unix Makefiles"])
            Utilities.PFork(appToExecute="cmake", argsForApp=CMakeArgs, wd=wd, failOnError=True)

    def makeTarget(self, targets):
        # make directory that CMake will dump all output to
        wd = FileSystem.getDirectory(FileSystem.WORKING, self._config, self._project_name)

        if platform.system() == "Windows":
            Utilities.PForkWithVisualStudio(appToExecute="nmake",
                                            argsForApp=targets,
                                            wd=wd)
        else:
            Utilities.PFork(appToExecute="make", argsForApp=targets, wd=wd, failOnError=True)

    def makeVisualStudioProjects(self, test="OFF", logging="OFF"):
        wd = FileSystem.getDirectory(FileSystem.VISUAL_STUDIO_ROOT, self._config, self._project_name)
        Utilities.mkdir(wd)
        CMakeArgs = self.getCMakeArgs("", wd, test, logging)
        if platform.system() == "Windows":
            visualStudioVersion = Utilities.formatVisualStudioVersion(Utilities.getVisualStudioVersion())
            CMakeArgs.extend(["-G", "\"Visual Studio %s\"" % visualStudioVersion])
            Utilities.PForkWithVisualStudio(appToExecute="cmake",
                                            argsForApp=CMakeArgs,
                                            wd=wd)

    def make(self):
        self.makeTarget(["all"])
        if self._installTarget):
            self.makeTarget(["install"])

    def build(self):
        print("Building project [%s]" % self._project_name)
        self.executeBuildSteps([self.customPreBuild if hasattr(self, "customPreBuild") else self.defaultPreBuild,
                                self.cmake, self.make])

    def uploadPackagedVersion(self):
        print("Uploading project [%s]" % self._project_name)
        packageDir = FileSystem.getDirectory(FileSystem.PACKAGE,
                                             configuration=self._config,
                                             projectName=self._project_name)
        packageFileName = self._project_name + "_" + self._project_build_number +\
            "_" + self._config.lower()
        productNumbers = [int(x) for x in self._project_build_number.split(".")]

        self._dbManager.openCollection(self._project_name.lower())
        self._dbManager.insert(
            {
                "fileName": packageFileName,
                "filetype": ".tar.gz",
                "major_version": productNumbers[0],
                "minor_version": productNumbers[1],
                "patch": productNumbers[2],
                "build_num": productNumbers[3],
                "config": self._config.lower(),
            },
            insertOne=True)
        self._httpRequest.upload(packageDir,
                                 fileName=packageFileName + ".tar.gz",
                                 urlParams=[os.environ["JOB_NAME"], self.config.lower()])

    def help(self):
        print("command specific to project [%s]" % self._project_name
        print("     [%s] specific build steps" % self._project_name
        print("         cmake                       generates build files for all C++ source and tests.")
        print("         make                        makes all binaries.")
        print("         build                       runs cmake and make to build all binaries.")
        print("         makeVisualStudioProjects    generates visual studio projects.")
        print("         uploadPackagedVersion       uploads built and tested binaries for distribution.")
        print("     [%s] specific custom variables" % self._project_name)
        print("")

        # call help of parent class (MetaBuild)
        super(ProjectBuild, self).help()
