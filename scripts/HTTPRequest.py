# SYSTEM IMPORTS
import os
import requests

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
        self.baseUrl = baseUrl

    def download(self, receivingFilePath, urlParams=[], fileChunkSize=1, readBytes=True):
        url = None
        if len(urlParams) == 0:
            url = self.baseUrl
        else:
            url = urljoin(self.baseUrl, *urlParams)
        response = requests.get(url, stream=True)

        if response.status_code != 200:
            Utilities.failExecution("Error %s downloading %s" % (response.status_code, url))
        with open(receivingFilePath, ("wb" if readBytes else "w")) as f:
            for chunk in response.iter_content(fileChunkSize):
                f.write(chunk)

    def upload(self, filePath, fileName="", urlParams=[]):
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

        # to post, do I have to add "/post" to the end of the url?
        response = requests.post(url, files={"upload_file": open(fullFilePath, 'rb')})

        # handle response
        if response.status_code != 200:
            Utilities.failExecution("Error %s uploading %s to %s" % (response.status_code,
                                                                     fullFilePath, url))

    def delete(self, urlParams=[]):
        fullUrlPath = self.baseUrl if len(urlParams) == 0 else urljoin(self.baseUrl, *urlParams)

        response = requests.delete(fullUrlPath)
        if response.status_code != 200:
            Utilities.failExecution("Error %s deleting file at url %s" % (response.status_code,
                                                                          fullUrlPath))

    def deleteAll(self, urlParams=[]):
        fullUrlPath = self.baseUrl if len(urlParams) == 0 else urljoin(self.baseUrl, *urlParams)

        for fileToDelete in self.listUrlContents(fullUrlPath).split("\n"):
            self.delete(urlParams + [fileToDelete])

    def listUrlContents(self, urlParams=[]):
        fullUrlPath = self.baseUrl if len(urlParams) == 0 else urljoin(self.baseUrl, *urlParams)

        response = requests.request("LIST", fullUrlPath)
        if response.status_code != 200:
            Utilities.failExecution("Error %s listing contents of %s" % (response.status_code,
                                                                         fullUrlPath))
