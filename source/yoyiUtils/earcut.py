#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   earcut.py
@Contact :   zhijuepeng@foxmail.com
@License :   (C)Copyright 2017-9999,CGWX

@Modify Time      @Author    @Version    @Desciption
------------      -------    --------    -----------
14/8/2021 下午2:39   Yoyi      1.0         None
"""

import math
from shapely.geometry import Polygon
import geopandas
import matplotlib.pyplot as plt
from source.yoyiUtils import shapelyCommon
__all__ = ['earcut', 'deviation', 'flatten']


def earcut(data, holeIndices=None, dim=None):
    dim = dim or 2

    hasHoles = holeIndices and len(holeIndices)
    outerLen =  holeIndices[0] * dim if hasHoles else len(data)
    outerNode = linkedList(data, 0, outerLen, dim, True)
    triangles = []

    if not outerNode:
        return triangles

    minX = None
    minY = None
    maxX = None
    maxY = None
    x = None
    y = None
    size = None

    if hasHoles:
        outerNode = eliminateHoles(data, holeIndices, outerNode, dim)

    # if the shape is not too simple, we'll use z-order curve hash later; calculate polygon bbox
    if (len(data) > 80 * dim):
        minX = maxX = data[0]
        minY = maxY = data[1]

        for i in range(dim, outerLen, dim):
            x = data[i]
            y = data[i + 1]
            if x < minX:
                minX = x
            if y < minY:
                minY = y
            if x > maxX:
                maxX = x
            if y > maxY:
                maxY = y

        # minX, minY and size are later used to transform coords into integers for z-order calculation
        size = max(maxX - minX, maxY - minY)

    earcutLinked(outerNode, triangles, dim, minX, minY, size)

    return triangles


# create a circular doubly linked _list from polygon points in the specified winding order
def linkedList(data, start, end, dim, clockwise):
    i = None
    last = None

    if (clockwise == (signedArea(data, start, end, dim) > 0)):
        for i in range(start, end, dim):
            last = insertNode(i, data[i], data[i + 1], last)

    else:
        for i in reversed(range(start, end, dim)):
            last = insertNode(i, data[i], data[i + 1], last)

    if (last and equals(last, last.next)):
        removeNode(last)
        last = last.next

    return last


# eliminate colinear or duplicate points
def filterPoints(start, end=None):
    if not start:
        return start
    if not end:
        end = start

    p = start
    again = True

    while again or p != end:
        again = False

        if (not p.steiner and (equals(p, p.next) or area(p.prev, p, p.next) == 0)):
            removeNode(p)
            p = end = p.prev
            if (p == p.next):
                return None

            again = True

        else:
            p = p.next

    return end

# main ear slicing loop which triangulates a polygon (given as a linked _list)
def earcutLinked(ear, triangles, dim, minX, minY, size, _pass=None):
    if not ear:
        return

    # interlink polygon nodes in z-order
    if not _pass and size:
        indexCurve(ear, minX, minY, size)

    stop = ear
    prev = None
    next = None

    # iterate through ears, slicing them one by one
    while ear.prev != ear.next:
        prev = ear.prev
        next = ear.next

        if isEarHashed(ear, minX, minY, size) if size else isEar(ear):
            # cut off the triangle
            triangles.append(prev.i // dim)
            triangles.append(ear.i // dim)
            triangles.append(next.i // dim)

            removeNode(ear)

            # skipping the next vertice leads to less sliver triangles
            ear = next.next
            stop = next.next

            continue

        ear = next

        # if we looped through the whole remaining polygon and can't find any more ears
        if ear == stop:
            # try filtering points and slicing again
            if not _pass:
                earcutLinked(filterPoints(ear), triangles, dim, minX, minY, size, 1)

                # if this didn't work, try curing all small self-intersections locally
            elif _pass == 1:
                ear = cureLocalIntersections(ear, triangles, dim)
                earcutLinked(ear, triangles, dim, minX, minY, size, 2)

                # as a last resort, try splitting the remaining polygon into two
            elif _pass == 2:
                splitEarcut(ear, triangles, dim, minX, minY, size)

            break

# check whether a polygon node forms a valid ear with adjacent nodes
def isEar(ear):
    a = ear.prev
    b = ear
    c = ear.next

    if area(a, b, c) >= 0:
        return False # reflex, can't be an ear

    # now make sure we don't have other points inside the potential ear
    p = ear.next.next

    while p != ear.prev:
        if pointInTriangle(a.x, a.y, b.x, b.y, c.x, c.y, p.x, p.y) and area(p.prev, p, p.next) >= 0:
                return False
        p = p.next

    return True

def isEarHashed(ear, minX, minY, size):
    a = ear.prev
    b = ear
    c = ear.next

    if area(a, b, c) >= 0:
        return False # reflex, can't be an ear

    # triangle bbox; min & max are calculated like this for speed
    minTX = (a.x if a.x < c.x else c.x) if a.x < b.x else (b.x if b.x < c.x else c.x)
    minTY = (a.y if a.y < c.y else c.y) if a.y < b.y else (b.y if b.y < c.y else c.y)
    maxTX = (a.x if a.x > c.x else c.x) if a.x > b.x else (b.x if b.x > c.x else c.x)
    maxTY = (a.y if a.y > c.y else c.y) if a.y > b.y else (b.y if b.y > c.y else c.y)

    # z-order range for the current triangle bbox;
    minZ = zOrder(minTX, minTY, minX, minY, size)
    maxZ = zOrder(maxTX, maxTY, minX, minY, size)

    # first look for points inside the triangle in increasing z-order
    p = ear.nextZ

    while p and p.z <= maxZ:
        if p != ear.prev and p != ear.next and pointInTriangle(a.x, a.y, b.x, b.y, c.x, c.y, p.x, p.y) and area(p.prev, p, p.next) >= 0:
            return False
        p = p.nextZ

    # then look for points in decreasing z-order
    p = ear.prevZ

    while p and p.z >= minZ:
        if p != ear.prev and p != ear.next and pointInTriangle(a.x, a.y, b.x, b.y, c.x, c.y, p.x, p.y) and area(p.prev, p, p.next) >= 0:
            return False
        p = p.prevZ

    return True

# go through all polygon nodes and cure small local self-intersections
def cureLocalIntersections(start, triangles, dim):
    do = True
    p = start

    while do or p != start:
        do = False

        a = p.prev
        b = p.next.next

        if not equals(a, b) and intersects(a, p, p.next, b) and locallyInside(a, b) and locallyInside(b, a):
            triangles.append(a.i // dim)
            triangles.append(p.i // dim)
            triangles.append(b.i // dim)

            # remove two nodes involved
            removeNode(p)
            removeNode(p.next)

            p = start = b

        p = p.next

    return p

# try splitting polygon into two and triangulate them independently
def splitEarcut(start, triangles, dim, minX, minY, size):
    # look for a valid diagonal that divides the polygon into two
    do = True
    a = start

    while do or a != start:
        do = False
        b = a.next.next

        while b != a.prev:
            if a.i != b.i and isValidDiagonal(a, b):
                # split the polygon in two by the diagonal
                c = splitPolygon(a, b)

                # filter colinear points around the cuts
                a = filterPoints(a, a.next)
                c = filterPoints(c, c.next)

                # run earcut on each half
                earcutLinked(a, triangles, dim, minX, minY, size)
                earcutLinked(c, triangles, dim, minX, minY, size)
                return

            b = b.next

        a = a.next

# link every hole into the outer loop, producing a single-ring polygon without holes
def eliminateHoles(data, holeIndices, outerNode, dim):
    queue = []
    i = None
    _len = len(holeIndices)
    start = None
    end = None
    _list = None

    for i in range(len(holeIndices)):
        start = holeIndices[i] * dim
        end =  holeIndices[i + 1] * dim if i < _len - 1 else len(data)
        _list = linkedList(data, start, end, dim, False)

        if (_list == _list.next):
            _list.steiner = True

        queue.append(getLeftmost(_list))

    queue = sorted(queue, key=lambda i: i.x)

    # process holes from left to right
    for i in range(len(queue)):
        eliminateHole(queue[i], outerNode)
        outerNode = filterPoints(outerNode, outerNode.next)

    return outerNode

def compareX(a, b):
    return a.x - b.x

# find a bridge between vertices that connects hole with an outer ring and and link it
def eliminateHole(hole, outerNode):
    outerNode = findHoleBridge(hole, outerNode)
    if outerNode:
        b = splitPolygon(outerNode, hole)
        filterPoints(b, b.next)

# David Eberly's algorithm for finding a bridge between hole and outer polygon
def findHoleBridge(hole, outerNode):
    do = True
    p = outerNode
    hx = hole.x
    hy = hole.y
    qx = -math.inf
    m = None

    # find a segment intersected by a ray from the hole's leftmost point to the left;
    # segment's endpoint with lesser x will be potential connection point
    while do or p != outerNode:
        do = False
        if hy <= p.y and hy >= p.next.y and p.next.y - p.y != 0:
            x = p.x + (hy - p.y) * (p.next.x - p.x) / (p.next.y - p.y)

            if x <= hx and x > qx:
                qx = x

                if (x == hx):
                    if hy == p.y:
                        return p
                    if hy == p.next.y:
                        return p.next

                m = p if p.x < p.next.x else p.next

        p = p.next

    if not m:
        return None

    if hx == qx:
        return m.prev # hole touches outer segment; pick lower endpoint

    # look for points inside the triangle of hole point, segment intersection and endpoint;
    # if there are no points found, we have a valid connection;
    # otherwise choose the point of the minimum angle with the ray as connection point

    stop = m
    mx = m.x
    my = m.y
    tanMin = math.inf
    tan = None

    p = m.next

    while p != stop:
        hx_or_qx = hx if hy < my else qx
        qx_or_hx = qx if hy < my else hx

        if hx >= p.x and p.x >= mx and pointInTriangle(hx_or_qx, hy, mx, my, qx_or_hx, hy, p.x, p.y):

            tan = abs(hy - p.y) / (hx - p.x) # tangential

            if (tan < tanMin or (tan == tanMin and p.x > m.x)) and locallyInside(p, hole):
                m = p
                tanMin = tan

        p = p.next

    return m

# interlink polygon nodes in z-order
def indexCurve(start, minX, minY, size):
    do = True
    p = start

    while do or p != start:
        do = False

        if p.z == None:
            p.z = zOrder(p.x, p.y, minX, minY, size)

        p.prevZ = p.prev
        p.nextZ = p.next
        p = p.next

    p.prevZ.nextZ = None
    p.prevZ = None

    sortLinked(p)

# Simon Tatham's linked _list merge sort algorithm
# http:#www.chiark.greenend.org.uk/~sgtatham/algorithms/_listsort.html
def sortLinked(_list):
    do = True
    i = None
    p = None
    q = None
    e = None
    tail = None
    numMerges = None
    pSize = None
    qSize = None
    inSize = 1

    while do or numMerges > 1:
        do = False
        p = _list
        _list = None
        tail = None
        numMerges = 0

        while p:
            numMerges += 1
            q = p
            pSize = 0
            for i in range(inSize):
                pSize += 1
                q = q.nextZ
                if not q:
                    break

            qSize = inSize

            while pSize > 0 or (qSize > 0 and q):

                if pSize == 0:
                    e = q
                    q = q.nextZ
                    qSize -= 1

                elif (qSize == 0 or not q):
                    e = p
                    p = p.nextZ
                    pSize -= 1

                elif (p.z <= q.z):
                    e = p
                    p = p.nextZ
                    pSize -= 1

                else:
                    e = q
                    q = q.nextZ
                    qSize -= 1

                if tail:
                    tail.nextZ = e

                else:
                    _list = e

                e.prevZ = tail
                tail = e

            p = q

        tail.nextZ = None
        inSize *= 2

    return _list


# z-order of a point given coords and size of the data bounding box
def zOrder(x, y, minX, minY, size):
    # coords are transformed into non-negative 15-bit integer range
    x = int(32767 * (x - minX) // size)
    y = int(32767 * (y - minY) // size)

    #print(x,y)

    x = (x | (x << 8)) & 0x00FF00FF
    x = (x | (x << 4)) & 0x0F0F0F0F
    x = (x | (x << 2)) & 0x33333333
    x = (x | (x << 1)) & 0x55555555

    y = (y | (y << 8)) & 0x00FF00FF
    y = (y | (y << 4)) & 0x0F0F0F0F
    y = (y | (y << 2)) & 0x33333333
    y = (y | (y << 1)) & 0x55555555

    return x | (y << 1)

# find the leftmost node of a polygon ring
def getLeftmost(start):
    do = True
    p = start
    leftmost = start

    while do or p != start:
        do = False
        if p.x < leftmost.x:
            leftmost = p
        p = p.next

    return leftmost

# check if a point lies within a convex triangle
def pointInTriangle(ax, ay, bx, by, cx, cy, px, py):
    return (cx - px) * (ay - py) - (ax - px) * (cy - py) >= 0 and \
        (ax - px) * (by - py) - (bx - px) * (ay - py) >= 0 and \
        (bx - px) * (cy - py) - (cx - px) * (by - py) >= 0

# check if a diagonal between two polygon nodes is valid (lies in polygon interior)
def isValidDiagonal(a, b):
    return a.next.i != b.i and a.prev.i != b.i and not intersectsPolygon(a, b) and \
        locallyInside(a, b) and locallyInside(b, a) and middleInside(a, b)

# signed area of a triangle
def area(p, q, r):
    return (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y)

# check if two points are equal
def equals(p1, p2):
    return p1.x == p2.x and p1.y == p2.y


# check if two segments intersect
def intersects(p1, q1, p2, q2):
    if (equals(p1, q1) and equals(p2, q2)) or (equals(p1, q2) and equals(p2, q1)):
        return True

    return area(p1, q1, p2) > 0 != area(p1, q1, q2) > 0 and \
        area(p2, q2, p1) > 0 != area(p2, q2, q1) > 0

# check if a polygon diagonal intersects any polygon segments
def intersectsPolygon(a, b):
    do = True
    p = a

    while do or p != a:
        do = False
        if (p.i != a.i and p.next.i != a.i and p.i != b.i and p.next.i != b.i and intersects(p, p.next, a, b)):
            return True

        p = p.next

    return False

# check if a polygon diagonal is locally inside the polygon
def locallyInside(a, b):
    if area(a.prev, a, a.next) < 0:
        return  area(a, b, a.next) >= 0 and area(a, a.prev, b) >= 0
    else:
        return area(a, b, a.prev) < 0 or area(a, a.next, b) < 0

# check if the middle point of a polygon diagonal is inside the polygon
def middleInside(a, b):
    do = True
    p = a
    inside = False
    px = (a.x + b.x) / 2
    py = (a.y + b.y) / 2

    while do or p != a:
        do = False
        if ((p.y > py) != (p.next.y > py)) and (px < (p.next.x - p.x) * (py - p.y) / (p.next.y - p.y) + p.x):
            inside = not inside

        p = p.next

    return inside

# link two polygon vertices with a bridge; if the vertices belong to the same ring, it splits polygon into two;
# if one belongs to the outer ring and another to a hole, it merges it into a single ring
def splitPolygon(a, b):
    a2 = Node(a.i, a.x, a.y)
    b2 = Node(b.i, b.x, b.y)
    an = a.next
    bp = b.prev

    a.next = b
    b.prev = a

    a2.next = an
    an.prev = a2

    b2.next = a2
    a2.prev = b2

    bp.next = b2
    b2.prev = bp

    return b2


# create a node and optionally link it with previous one (in a circular doubly linked _list)
def insertNode(i, x, y, last):
    p = Node(i, x, y)

    if not last:
        p.prev = p
        p.next = p

    else:
        p.next = last.next
        p.prev = last
        last.next.prev = p
        last.next = p

    return p

def removeNode(p):
    p.next.prev = p.prev
    p.prev.next = p.next

    if p.prevZ:
        p.prevZ.nextZ = p.nextZ

    if p.nextZ:
        p.nextZ.prevZ = p.prevZ

class Node(object):
    def __init__(self, i, x, y):
    # vertice index in coordinates array
        self.i = i

        # vertex coordinates

        self.x = x
        self.y = y

        # previous and next vertice nodes in a polygon ring
        self.prev = None
        self.next = None

        # z-order curve value
        self.z = None

        # previous and next nodes in z-order
        self.prevZ = None
        self.nextZ = None

        # indicates whether this is a steiner point
        self.steiner = False


# return a percentage difference between the polygon area and its triangulation area;
# used to verify correctness of triangulation
def deviation(data, holeIndices, dim, triangles):
    _len = len(holeIndices)
    hasHoles = holeIndices and len(holeIndices)
    outerLen = holeIndices[0] * dim if hasHoles else len(data)

    polygonArea = abs(signedArea(data, 0, outerLen, dim))

    if hasHoles:
        for i in range(_len):
            start = holeIndices[i] * dim
            end = holeIndices[i + 1] * dim if i < _len - 1 else len(data)
            polygonArea -= abs(signedArea(data, start, end, dim))

    trianglesArea = 0

    for i in range(0, len(triangles), 3):
        a = triangles[i] * dim
        b = triangles[i + 1] * dim
        c = triangles[i + 2] * dim
        trianglesArea += abs(
            (data[a] - data[c]) * (data[b + 1] - data[a + 1]) -
            (data[a] - data[b]) * (data[c + 1] - data[a + 1]))

    if polygonArea == 0 and trianglesArea == 0:
        return 0

    return abs((trianglesArea - polygonArea) / polygonArea)


def signedArea(data, start, end, dim):
    sum = 0
    j = end - dim

    for i in range(start, end, dim):
        sum += (data[j] - data[i]) * (data[i + 1] + data[j + 1])
        j = i
    return sum


# turn a polygon in a multi-dimensional array form (e.g. as in GeoJSON) into a form Earcut accepts
def flatten(data):
    dim = len(data[0][0])
    result = {
        'vertices': [],
        'holes': [],
        'dimensions': dim
    }
    holeIndex = 0
    for i in range(len(data)):
        for j in range(len(data[i])):
            for d in range(dim):
                result['vertices'].append(data[i][j][d])
        if i > 0:
            holeIndex += len(data[i - 1])
            result['holes'].append(holeIndex)
    return result

def unflatten(data):
    result = []
    for i in range(0, len(data), 3):
        result.append(tuple(data[i:i + 3]))
    return result

def res2ShapePolygon(polyList:list,res:list):
    polyRes = []
    for i in range(0, len(res),3):
        tupleXY = [tuple(polyList[res[i]]),tuple(polyList[res[i+1]]),tuple(polyList[res[i+2]]),tuple(polyList[res[i]])]
        polyTemp = Polygon(tupleXY)
        polyRes.append(polyTemp)
    return polyRes

if __name__ == '__main__':
    #a = "POLYGON ((120.777165953586 28.0357131158378,120.77774297288 28.0360343430735,120.77866501402 28.0362187513014,120.779247981966 28.0360581376835,120.779105214306 28.0358380375407,120.778296197564 28.0356952698802,120.777873843236 28.0354692210847,120.777165953586 28.0357131158378))"
    #a  = "POLYGON ((10.0 0.0,0.0 50.0,60.0 60.0,70.0 10.0,10.0 0.0))"
    #aList = shapleCommon.polygonStr2MathList(a)
    #aPolyList = shapleCommon.polygonStr2List(a)
    #print(aPolyList)
    #aPoly = shapleCommon.polyList2ShapelyPolygon(aPolyList)

    #polyList = shapleCommon.polygonStr2List(a)
    aList = [8270.000000003814, 768.0000000062043, 8272.00000001118, 768.0000000062043, 8272.00000001118, 768.9999999962057, 8280.000000035167, 768.9999999962057, 8280.000000035167, 769.9999999989761, 8285.000000049931, 769.9999999989761, 8285.000000049931, 771.0000000017466, 8290.000000064694, 771.0000000017466, 8290.000000064694, 772.0000000054291, 8295.999999955451, 772.0000000054291, 8295.999999955451, 772.9999999954305, 8301.999999972073, 772.9999999954305, 8301.999999972073, 773.9999999982009, 8307.999999990521, 773.9999999982009, 8307.999999990521, 775.0000000009713, 8313.000000005284, 775.0000000009713, 8313.000000005284, 776.0000000046539, 8314.000000008968, 776.0000000046539, 8314.000000008968, 775.0000000009713, 8315.00000001265, 775.0000000009713, 8315.00000001265, 776.0000000046539, 8322.000000032955, 776.0000000046539, 8322.000000032955, 776.9999999946552, 8325.000000042179, 776.9999999946552, 8325.000000042179, 777.9999999974257, 8328.000000051401, 777.9999999974257, 8328.000000051401, 780.0000000038787, 8331.000000060625, 780.0000000038787, 8331.000000060625, 779.0000000001961, 8338.999999956923, 779.0000000001961, 8338.999999956923, 780.0000000038787, 8342.999999968004, 780.0000000038787, 8342.999999968004, 781.0000000066491, 8347.999999982769, 781.0000000066491, 8347.999999982769, 781.9999999966504, 8356.000000006756, 781.9999999966504, 8356.000000006756, 782.9999999994209, 8360.000000019661, 782.9999999994209, 8360.000000019661, 784.0000000031034, 8366.000000038108, 784.0000000031034, 8366.000000038108, 785.0000000058739, 8372.000000054732, 785.0000000058739, 8372.000000054732, 785.9999999958752, 8377.999999945487, 785.9999999958752, 8377.999999945487, 786.9999999986456, 8382.999999960251, 786.9999999986456, 8382.999999960251, 788.0000000023281, 8389.999999982381, 788.0000000023281, 8389.999999982381, 789.0000000050985, 8393.999999993463, 789.0000000050985, 8393.999999993463, 789.9999999950999, 8400.000000011909, 789.9999999950999, 8400.000000011909, 790.9999999978703, 8403.000000021133, 790.9999999978703, 8403.000000021133, 792.0000000015528, 8407.000000032214, 792.0000000015528, 8407.000000032214, 790.9999999978703, 8409.00000003958, 790.9999999978703, 8409.00000003958, 792.0000000015528, 8413.00000005066, 792.0000000015528, 8413.00000005066, 793.0000000043233, 8417.000000063566, 793.0000000043233, 8417.000000063566, 793.9999999943246, 8422.999999952499, 793.9999999943246, 8422.999999952499, 794.9999999970951, 8431.99999998017, 794.9999999970951, 8431.99999998017, 796.0000000007776, 8435.99999999125, 796.0000000007776, 8435.99999999125, 797.000000003548, 8437.999999998616, 797.000000003548, 8437.999999998616, 797.9999999935494, 8449.000000031827, 797.9999999935494, 8449.000000031827, 798.9999999963198, 8453.000000042908, 798.9999999963198, 8453.000000042908, 800.0000000000024, 8458.000000057673, 800.0000000000024, 8458.000000057673, 801.0000000027728, 8466.999999957652, 801.0000000027728, 8466.999999957652, 802.0000000055433, 8469.999999966876, 802.0000000055433, 8469.999999966876, 802.9999999955446, 8474.999999981641, 802.9999999955446, 8474.999999981641, 803.9999999992272, 8477.999999990863, 803.9999999992272, 8477.999999990863, 805.0000000019976, 8481.000000000087, 805.0000000019976, 8481.000000000087, 803.9999999992272, 8484.00000000931, 803.9999999992272, 8484.00000000931, 805.0000000019976, 8489.000000024074, 805.0000000019976, 8489.000000024074, 806.000000004768, 8488.000000020393, 806.000000004768, 8488.000000020393, 819.9999999961261, 8487.00000001671, 819.9999999961261, 8477.999999990863, 819.9999999961261, 8477.999999990863, 819.0000000061248, 8475.999999983498, 819.0000000061248, 8475.999999983498, 820.9999999988966, 8474.999999981641, 820.9999999988966, 8470.999999968733, 820.9999999988966, 8470.999999968733, 819.9999999961261, 8463.99999994843, 819.9999999961261, 8463.99999994843, 820.9999999988966, 8462.999999944746, 820.9999999988966, 8462.999999944746, 827.0000000045742, 8461.999999942887, 827.0000000045742, 8459.999999935522, 827.0000000045742, 8459.999999935522, 827.9999999945755, 8459.000000061356, 827.9999999945755, 8458.000000057673, 827.9999999945755, 8458.000000057673, 830.0000000001164, 8457.000000055814, 830.0000000001164, 8457.000000055814, 831.000000003799, 8456.000000052132, 831.000000003799, 8456.000000052132, 828.999999997346, 8451.000000037367, 828.999999997346, 8451.000000037367, 830.0000000001164, 8450.000000033686, 830.0000000001164, 8449.000000031827, 830.0000000001164, 8449.000000031827, 831.000000003799, 8448.000000028145, 831.000000003799, 8447.000000024462, 831.000000003799, 8447.000000024462, 832.0000000065694, 8446.000000022603, 832.0000000065694, 8446.000000022603, 832.9999999965708, 8445.000000018921, 832.9999999965708, 8445.000000018921, 835.0000000030237, 8441.00000000784, 835.0000000030237, 8441.00000000784, 832.0000000065694, 8433.99999998571, 832.0000000065694, 8433.99999998571, 828.999999997346, 8430.999999976486, 828.999999997346, 8430.999999976486, 827.0000000045742, 8431.99999998017, 827.0000000045742, 8431.99999998017, 826.0000000008918, 8432.999999983851, 826.0000000008918, 8432.999999983851, 824.9999999981213, 8433.99999998571, 824.9999999981213, 8433.99999998571, 823.0000000053495, 8434.999999989392, 823.0000000053495, 8434.999999989392, 820.9999999988966, 8432.999999983851, 820.9999999988966, 8432.999999983851, 822.000000001667, 8431.99999998017, 822.000000001667, 8431.99999998017, 823.0000000053495, 8430.999999976486, 823.0000000053495, 8430.999999976486, 824.9999999981213, 8429.999999974629, 824.9999999981213, 8429.999999974629, 827.0000000045742, 8428.999999970945, 827.0000000045742, 8427.999999967264, 827.0000000045742, 8427.999999967264, 827.9999999945755, 8426.999999965405, 827.9999999945755, 8420.999999946958, 827.9999999945755, 8420.999999946958, 828.999999997346, 8418.999999941418, 828.999999997346, 8418.999999941418, 827.0000000045742, 8419.999999943275, 827.0000000045742, 8420.999999946958, 827.0000000045742, 8420.999999946958, 826.0000000008918, 8419.999999943275, 826.0000000008918, 8419.999999943275, 824.9999999981213, 8418.999999941418, 824.9999999981213, 8418.999999941418, 823.9999999953509, 8417.999999937734, 823.9999999953509, 8417.999999937734, 822.000000001667, 8417.000000063566, 822.000000001667, 8417.000000063566, 823.0000000053495, 8416.000000059885, 823.0000000053495, 8416.000000059885, 824.9999999981213, 8415.000000056201, 824.9999999981213, 8414.000000054344, 824.9999999981213, 8414.000000054344, 826.0000000008918, 8413.00000005066, 826.0000000008918, 8410.000000041438, 826.0000000008918, 8410.000000041438, 827.0000000045742, 8409.00000003958, 827.0000000045742, 8409.00000003958, 831.000000003799, 8408.000000035898, 831.000000003799, 8408.000000035898, 832.0000000065694, 8411.00000004512, 832.0000000065694, 8411.00000004512, 833.9999999993412, 8416.000000059885, 833.9999999993412, 8416.000000059885, 836.0000000057942, 8415.000000056201, 836.0000000057942, 8412.000000048803, 836.0000000057942, 8412.000000048803, 836.9999999957955, 8414.000000054344, 836.9999999957955, 8414.000000054344, 837.999999998566, 8415.000000056201, 837.999999998566, 8415.000000056201, 840.0000000050189, 8410.000000041438, 840.0000000050189, 8410.000000041438, 837.999999998566, 8408.000000035898, 837.999999998566, 8408.000000035898, 836.0000000057942, 8405.000000026674, 836.0000000057942, 8405.000000026674, 839.0000000022485, 8404.00000002299, 839.0000000022485, 8403.000000021133, 839.0000000022485, 8403.000000021133, 840.0000000050189, 8399.000000008227, 840.0000000050189, 8399.000000008227, 839.0000000022485, 8397.000000002687, 839.0000000022485, 8397.000000002687, 840.0000000050189, 8395.999999999003, 840.0000000050189, 8395.999999999003, 840.9999999950203, 8393.999999993463, 840.9999999950203, 8393.999999993463, 839.0000000022485, 8394.999999997144, 839.0000000022485, 8394.999999997144, 837.999999998566, 8395.999999999003, 837.999999998566, 8395.999999999003, 836.9999999957955, 8397.000000002687, 836.9999999957955, 8397.000000002687, 833.9999999993412, 8399.000000008227, 833.9999999993412, 8400.000000011909, 833.9999999993412, 8400.000000011909, 832.9999999965708, 8403.000000021133, 832.9999999965708, 8404.00000002299, 832.9999999965708, 8404.00000002299, 832.0000000065694, 8405.000000026674, 832.0000000065694, 8405.000000026674, 831.000000003799, 8401.000000015592, 831.000000003799, 8401.000000015592, 827.0000000045742, 8399.000000008227, 827.0000000045742, 8399.000000008227, 827.9999999945755, 8398.000000006368, 827.9999999945755, 8398.000000006368, 832.9999999965708, 8397.000000002687, 832.9999999965708, 8392.99999998978, 832.9999999965708, 8392.99999998978, 830.0000000001164, 8390.999999984238, 830.0000000001164, 8390.999999984238, 832.0000000065694, 8389.999999982381, 832.0000000065694, 8386.999999973157, 832.0000000065694, 8386.999999973157, 833.9999999993412, 8385.999999969476, 833.9999999993412, 8385.999999969476, 836.9999999957955, 8384.999999965792, 836.9999999957955, 8380.99999995471, 836.9999999957955, 8380.99999995471, 840.0000000050189, 8382.999999960251, 840.0000000050189, 8382.999999960251, 839.0000000022485, 8386.999999973157, 839.0000000022485, 8386.999999973157, 840.0000000050189, 8391.999999987922, 840.0000000050189, 8391.999999987922, 843.0000000014733, 8390.999999984238, 843.0000000014733, 8388.999999978698, 843.0000000014733, 8388.999999978698, 844.0000000042437, 8387.999999975016, 844.0000000042437, 8386.999999973157, 844.0000000042437, 8386.999999973157, 844.9999999942451, 8380.99999995471, 844.9999999942451, 8380.99999995471, 841.9999999977907, 8378.99999994917, 841.9999999977907, 8378.99999994917, 840.0000000050189, 8374.999999936264, 840.0000000050189, 8374.999999936264, 839.0000000022485, 8374.000000062097, 839.0000000022485, 8374.000000062097, 836.0000000057942, 8371.000000052873, 836.0000000057942, 8371.000000052873, 836.9999999957955, 8370.000000049191, 836.9999999957955, 8370.000000049191, 839.0000000022485, 8368.000000043648, 839.0000000022485, 8368.000000043648, 836.9999999957955, 8367.000000039967, 836.9999999957955, 8367.000000039967, 837.999999998566, 8366.000000038108, 837.999999998566, 8364.000000030743, 837.999999998566, 8364.000000030743, 839.0000000022485, 8361.00000002152, 839.0000000022485, 8361.00000002152, 836.9999999957955, 8362.000000025202, 836.9999999957955, 8362.000000025202, 836.0000000057942, 8361.00000002152, 836.0000000057942, 8361.00000002152, 832.0000000065694, 8358.00000001412, 832.0000000065694, 8358.00000001412, 828.999999997346, 8359.00000001598, 828.999999997346, 8359.00000001598, 826.0000000008918, 8358.00000001412, 826.0000000008918, 8358.00000001412, 827.0000000045742, 8357.000000010437, 827.0000000045742, 8351.999999995674, 827.0000000045742, 8351.999999995674, 827.9999999945755, 8350.999999991991, 827.9999999945755, 8350.999999991991, 832.0000000065694, 8351.999999995674, 832.0000000065694, 8351.999999995674, 833.9999999993412, 8350.999999991991, 833.9999999993412, 8346.99999998091, 833.9999999993412, 8346.99999998091, 835.0000000030237, 8345.999999977228, 835.0000000030237, 8345.999999977228, 836.9999999957955, 8344.999999973545, 836.9999999957955, 8344.999999973545, 837.999999998566, 8340.999999962463, 837.999999998566, 8340.999999962463, 836.0000000057942, 8338.999999956923, 836.0000000057942, 8338.999999956923, 836.9999999957955, 8337.99999995324, 836.9999999957955, 8337.99999995324, 835.0000000030237, 8336.999999949558, 835.0000000030237, 8336.999999949558, 832.9999999965708, 8335.999999947699, 832.9999999965708, 8335.999999947699, 831.000000003799, 8330.000000056943, 831.000000003799, 8330.000000056943, 832.0000000065694, 8328.000000051401, 832.0000000065694, 8328.000000051401, 830.0000000001164, 8329.000000055084, 830.0000000001164, 8329.000000055084, 828.999999997346, 8330.000000056943, 828.999999997346, 8330.000000056943, 827.9999999945755, 8327.00000004772, 827.9999999945755, 8327.00000004772, 826.0000000008918, 8322.000000032955, 826.0000000008918, 8322.000000032955, 820.9999999988966, 8321.000000029273, 820.9999999988966, 8321.000000029273, 819.9999999961261, 8318.000000021873, 819.9999999961261, 8318.000000021873, 820.9999999988966, 8317.00000001819, 820.9999999988966, 8316.000000014508, 820.9999999988966, 8316.000000014508, 826.0000000008918, 8315.00000001265, 826.0000000008918, 8315.00000001265, 828.999999997346, 8323.000000036638, 828.999999997346, 8323.000000036638, 830.0000000001164, 8324.000000038495, 830.0000000001164, 8324.000000038495, 831.000000003799, 8325.000000042179, 831.000000003799, 8325.000000042179, 832.0000000065694, 8326.00000004586, 832.0000000065694, 8326.00000004586, 832.9999999965708, 8327.00000004772, 832.9999999965708, 8327.00000004772, 833.9999999993412, 8328.000000051401, 833.9999999993412, 8328.000000051401, 835.0000000030237, 8329.000000055084, 835.0000000030237, 8329.000000055084, 836.0000000057942, 8330.000000056943, 836.0000000057942, 8330.000000056943, 836.9999999957955, 8331.000000060625, 836.9999999957955, 8331.000000060625, 837.999999998566, 8336.999999949558, 837.999999998566, 8336.999999949558, 848.0000000034684, 8335.999999947699, 848.0000000034684, 8335.999999947699, 849.9999999962401, 8317.00000001819, 849.9999999962401, 8317.00000001819, 848.9999999934697, 8316.000000014508, 848.9999999934697, 8316.000000014508, 848.0000000034684, 8306.999999988662, 848.0000000034684, 8306.999999988662, 844.9999999942451, 8300.999999970216, 844.9999999942451, 8300.999999970216, 840.9999999950203, 8296.99999995731, 840.9999999950203, 8296.99999995731, 837.999999998566, 8297.999999960992, 837.999999998566, 8297.999999960992, 836.0000000057942, 8296.99999995731, 836.0000000057942, 8296.99999995731, 833.9999999993412, 8295.999999955451, 833.9999999993412, 8295.999999955451, 832.0000000065694, 8288.000000059154, 832.0000000065694, 8288.000000059154, 832.9999999965708, 8287.000000055472, 832.9999999965708, 8286.000000053613, 832.9999999965708, 8286.000000053613, 833.9999999993412, 8283.00000004439, 833.9999999993412, 8283.00000004439, 831.000000003799, 8280.000000035167, 831.000000003799, 8280.000000035167, 830.0000000001164, 8279.000000031483, 830.0000000001164, 8279.000000031483, 828.999999997346, 8278.000000027801, 828.999999997346, 8278.000000027801, 830.0000000001164, 8277.000000025942, 830.0000000001164, 8277.000000025942, 831.000000003799, 8275.000000020402, 831.000000003799, 8275.000000020402, 830.0000000001164, 8274.00000001672, 830.0000000001164, 8274.00000001672, 827.9999999945755, 8272.00000001118, 827.9999999945755, 8272.00000001118, 822.000000001667, 8270.000000003814, 822.000000001667, 8270.000000003814, 823.0000000053495, 8269.000000001955, 823.0000000053495, 8266.99999999459, 823.0000000053495, 8266.99999999459, 823.9999999953509, 8265.999999992731, 823.9999999953509, 8265.999999992731, 824.9999999981213, 8263.99999998719, 824.9999999981213, 8263.99999998719, 823.9999999953509, 8260.999999977968, 823.9999999953509, 8260.999999977968, 823.0000000053495, 8259.999999974285, 823.0000000053495, 8259.999999974285, 822.000000001667, 8258.999999970603, 822.000000001667, 8258.999999970603, 823.0000000053495, 8257.999999968744, 823.0000000053495, 8254.99999995952, 823.0000000053495, 8254.99999995952, 823.9999999953509, 8253.999999955839, 823.9999999953509, 8253.999999955839, 824.9999999981213, 8250.999999946614, 824.9999999981213, 8250.999999946614, 820.9999999988966, 8248.999999941074, 820.9999999988966, 8248.999999941074, 823.0000000053495, 8247.999999937392, 823.0000000053495, 8247.999999937392, 823.9999999953509, 8247.000000063224, 823.9999999953509, 8246.000000061365, 823.9999999953509, 8246.000000061365, 824.9999999981213, 8245.000000057684, 824.9999999981213, 8245.000000057684, 826.0000000008918, 8240.000000042919, 826.0000000008918, 8240.000000042919, 823.0000000053495, 8241.000000044778, 823.0000000053495, 8241.000000044778, 820.9999999988966, 8240.000000042919, 820.9999999988966, 8240.000000042919, 822.000000001667, 8239.000000039236, 822.000000001667, 8238.000000035554, 822.000000001667, 8238.000000035554, 823.9999999953509, 8235.000000028154, 823.9999999953509, 8235.000000028154, 822.000000001667, 8236.000000030013, 822.000000001667, 8237.000000033695, 822.000000001667, 8237.000000033695, 819.9999999961261, 8234.000000024473, 819.9999999961261, 8234.000000024473, 823.0000000053495, 8230.000000011567, 823.0000000053495, 8230.000000011567, 822.000000001667, 8229.000000009708, 822.000000001667, 8229.000000009708, 816.9999999996718, 8228.000000006024, 816.9999999996718, 8228.000000006024, 810.999999993994, 8230.000000011567, 810.999999993994, 8231.000000015249, 810.999999993994, 8231.000000015249, 810.0000000039927, 8232.000000018932, 810.0000000039927, 8232.000000018932, 809.0000000012222, 8233.00000002079, 809.0000000012222, 8234.000000024473, 809.0000000012222, 8234.000000024473, 806.9999999947694, 8231.000000015249, 806.9999999947694, 8231.000000015249, 805.0000000019976, 8237.000000033695, 805.0000000019976, 8237.000000033695, 806.000000004768, 8238.000000035554, 806.000000004768, 8238.000000035554, 809.0000000012222, 8239.000000039236, 809.0000000012222, 8239.000000039236, 807.9999999984518, 8241.000000044778, 807.9999999984518, 8241.000000044778, 809.0000000012222, 8243.000000052143, 809.0000000012222, 8243.000000052143, 807.9999999984518, 8244.000000054, 807.9999999984518, 8244.000000054, 806.000000004768, 8245.000000057684, 806.000000004768, 8245.000000057684, 803.9999999992272, 8246.000000061365, 803.9999999992272, 8247.000000063224, 803.9999999992272, 8247.000000063224, 798.9999999963198, 8245.000000057684, 798.9999999963198, 8245.000000057684, 797.9999999935494, 8244.000000054, 797.9999999935494, 8244.000000054, 794.9999999970951, 8241.000000044778, 794.9999999970951, 8241.000000044778, 790.9999999978703, 8242.00000004846, 790.9999999978703, 8242.00000004846, 789.9999999950999, 8243.000000052143, 789.9999999950999, 8243.000000052143, 786.9999999986456, 8244.000000054, 786.9999999986456, 8244.000000054, 781.9999999966504, 8246.000000061365, 781.9999999966504, 8246.000000061365, 782.9999999994209, 8247.000000063224, 782.9999999994209, 8247.000000063224, 784.0000000031034, 8248.999999941074, 784.0000000031034, 8248.999999941074, 782.9999999994209, 8249.999999944757, 782.9999999994209, 8250.999999946614, 782.9999999994209, 8250.999999946614, 781.0000000066491, 8249.999999944757, 781.0000000066491, 8249.999999944757, 779.0000000001961, 8250.999999946614, 779.0000000001961, 8251.999999950298, 779.0000000001961, 8251.999999950298, 776.0000000046539, 8254.99999995952, 776.0000000046539, 8255.999999963204, 776.0000000046539, 8255.999999963204, 775.0000000009713, 8258.999999970603, 775.0000000009713, 8259.999999974285, 775.0000000009713, 8259.999999974285, 773.9999999982009, 8262.999999983509, 773.9999999982009, 8262.999999983509, 775.0000000009713, 8266.99999999459, 775.0000000009713, 8266.99999999459, 773.9999999982009, 8267.999999998274, 773.9999999982009, 8267.999999998274, 772.9999999954305, 8265.999999992731, 772.9999999954305, 8265.999999992731, 772.0000000054291, 8264.99999998905, 772.0000000054291, 8264.99999998905, 771.0000000017466, 8265.999999992731, 771.0000000017466, 8266.99999999459, 771.0000000017466, 8266.99999999459, 769.9999999989761, 8267.999999998274, 769.9999999989761, 8267.999999998274, 768.9999999962057, 8269.000000001955, 768.9999999962057, 8270.000000003814, 768.9999999962057, 8270.000000003814, 768.0000000062043]
    res = earcut(aList)
    # polyList = res2ShapePolygon(aPolyList,res)
    # for polyTemp in polyList:
    #     plt.plot(*polyTemp.exterior.xy)
    # plt.plot(*aPoly.exterior.xy)
    # plt.show()
