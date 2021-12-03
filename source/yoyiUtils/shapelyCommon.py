#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   shapleCommon.py
@Contact :   zhijuepeng@foxmail.com
@License :   (C)Copyright 2017-9999,CGWX

@Modify Time      @Author    @Version    @Desciption
------------      -------    --------    -----------
3/8/2021 下午3:46   Yoyi      1.0         None
"""


from shapely.geometry import Polygon,Point,LineString,MultiPolygon
import shapely.vectorized as sv
from itertools import compress
import numpy as np
import matplotlib.pyplot as plt

from source.yoyiUtils import Geo2rowcol
from source.yoyiUtils import earcut
from source.yoyiUtils.SCircle import SCircle,pointDis
import random
random.seed(623)

# 将一个面字符串转为数值数组
def OldpolygonStr2List(polyStr)->list:
    clipStr = polyStr[10:-2]
    #print(clipStr)
    xys = clipStr.split(',')
    bounds = []
    for xy in xys:
        xyTemp = xy.split(' ')
        if xyTemp[0][0] == '(':
            xyTemp[0] = xyTemp[0][1:]
        if xyTemp[1][-1] == ')':
            xyTemp[1] = xyTemp[1][:-1]
        bounds.append(list(map(float, xyTemp)))
    return bounds

# 将一个面字符串转为数值数组
def polygonStr2List(polyStr)->list:
    clipStr = polyStr[10:-2]
    #print(clipStr)
    strs = clipStr.split('),(')
    res = []
    for strTemp in strs:
        xys = strTemp.split(',')
        bounds = []
        for xy in xys:
            xyTemp = xy.split(' ')
            bounds.append(list(map(float, xyTemp)))
        res.append(bounds)
    return res

# 将一个面字符串转为数值数组
def polygonStr2MathList(polyStr)->list:
    clipStr = polyStr[10:-2]
    #print(clipStr)
    xys = clipStr.split(',')
    bounds = []
    for xy in xys:
        xyTemp = xy.split(' ')
        for i in xyTemp:
            bounds.append(float(i))
    return bounds

def polyList2MathList(polyList):
    res = []
    for xys in polyList:
        res.append(xys[0])
        res.append(xys[1])
    return res

# 将一个点字符串转为数值数组
def pointStr2List(pointStr)->list:
    clipStr = pointStr[7:-1]
    xy = clipStr.split(' ')
    xy = list(map(float, xy))
    return xy

def pointStr2IntList(pointStr)->list:
    clipStr = pointStr[7:-1]
    xy = clipStr.split(' ')
    xy = list(map(float, xy))
    xy = list(map(int, xy))
    return xy


# 将一个面矢量 数值数组转为 Polygon
def polyList2ShapelyPolygon(xys)->Polygon:
    #print(xys)
    if len(xys) == 1:
        tupleXY = []
        for xy in xys[0]:
            tupleXY.append(tuple(xy))
        #print(tupleXY)
        # buffer 解决拓扑逻辑的bug
        poly = Polygon(tupleXY).buffer(0.001)
        return poly
    else:
        # 挖空洞
        res = []
        for i in range(len(xys)):
            tupleXY = []
            for xy in xys[i]:
                tupleXY.append(tuple(xy))
            res.append(tupleXY)
        poly = Polygon(res[0], [temp for temp in res[1:]]).buffer(0.001)
        return poly




# 给定行数和列数 划分面矢量并且采样中心点
def samplePolygonByMatrixCenter(polyList,segNetNum=5,minArea=1):
    """
    给定行数和列数 划分面矢量并且逐步采样中心点
    :param polyList: [[x,y],[x,y]]类型的数组
    :param segNetNum: 分割的数量
    :param minArea: 若小于该面积，则只采样一个中心点
    :return:  [[x,y],[x,y]] 的采样点
    """
    polyA = polyList2ShapelyPolygon(polyList)
    if polyA.area <= minArea:
        #print(f"该地区面积小于{minArea},仅选取一个中心点...")
        poT = pointStr2IntList(polyA.centroid.wkt)
        return Geo2rowcol.field3_3(poT[0],poT[1])
    polyNp = np.array(polyList)
    xMin, yMin, xMax, yMax = polyA.bounds
    xSize = xMax - xMin
    ySize = yMax - yMin
    fishNetSize = xSize/float(segNetNum) if xSize > ySize else ySize/float(segNetNum)
    xLoopNum = int(xSize / fishNetSize) if int(xSize / fishNetSize) > 0 else 1
    yLoopNum = int(ySize / fishNetSize) if int(ySize / fishNetSize) > 0 else 1
    samplePoints = []
    for i in range(xLoopNum):
        for j in range(yLoopNum):
            x1 = xMin + i*fishNetSize
            y1 = yMin + j*fishNetSize
            x2 = xMin + (i+1)*fishNetSize
            y2 = yMin + (j+1)*fishNetSize

            xys = [[[x1,y1],[x1,y2],[x2,y2],[x2,y1],[x1,y1]]]
            polyFish = polyList2ShapelyPolygon(xys)
            # 对渔网进行相交操作
            polyInter = polyA.intersection(polyFish)
            if not polyInter.is_empty:
                poTemp = polyInter.centroid #相交
                if poTemp.within(polyA):
                    listTemp = pointStr2List(poTemp.wkt)
                    listTemp = [int(i) for i in listTemp]
                    samplePoints.append(listTemp)

    return samplePoints

# 根据earcut来采样面矢量中的点
def samplePolygonByEarCut(polyList,minArea=50):
    mathList = polyList2MathList(polyList[0])
    polyA = polyList2ShapelyPolygon(polyList)
    # if polyA.area <= minArea:
    #     #print(f"该地区面积小于{minArea},仅选取一个中心点...")
    #     cent = []
    #     cent.append(pointStr2IntList(polyA.centroid.wkt))
    #     return cent
    if polyA.area <= minArea:
        #print(f"该地区面积小于{minArea},仅选取一个中心点...")
        poT = pointStr2IntList(polyA.centroid.wkt)
        return Geo2rowcol.field3_3(poT[0],poT[1])
    #print(mathList)
    res = earcut.earcut(mathList)
    polyRes = earcut.res2ShapePolygon(polyList[0], res)
    # import geopandas
    # geopandas.GeoSeries(polyRes).plot()
    # plt.show()
    samplePoints = []
    for polyTemp in polyRes:
        if (polyTemp is not None) and (not polyTemp.centroid.wkt.__eq__("POINT EMPTY")):
            samplePoints.append(pointStr2IntList(polyTemp.centroid.wkt))

    return samplePoints

# 根据CirclePart来采样面矢量中的点
def samplePolygonByCirclePart(polyList,minArea=50):
    polyA = polyList2ShapelyPolygon(polyList)
    if polyA.area <= minArea:
        # print(f"该地区面积小于{minArea},仅选取一个中心点...")
        poT = pointStr2IntList(polyA.centroid.wkt)
        return Geo2rowcol.field3_3(poT[0], poT[1])
    minX, minY, maxX, maxY = polyA.bounds
    midX = (maxX + minX) / 2
    midY = (maxY + minY) / 2

    cir = SCircle((midX, midY), pointDis(midX,minY,midX,midY))
    polyRes = cir.equalPartby8()
    samplePoints = []
    for poly in list(polyRes):
        polyTemp = polyA.intersection(poly)
        if (polyTemp is not None) and (not polyTemp.centroid.wkt.__eq__("POINT EMPTY")):
            samplePoints.append(pointStr2IntList(polyTemp.centroid.wkt))

    return samplePoints

# 给定行数和列数 划分面矢量并且采样中心点
def samplePolygonByRandomOld(polyA:Polygon,segNetNum=10):

    # if polyA.area <= minArea:
    #     #print(f"该地区面积小于{minArea},仅选取一个中心点...")
    #     poT = pointStr2List(polyA.centroid.wkt)
    #     return [poT]
    xMin, yMin, xMax, yMax = polyA.bounds
    xSize = xMax - xMin
    ySize = yMax - yMin
    samplePoints = []
    while len(samplePoints) < segNetNum:
        ranX = random.uniform(xMin,xMax)
        ranY = random.uniform(yMin,yMax)
        ranPoint = Point(ranX,ranY)
        if polyA.contains(ranPoint):
            samplePoints.append([ranX,ranY])

    return samplePoints

def samplePolygonByRandomOld2(polyA:Polygon,segNetNum=16):

    xMin, yMin, xMax, yMax = polyA.bounds
    xSize = xMax - xMin
    ySize = yMax - yMin
    xMid = xMin + xSize/2.0
    yMid = yMin + ySize/2.0
    samplePoints = []
    while len(samplePoints) < segNetNum:
        xLeftDown = random.uniform(xMin,xMid)
        yLeftDown = random.uniform(yMin,yMid)
        ranPoint1 = Point(xLeftDown,yLeftDown)
        if polyA.contains(ranPoint1):
            samplePoints.append([xLeftDown,xLeftDown])

        xRightDown = random.uniform(xMid, xMax)
        yRightDown = random.uniform(yMin, yMid)
        ranPoint2 = Point(xRightDown, yRightDown)
        if polyA.contains(ranPoint2):
            samplePoints.append([xRightDown, yRightDown])

        xLeftUp = random.uniform(xMin, xMid)
        yLeftUp = random.uniform(yMid, yMax)
        ranPoint3 = Point(xLeftUp, yLeftUp)
        if polyA.contains(ranPoint3):
            samplePoints.append([xLeftUp, yLeftUp])

        xRightUp = random.uniform(xMid, xMax)
        yRightUp = random.uniform(yMid, yMax)
        ranPoint4 = Point(xRightUp, yRightUp)
        if polyA.contains(ranPoint4):
            samplePoints.append([xRightUp, yRightUp])
    return samplePoints

def samplePolygonByRandomNew(polyA:Polygon,segNetNum=16):
    xMin, yMin, xMax, yMax = polyA.bounds
    xSize = xMax - xMin
    ySize = yMax - yMin
    xMid = xMin + xSize/2.0
    yMid = yMin + ySize/2.0
    samplePoints = []
    segXX = segNetNum // 3  # 多加点希望一次性过,这样就少了一倍的循环次数
    while len(samplePoints) < segNetNum:
        #np.random.uniform(xMin,xMid,segXX).tolist()
        xLeft = np.random.uniform(xMin,xMid,segXX).tolist()
        yDown = np.random.uniform(yMin,yMid,segXX).tolist()
        xRight = np.random.uniform(xMid,xMax,segXX).tolist()
        yUp = np.random.uniform(yMid,yMax,segXX).tolist()

        svLD = sv.contains(polyA,xLeft,yDown)
        xld = list(compress(xLeft,svLD))
        yld = list(compress(yDown,svLD))
        for i in range(len(xld)):
            samplePoints.append([xld[i],yld[i]])

        svRD = sv.contains(polyA, xRight, yDown)
        xrd = list(compress(xRight, svRD))
        yrd = list(compress(yDown, svRD))
        for i in range(len(xrd)):
            samplePoints.append([xrd[i], yrd[i]])

        svLU = sv.contains(polyA, xLeft, yUp)
        xlu = list(compress(xLeft, svLU))
        ylu = list(compress(yUp, svLU))
        for i in range(len(xlu)):
            samplePoints.append([xlu[i], ylu[i]])

        svRU = sv.contains(polyA, xRight, yUp)
        xru = list(compress(xRight, svRU))
        yru = list(compress(yUp, svRU))
        for i in range(len(xru)):
            samplePoints.append([xru[i], yru[i]])

        segXX = segNetNum - len(samplePoints)
    return samplePoints

def samplePolygonByRandom(polyA:Polygon,segNetNum=16):
    xMin, yMin, xMax, yMax = polyA.bounds
    samplePoints = []
    segXX = segNetNum + segNetNum//4  # 多加点希望一次性过,这样就少了一倍的循环次数
    while len(samplePoints) < segNetNum:
        #np.random.uniform(xMin,xMid,segXX).tolist()
        xList = np.random.uniform(xMin,xMax,segXX).tolist()
        yList = np.random.uniform(yMin,yMax, segXX).tolist()
        svMask = sv.contains(polyA,xList,yList)
        xs = list(compress(xList,svMask))
        ys = list(compress(yList,svMask))
        for i in range(len(xs)):
            samplePoints.append([xs[i],ys[i]])
        segXX = segNetNum - len(samplePoints) + segNetNum//4
    return samplePoints

# 展示earcut分割结果
def showPolygonByEarCut(polyList):
    mathList = polyList2MathList(polyList[0])
    polyA = polyList2ShapelyPolygon(polyList)
    plt.plot(*polyA.exterior.xy)
    plt.show()
    res = earcut.earcut(mathList)
    polyRes = earcut.res2ShapePolygon(polyList[0], res)
    for polyTemp in polyRes:
        plt.plot(*polyTemp.exterior.xy)
    plt.show()

if __name__ == '__main__':
    pass

