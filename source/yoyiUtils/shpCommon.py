#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   shpCommon.py
@Contact :   zhijuepeng@foxmail.com
@License :   (C)Copyright 2017-9999,CGWX

@Modify Time      @Author    @Version    @Desciption
------------      -------    --------    -----------
29/7/2021 下午1:41   Yoyi      1.0         None
"""

#防止报错  ValueError: GEOSGeom_createLinearRing_r returned a NULL pointer
from shapely import speedups
speedups.disable()
from source.yoyiUtils import Geo2rowcol
from osgeo import ogr,gdal,osr
from source.yoyiUtils import shapleCommon

class ShapeFile:

    def __init__(self,shpPath):
        self.shpPath = shpPath
        driver = ogr.GetDriverByName('ESRI Shapefile')
        self.shpDs = driver.Open(shpPath,1) # type: ogr.DataSource
        assert isinstance(self.shpDs,ogr.DataSource),"shp文件打开失败"
        self.shpLayer = self.shpDs.GetLayerByIndex(0) # type: ogr.Layer
        assert isinstance(self.shpLayer,ogr.Layer),"获取图层失败"
        self.shpSpatialRef = self.shpLayer.GetSpatialRef() #type: osr.SpatialReference

        #self.printFieldInfo()

    # 打印shp文件的属性表信息
    def printFieldInfo(self):
        shpDefn = self.shpLayer.GetLayerDefn()  # type: ogr.FeatureDefn
        fieldCount = shpDefn.GetFieldCount()
        print(f"{self.shpPath}文件的属性表信息：")
        for i in range(fieldCount):
            fieldTemp = shpDefn.GetFieldDefn(i)  # type: ogr.FieldDefn
            print("%s: %s(%d.%d)" % (
                fieldTemp.GetNameRef(), fieldTemp.GetFieldTypeName(fieldTemp.GetType()), fieldTemp.GetWidth(),
                fieldTemp.GetPrecision()))

    # 汇总shp文件的属性表名字并返回一个List
    def getField2List(self)->list:
        shpDefn = self.shpLayer.GetLayerDefn() # type: ogr.FeatureDefn
        fieldCount  = shpDefn.GetFieldCount()
        res = []
        for i in range(fieldCount):
            fieldTemp = shpDefn.GetFieldDefn(i) # type: ogr.FieldDefn
            res.append(fieldTemp.GetNameRef())
        return res

    # 汇总shp文件的categoryName属性的所有出现的实例
    def getCategoriesByField2List(self,categoryName):
        assert categoryName in self.getField2List(),f"NOT FOUND {categoryName} Field in {self.shpPath} File!!!"
        names = []
        feature = self.shpLayer.GetNextFeature() # type: ogr.Feature
        name = feature.GetField(categoryName)
        while feature:
            name = feature.GetField(categoryName)
            if name not in names:
                names.append(name)
            feature = self.shpLayer.GetNextFeature()
        if '0' in names:
            names.remove('0')
        return names

    # 采样 Field面矢量 中的点 -> labels[] points[] labels 和 points 是一对多的关系
    def getShpPolygonSamplePoint2PointsLabel(self,tifDs:gdal.Dataset,categoryName,segOption,fishSeg):
        assert categoryName in self.getField2List(), "属性表中没有这个属性名!"
        geomTrans = tifDs.GetGeoTransform()
        targetsr = osr.SpatialReference()
        targetsr.ImportFromWkt(tifDs.GetProjectionRef())
        feature = self.shpLayer.GetNextFeature()  # type: ogr.Feature
        labels = []
        points = []
        if segOption == 'fishSeg':
            while feature:
                label = feature.GetField(categoryName)
                labels.append(label)
                geom = feature.GetGeometryRef()  # type: ogr.Geometry
                typeName = geom.GetGeometryName()
                if typeName == "POLYGON":
                    featureWKT = geom.ExportToWkt()
                    polyList = self.geo2XY(shapleCommon.polygonStr2List(featureWKT),geomTrans,targetsr)
                    samplePoints = shapleCommon.samplePolygonByMatrixCenter(polyList,segNetNum=fishSeg)
                    points.append(samplePoints)
                elif typeName == "POINT":
                    ptsX = geom.GetX()
                    ptsY = geom.GetY()
                    points.append(self.geo2PointXY(ptsX,ptsY,geomTrans,targetsr))
                elif typeName == "MULTIPOLYGON":
                    print("找到Multi面样本，请核查...")
                    print("已自动选择最大多边形")
                    area_polygon = []
                    for j in range(geom.GetGeometryCount()):
                        pts = geom.GetGeometryRef(j)
                        area_polygon.append(pts.GetGeometryRef(0).GetArea())
                    max_index = area_polygon.index(max(area_polygon))
                    featureWKT = geom.GetGeometryRef(max_index).ExportToWkt()
                    polyList = self.geo2XY(shapleCommon.polygonStr2List(featureWKT), geomTrans, targetsr)
                    samplePoints = shapleCommon.samplePolygonByMatrixCenter(polyList)
                    points.append(samplePoints)
                feature.Destroy()
                feature = self.shpLayer.GetNextFeature()
        elif segOption == 'earCut':
            while feature:
                label = feature.GetField(categoryName)
                labels.append(label)
                geom = feature.GetGeometryRef()  # type: ogr.Geometry
                typeName = geom.GetGeometryName()
                if typeName == "POLYGON":
                    featureWKT = geom.ExportToWkt()
                    polyList = self.geo2XY(shapleCommon.polygonStr2List(featureWKT),geomTrans,targetsr)
                    samplePoints = shapleCommon.samplePolygonByEarCut(polyList)
                    points.append(samplePoints)
                elif typeName == "POINT":
                    ptsX = geom.GetX()
                    ptsY = geom.GetY()
                    points.append(self.geo2PointXY(ptsX,ptsY,geomTrans,targetsr))
                elif typeName == "MULTIPOLYGON":
                    print("找到Multi面样本，请核查...")
                    print("已自动选择最大多边形")
                    area_polygon = []
                    for j in range(geom.GetGeometryCount()):
                        pts = geom.GetGeometryRef(j)
                        area_polygon.append(pts.GetGeometryRef(0).GetArea())
                    max_index = area_polygon.index(max(area_polygon))
                    featureWKT = geom.GetGeometryRef(max_index).ExportToWkt()
                    polyList = self.geo2XY(shapleCommon.polygonStr2List(featureWKT), geomTrans, targetsr)
                    samplePoints = shapleCommon.samplePolygonByEarCut(polyList)
                    points.append(samplePoints)
                feature.Destroy()
                feature = self.shpLayer.GetNextFeature()
        elif segOption == 'circlePart':
            while feature:
                label = feature.GetField(categoryName)
                labels.append(label)
                geom = feature.GetGeometryRef()  # type: ogr.Geometry
                typeName = geom.GetGeometryName()
                if typeName == "POLYGON":
                    featureWKT = geom.ExportToWkt()
                    polyList = self.geo2XY(shapleCommon.polygonStr2List(featureWKT),geomTrans,targetsr)
                    samplePoints = shapleCommon.samplePolygonByCirclePart(polyList)
                    points.append(samplePoints)
                elif typeName == "POINT":
                    ptsX = geom.GetX()
                    ptsY = geom.GetY()
                    points.append(self.geo2PointXY(ptsX,ptsY,geomTrans,targetsr))
                elif typeName == "MULTIPOLYGON":
                    print("找到Multi面样本，请核查...")
                    print("已自动选择最大多边形")
                    area_polygon = []
                    for j in range(geom.GetGeometryCount()):
                        pts = geom.GetGeometryRef(j)
                        area_polygon.append(pts.GetGeometryRef(0).GetArea())
                    max_index = area_polygon.index(max(area_polygon))
                    featureWKT = geom.GetGeometryRef(max_index).ExportToWkt()
                    polyList = self.geo2XY(shapleCommon.polygonStr2List(featureWKT), geomTrans, targetsr)
                    samplePoints = shapleCommon.samplePolygonByEarCut(polyList)
                    points.append(samplePoints)
                feature.Destroy()
                feature = self.shpLayer.GetNextFeature()
        elif segOption == 'needNot':
            while feature:
                label = feature.GetField(categoryName)
                labels.append(label)
                geom = feature.GetGeometryRef()  # type: ogr.Geometry
                typeName = geom.GetGeometryName()
                if typeName == "POLYGON":
                    featureWKT = geom.ExportToWkt()
                    polyList = self.geo2XY(shapleCommon.polygonStr2List(featureWKT),geomTrans,targetsr)
                    samplePoints = shapleCommon.samplePolygonByCirclePart(polyList)
                    points.append(samplePoints)
                elif typeName == "POINT":
                    ptsX = geom.GetX()
                    ptsY = geom.GetY()
                    points.append(self.geo2PointXY(ptsX,ptsY,geomTrans,targetsr))
                elif typeName == "MULTIPOLYGON":
                    print("找到Multi面样本，请核查...")
                    print("已自动选择最大多边形")
                    area_polygon = []
                    for j in range(geom.GetGeometryCount()):
                        pts = geom.GetGeometryRef(j)
                        area_polygon.append(pts.GetGeometryRef(0).GetArea())
                    max_index = area_polygon.index(max(area_polygon))
                    featureWKT = geom.GetGeometryRef(max_index).ExportToWkt()
                    polyList = self.geo2XY(shapleCommon.polygonStr2List(featureWKT), geomTrans, targetsr)
                    samplePoints = shapleCommon.samplePolygonByEarCut(polyList)
                    points.append(samplePoints)
                feature.Destroy()
                feature = self.shpLayer.GetNextFeature()
        return points,labels

    def geo2PointXY(self,ptsX,ptsY,geomTrans,targetsr):
        if self.shpSpatialRef == None:
            px, py = Geo2rowcol.geo2imagexy(geomTrans, ptsX, ptsY)
        else:
            if self.shpSpatialRef.IsProjected():
                px, py = Geo2rowcol.Project2pixel(ptsY, ptsX, self.shpSpatialRef, geomTrans)
            else:
                px, py = Geo2rowcol.latlon2pixel(ptsY, ptsX, input_raster="",
                                                 targetsr=targetsr, geom_transform=geomTrans)
        return Geo2rowcol.field3_3(int(px),int(py))

    def geo2PointXYNoAugment(self,ptsX,ptsY,geomTrans,targetsr):
        if self.shpSpatialRef == None:
            px, py = Geo2rowcol.geo2imagexy(geomTrans, ptsX, ptsY)
        else:
            if self.shpSpatialRef.IsProjected():
                px, py = Geo2rowcol.Project2pixel(ptsY, ptsX, self.shpSpatialRef, geomTrans)
            else:
                px, py = Geo2rowcol.latlon2pixel(ptsY, ptsX, input_raster="",
                                                 targetsr=targetsr, geom_transform=geomTrans)
        return [int(px),int(py)]

    def Oldgeo2XY(self,XYs,geomTrans,targetsr):

        transXY = []
        if self.shpSpatialRef == None:
            for xy in XYs:
                px, py = Geo2rowcol.geo2imagexy(geomTrans,xy[0], xy[1])
                transXY.append([px, py])
        else:
            if self.shpSpatialRef.IsProjected():
                for xy in XYs:
                    px, py = Geo2rowcol.Project2pixel(xy[1], xy[0], self.shpSpatialRef, geomTrans)
                    transXY.append([px, py])
            else:
                for xy in XYs:
                    px, py = Geo2rowcol.latlon2pixel(xy[1], xy[0], input_raster="",
                                                 targetsr=targetsr, geom_transform=geomTrans)
                    transXY.append([px, py])
        return transXY

    def geo2XY(self,XYs,geomTrans,targetsr):
        res = []
        if len(XYs) == 1:
            transXY = []
            if self.shpSpatialRef == None:
                for xy in XYs[0]:
                    px, py = Geo2rowcol.geo2imagexy(geomTrans,xy[0], xy[1])
                    transXY.append([px, py])
            else:
                if self.shpSpatialRef.IsProjected():
                    for xy in XYs[0]:
                        px, py = Geo2rowcol.Project2pixel(xy[1], xy[0], self.shpSpatialRef, geomTrans)
                        transXY.append([px, py])
                else:
                    for xy in XYs[0]:
                        px, py = Geo2rowcol.latlon2pixel(xy[1], xy[0], input_raster="",
                                                     targetsr=targetsr, geom_transform=geomTrans)
                        transXY.append([px, py])
            res.append(transXY)
            return res
        else:
            for XYstemp in XYs:
                transXY = []
                if self.shpSpatialRef == None:
                    for xy in XYstemp:
                        px, py = Geo2rowcol.geo2imagexy(geomTrans, xy[0], xy[1])
                        transXY.append([px, py])
                else:
                    if self.shpSpatialRef.IsProjected():
                        for xy in XYstemp:
                            px, py = Geo2rowcol.Project2pixel(xy[1], xy[0], self.shpSpatialRef, geomTrans)
                            transXY.append([px, py])
                    else:
                        for xy in XYstemp:
                            px, py = Geo2rowcol.latlon2pixel(xy[1], xy[0], input_raster="",
                                                             targetsr=targetsr, geom_transform=geomTrans)
                            transXY.append([px, py])
                res.append(transXY)
            return res



    def createNewField(self,fieldName):
        fieldList = self.getField2List()
        if fieldName in fieldList:
            print("该字段已存在，即将删除原字段")
            self.shpLayer.DeleteField(self.shpLayer.FindFieldIndex(fieldName,1))
        else:
            fieldDefn = ogr.FieldDefn(fieldName,ogr.OFTInteger)
            self.shpLayer.CreateField(fieldDefn)


    def showEarCut(self,tifPath):
        tifDs = gdal.Open(tifPath)
        geomTrans = tifDs.GetGeoTransform()
        targetsr = osr.SpatialReference()
        targetsr.ImportFromWkt(tifDs.GetProjectionRef())
        feature = self.shpLayer.GetNextFeature()  # type: ogr.Feature
        geom = feature.GetGeometryRef()  # type: ogr.Geometry
        typeName = geom.GetGeometryName()
        if typeName == "POLYGON":
            featureWKT = geom.ExportToWkt()
            print(featureWKT)
            polyList = self.geo2XY(shapleCommon.polygonStr2List(featureWKT), geomTrans, targetsr)
            samplePoints = shapleCommon.showPolygonByEarCut(polyList)

        else:
            print("您的不是面矢量")





if __name__ == '__main__':
    shpPath = r"D:\YoyiImage\kongDongTest.shp"
    tifPath = r"D:\YoyiImage\苏南\sunan_202107_10.tif"
    shpF = ShapeFile(shpPath)
    tifDs = gdal.Open(tifPath)
    geomTrans = tifDs.GetGeoTransform()
    targetsr = osr.SpatialReference()
    targetsr.ImportFromWkt(tifDs.GetProjectionRef())
    feature = shpF.shpLayer.GetNextFeature()
    geom = feature.GetGeometryRef()
    print(geom)
    featureWKT = geom.ExportToWkt()
    print(featureWKT)
    a = shapleCommon.polygonStr2List(featureWKT)
    print(a)
    polyList = shpF.geo2XY(shapleCommon.polygonStr2List(featureWKT), geomTrans, targetsr)
    print(polyList)
    #shpF.getShpPolygonSamplePoint2PointsLabel(tifDs,"Scale","earCut",5)
