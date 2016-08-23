# SYSTEM IMPORTS
import os
import requests
import sys

# PYTHON PROJECT IMPORTS
import Utilities


def urljoin(url, *urls):
    urlList = [url]
    urlList.extend([urlPart for urlPart in urls])
    unrefinedUrl = '/'.join(urlList).strip()
    unrefinedUrl = unrefinedUrl.replace("//", "/")
    return unrefinedUrl.replace("http:/", "http://")


class HTTPRequest(object):
    def __init__(self, baseUrl):
        self.user = os.environ.get("DBFILESERVER_USERNAME")
        self.pswrd = os.environ.get("DBFILESERVER_PASSWORD")
        self.baseUrl = baseUrl

    def parseValue(self, stringValue):
        if "u'" in stringValue:
            return stringValue[2:-1]
        elif "." in stringValue:
            return float(stringValue)
        else:
            return int(stringValue)

    def parseDict(self, dictData, keysToKeep, keysToIgnore):
        returnDict = {}
        dictPairs = dictData.strip().split(",")
        for pair in dictPairs:
            key, value = pair.strip().split(":")
            key = key[2:-1]  # all keys are strings so they have u'<key>'. Get rid of the u''
            if (key in keysToKeep and len(keysToKeep) > 0) or\
               (key not in keysToIgnore and len(keysToIgnore) > 0) or\
               (key == "relativeUrl" or key == "fileName" or key == "filetype") and key != "_id":
                returnDict[key] = self.parseValue(value.strip())

        return returnDict

    def parseQueryData(self, marshalledQueryData, keysToKeep, keysToIgnore):
        parsedQueryData = []
        marshalledQueryData = marshalledQueryData.replace("[", "").replace("]", "")
        splitDictData = marshalledQueryData.split("},")
        splitDictData[-1] = splitDictData[-1][:-1]
        for dictData in splitDictData:
            parsedQueryData.append(self.parseDict(dictData.strip()[1:], keysToKeep, keysToIgnore))

        return parsedQueryData

    def query(self, dbName, collectionName, dbParams={}, keysToKeep=[], keysToIgnore=[], hook=None):
        auth = requests.auth.HTTPBasicAuth(self.user, self.pswrd)

        finalDBParams = {("dbkey_%s" % key): dbParams[key] for key in dbParams.keys()}
        finalDBParams["dbName"] = dbName
        finalDBParams["collectionName"] = collectionName
        queryResponse = requests.request("QUERY", self.baseUrl, data=finalDBParams, auth=auth)

        if queryResponse.status_code != 200:
            Utilities.failExecution("Error querying database %s" % (queryResponse.status_code,
                                                                    queryResponse.content))

        requestData = self.parseQueryData(queryResponse.content, keysToKeep, keysToIgnore)
        if hook is not None:
            requestData = hook(requestData)
        return requestData

    def download(self, receivingDirPath, dbName, collectionName, urlParams=[],
                 dbParams={}, keysToKeep=[], keysToIgnore=[], fileChunkSize=1, readBytes=True, hook=None):
        url = None
        if len(urlParams) == 0:
            url = self.baseUrl
        else:
            url = urljoin(self.baseUrl, *urlParams)
        auth = requests.auth.HTTPBasicAuth(self.user, self.pswrd)

        requestData = self.query(dbName, collectionName, dbParams=dbParams,
                                 keysToKeep=keysToKeep, keysToIgnore=keysToIgnore, hook=hook)

        for fileToDownload in requestData:
            url = fileToDownload["relativeUrl"]
            if "http" not in url:
                url = urljoin(self.baseUrl, url)
            response = requests.get(url, stream=True, auth=auth)

            if response.status_code != 200:
                Utilities.failExecution("Error %s downloading %s" % (response.status_code, url))

            numBytes = len(response.content)
            currentBytes = 0.0
            minPercentToPrint = 0
            print("Starting download (%s bytes):" % numBytes)
            with open(os.path.join(receivingDirPath, fileToDownload["fileName"] +
                                   fileToDownload["filetype"]), ("wb" if readBytes else "w")) as f:
                for chunk in response.iter_content(fileChunkSize):
                    if currentBytes/numBytes >= minPercentToPrint:
                        print("[%s%%]" % int(currentBytes/numBytes * 100)),
                        minPercentToPrint += 0.1
                    f.write(chunk)
                    currentBytes += len(chunk)
            print("Download done")
        return requestData

    def upload(self, filePath, dbName, collectionName, fileName="", dbParams={}, urlParams=[]):
        fullFilePath = None
        url = None
        if fileName == "":
            fullFilePath = filePath

            # parse out fileName from filePath
            fileName = filePath.split(os.sep)[-1]
        else:
            fullFilePath = os.path.join(filePath, fileName)

        if len(urlParams) == 0:
            url = self.baseUrl
        else:
            url = urljoin(self.baseUrl, *urlParams)

        finalDBParams = {"dbkey_%s" % key: dbParams[key] for key in dbParams.keys()}
        finalDBParams["dbName"] = dbName
        finalDBParams["collectionName"] = collectionName
        # to post, do I have to add "/post" to the end of the url?
        response = requests.request("QUERY_POST", url, files={"upload_file": open(fullFilePath, 'rb')},
                                    data=finalDBParams, auth=requests.auth.HTTPBasicAuth(self.user, self.pswrd))

        # handle response
        if response.status_code != 200:
            Utilities.failExecution("Error %s uploading %s to %s" % (response.status_code,
                                                                     fullFilePath, url))

    def delete(self, urlParams=[]):
        fullUrlPath = self.baseUrl if len(urlParams) == 0 else urljoin(self.baseUrl, *urlParams)

        response = requests.delete(fullUrlPath, auth=requests.auth.HTTPBasicAuth(self.user, self.pswrd))
        if response.status_code != 200:
            Utilities.failExecution("Error %s deleting file at url %s" % (response.status_code,
                                                                          fullUrlPath))

    def deleteAll(self, urlParams=[]):
        fullUrlPath = self.baseUrl if len(urlParams) == 0 else urljoin(self.baseUrl, *urlParams)

        for fileToDelete in self.listUrlContents(fullUrlPath).split("\n"):
            self.delete(urlParams + [fileToDelete])

    def listUrlContents(self, urlParams=[]):
        fullUrlPath = self.baseUrl if len(urlParams) == 0 else urljoin(self.baseUrl, *urlParams)

        response = requests.request("LIST", fullUrlPath, auth=requests.auth.HTTPBasicAuth(self.user, self.pswrd))
        if response.status_code != 200:
            Utilities.failExecution("Error %s listing contents of %s" % (response.status_code,
                                                                         fullUrlPath))
        if sys.version_info[0] < 3:
            return str(response.content)
        else:
            return response.content.decode("utf-8")

    def customRequest(self, requestName, uploadFiles={}, requestData={}, urlParams=[]):
        fullUrlPath = self.baseUrl if len(urlParams) == 0 else urljoin(self.baseUrl, *urlParams)

        response = requests.request(requestName, fullUrlPath, files=uploadFiles, data=requestData,
                                    auth=requests.auth.HTTPBasicAuth(self.user, self.pswrd))
        if response.status_code != 200:
            Utilities.failExecution("Error %s executing [%s]: %s" % (response.status_code,
                                                                     requestName, fullUrlPath))

        if sys.version_info[0] < 3:
            return str(response.content)
        else:
            return response.content.decode("utf-8")
