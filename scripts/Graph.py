# SYSTEM IMPORTS


# PYTHON PROJECT IMPORTS


class Node(object):
    def __init__(self, name, incomingEdges=[], outgoingEdges=[], extraInfo={}):
        self._name = name
        self._incomingEdges = incomingEdges
        self._outgoingEdges = outgoingEdges
        self._extraInfo = extraInfo
        self._discoveryTime = 0
        self._finishingTime = 0
        self._color = "WHITE"
        self._parent = None


class Graph(object):
    def __init__(self):
        self._nodeMap = {}
        self._topologicalOrder = []

    def AddNode(self, name, incomingEdges=[], outgoingEdges=[], extraInfo={}):
        self._nodeMap[name] = Node(name, extraInfo=extraInfo)

    def AddEdge(self, source, destination):
        self._nodeMap[source]._outgoingEdges.append(destination)
        self._nodeMap[destination]._incomingEdges.append(source)

    def GetNode(self, name):
        return self._nodeMap[name]

    def DepthFirstSearchVisit(self, node, time, onNodeFinish=None):
        time += 1

        # discover the node
        node._discoveryTime = time
        node._color = "GRAY"
        for childName in node._outgoingEdges:
            # visit all unvisited children
            if self._nodeMap[childName]._color == "WHITE":
                self._nodeMap[childName]._parent = node
                self.DepthFirstSearchVisit(self._nodeMap[childName], time, onNodeFinish)

        # finish the node
        node._color = "BLACK"
        time += 1
        node._finishingTime = time
        if onNodeFinish is not None:
            onNodeFinish(node)

    def DepthFirstSearch(self, onNodeFinish=None):
        time = 0
        for name, node in self._nodeMap.items():
            if node._color == "WHITE":
                self.DepthFirstSearchVisit(node, time, onNodeFinish)

    def TopologicalSort(self):
        def addToTopologicalOrder(node):
            if node._extraInfo["buildType"] == "local":
                self._topologicalOrder.insert(0, node)
        self.DepthFirstSearch(onNodeFinish=addToTopologicalOrder)
        return self._topologicalOrder
