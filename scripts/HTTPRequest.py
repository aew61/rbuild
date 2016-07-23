# SYSTEM IMPORTS
import os
import requests

# PYTHON PROJECT IMPORTS



def urljoin(url, *urls):
    return '/'.join(url, *urls)

class HTTPRequest(object):
    def __init__(self, url):
        self.url = url

    def post(self, filePath, fileName=""):
        if fileName == "":
            fullFilePath = filePath

            # parse out fileName from filePath
            fileName = filePath.split(os.sep)[-1]
        else:
            fullFilePath = os.path.join(filePath, fileName)

        response = requests.post(urljoin(self.url, 'post'), {fileName: open(fullFilePath, 'rb')})

        # handle response
