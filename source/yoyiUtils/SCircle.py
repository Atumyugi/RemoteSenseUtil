# encoding: utf-8
"""
@version: 3.6
@author: yoyi
@file: SCircle.py
@time: 2021/8/19 15:39
"""

import math
from shapely import wkt
from shapely.geometry import Polygon,Point,LineString,MultiPolygon
import geopandas
import matplotlib.pyplot as plt
import math
class SCircle:

    def __init__(self,Pointparam,length,circleResolution=16):
        """
        创建SPoint的各种方式：
        1.wkt 给我wkt,直接根据wkt创建点
        2.list 给我python的数组 example： [a,b] 根据这个创建点
        3.tuple 给我字符串 example: (a,b) 根据这个创建点
        :param params:
        :param createOption:
        """
        if type(Pointparam) == str:
            self.circle = wkt.loads(Pointparam).buffer(length,resolution=circleResolution) #type: Polygon

        elif type(Pointparam) == list:
            self.circle = Point(tuple(Pointparam)).buffer(length,resolution=circleResolution) #type: Polygon
        elif type(Pointparam) == tuple:
            self.circle = Point(Pointparam).buffer(length,resolution=circleResolution) #type: Polygon
        else:
            print("未读懂输入参数!!!")
            raise ValueError

    # 八等分圆
    def equalPartby8(self)->MultiPolygon:
        minX,minY,maxX,maxY = self.circle.bounds
        midX = (maxX + minX) / 2
        midY = (maxY + minY) / 2
        line1 = LineString([(minX, minY), (maxX, maxY)])
        line2 = LineString([(minX, maxY), (maxX, minY)])
        line3 = LineString([(minX, midY), (maxX, midY)])
        line4 = LineString([(midX, minY), (midX, maxY)])
        res = self.circle.difference(line1.buffer(0.001))
        res = res.difference(line2.buffer(0.001))
        res = res.difference(line3.buffer(0.001))
        res = res.difference(line4.buffer(0.001))
        return res



# 计算a 和 b之间的坐标距离 其实就是计算直角三角形的第三边长度
def pointDis(a1,a2,b1,b2):
    c = abs(a1-b1)
    d = abs(a2-b2)
    return math.sqrt(math.pow(c, 2) + math.pow(d, 2))


if __name__ == '__main__':
    str = "POLYGON ((-3 0,0 -3,3 0,0 3,-3 0),(-1 0,0 -1,1 0,0 1,-1 0))"
    polyA = wkt.loads(str)
    #plt.plot(*polyA.exterior.xy)


    minX, minY, maxX, maxY = polyA.bounds
    midX = (maxX + minX)/2
    midY = (maxY + minY)/2
    cir = SCircle((midX, midY), pointDis(midX,minY,midX,midY))
    plt.plot(*cir.circle.exterior.xy)
    cir.equalPartby8()
    line1 = LineString([(minX, minY), (maxX, maxY)])
    line2 = LineString([(minX, maxY), (maxX, minY)])
    line3 = LineString([(minX, midY), (maxX, midY)])
    line4 = LineString([(midX, minY), (midX, maxY)])

    cir.circle = cir.circle.difference(line1.buffer(0.001))
    cir.circle = cir.circle.difference(line2.buffer(0.001))
    cir.circle = cir.circle.difference(line3.buffer(0.001))
    cir.circle = cir.circle.difference(line4.buffer(0.001))

    #geopandas.GeoSeries(cir.circle).plot()
    samplePoints = []
    polygons = list(cir.circle)
    for poly in polygons:
        polyTemp = polyA.intersection(poly)
        plt.plot(*polyTemp.exterior.xy)
        if polyTemp is not None:
            center = polyTemp.centroid
            if center.within(polyA):
                te = center.buffer(0.1)
                plt.plot(*te.exterior.xy)
                # listTemp = pointStr2List(poTemp.wkt)
                # listTemp = [int(i) for i in listTemp]
                # samplePoints.append(listTemp)






    plt.show()
