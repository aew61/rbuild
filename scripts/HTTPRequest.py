# SYSTEM IMPORTS
import os
import requests

# PYTHON PROJECT IMPORTS
import Utilities


def urljoin(url, *urls):
    unrefinedUrl = '/'.join(url, *urls).strip()
    return unrefinedUrl.replace("//", "/")


class HTTPRequest(object):
    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

    def download(self, receivingFilePath, urlParams=[], fileChunkSize=0, readBytes=True):
        url = None
        if len(urlParams) == 0:
            url = self.baseUrl
        else:
            url = urljoin(self.baseUrl, *urlParams)
        response = requests.get(url, stream=True)

        if response.status_code != 200:
            Utilities.failExecution("Error %s downloading %s" % (response.status_code, url))
        with open(receivingFilePath, ("wb" if readBytes else "w")) as f:
            for chunk in response.iter_content(fileChunkSize if fileChunkSize > 0 else None):
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
        response = requests.post(url, {"upload_file": open(fullFilePath, 'rb')})

        # handle response
        if response.status_code != 200:
            Utilities.failExecution("Error %s uploading %s to %s" % (response.status_code,
                                                                     fullFilePath, url))
