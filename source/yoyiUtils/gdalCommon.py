#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   gdalCommon.py    
@Contact :   zhijuepeng@foxmail.com
@License :   (C)Copyright 2017-9999,CGWX

@Modify Time      @Author    @Version    @Desciption
------------      -------    --------    -----------
15/7/2021 下午2:17   Yoyi      1.0         None
"""

import numpy as np
import os
import os.path as osp
import math
import glob
from source.classificationPytorch.tools import Geo2rowcol
from osgeo import gdal,osr,ogr,gdalconst
import ctypes
from skimage import io
import time
from tqdm import tqdm
from source.classificationPytorch.yoyiUtils.preProcessCommon import copyShpFilesAndRename
# 16位遥感影像 转 8位遥感影像
def uint16to8(bands, lower_percent=0.001, higher_percent=99.999):
    out = np.zeros_like(bands,dtype = np.uint8)
    n = bands.shape[0]
    for i in range(n):
        a = 0 # np.min(band)
        b = 255 # np.max(band)
        c = np.percentile(bands[i, :, :], lower_percent)
        d = np.percentile(bands[i, :, :], higher_percent)
        t = a + (bands[i, :, :] - c) * (b - a) / (d - c)
        t[t<a] = a
        t[t>b] = b
        out[i, :, :] = t
    return out

def getGdalConst():
    print(gdalconst.GDT_Unknown)
    print(gdalconst.GDT_Byte)
    print(gdalconst.GDT_UInt16)
    print(gdalconst.GDT_Int16)
    print(gdalconst.GDT_UInt32)
    print(gdalconst.GDT_Int32)
    print(gdalconst.GDT_Float32)
    print(gdalconst.GDT_Float64)
    print(gdalconst.GDT_CInt16)
    print(gdalconst.GDT_CInt32)
    print(gdalconst.GDT_CFloat32)
    print(gdalconst.GDT_CFloat64)


def batch16to8(tifFolder,resDir):
    for raster in glob.glob(os.path.join(tifFolder, '*.tif')):
        tifDs = gdal.Open(raster) #type: gdal.Dataset
        tifGeoTrans = tifDs.GetGeoTransform()
        tifProject = tifDs.GetProjection()
        tifNp = tifDs.ReadAsArray()
        cols = tifDs.RasterXSize
        rows = tifDs.RasterYSize
        bands = tifDs.RasterCount

        outNp = uint16to8(tifNp)
        baseName = os.path.basename(raster)
        outFileName = os.path.join(resDir,baseName)

        tempDriver = gdal.GetDriverByName("GTiff")  # type: gdal.Driver
        resDS= tempDriver.Create(outFileName,cols,rows,bands,gdalconst.GDT_Byte)

        resDS.SetGeoTransform(tifGeoTrans)
        resDS.SetProjection(tifProject)
        for b in range(bands):
            resDS.GetRasterBand(b + 1).WriteArray(outNp[b, :, :])
        resDS.FlushCache()

# 选定裁剪次数，动态裁剪遥感影像
def segTifOld(tifPath,resultDir,segNum=6):
    tifDs = gdal.Open(tifPath) #type: gdal.Dataset
    tifGeoTrans = tifDs.GetGeoTransform()
    tifProject = tifDs.GetProjection()
    tifNp = tifDs.ReadAsArray()
    bandTif, heiTif, weiTif = tifNp.shape
    dataType = tifDs.GetRasterBand(1).DataType
    #print(bandTif,heiTif,weiTif)

    xsize = math.ceil(weiTif / segNum)
    ysize = math.ceil(heiTif / segNum)
    XSegNum = int(weiTif / xsize) if weiTif%xsize == 0 else int(weiTif / xsize)+1
    YSegNum = int(heiTif / ysize) if heiTif%ysize == 0 else int(heiTif / ysize)+1

    num = 0
    for y in range(YSegNum):
        for x in range(XSegNum):
            tifTempPath = osp.join(resultDir,f"{x+1}_{y+1}_seg.tif")
            xOff = x*xsize
            yOff = y*ysize
            xSizeTemp = min(weiTif-xOff,xsize)
            ySizeTemp = min(heiTif-yOff,ysize)

            arrayTemp = tifDs.ReadAsArray(xOff,yOff,xSizeTemp,ySizeTemp)
            tempDriver = gdal.GetDriverByName("GTiff") #type: gdal.Driver

            dsTemp = tempDriver.Create(tifTempPath,xSizeTemp,ySizeTemp,bandTif,dataType) #type: gdal.Dataset

            top_leftX = tifGeoTrans[0] + xOff*tifGeoTrans[1]
            top_leftY = tifGeoTrans[3] + yOff*tifGeoTrans[5]
            transTemp = (top_leftX,tifGeoTrans[1],tifGeoTrans[2],top_leftY,tifGeoTrans[4],tifGeoTrans[5])
            dsTemp.SetGeoTransform(transTemp)
            dsTemp.SetProjection(tifProject)
            for b in range(bandTif):
                dsTemp.GetRasterBand(b + 1).WriteArray(arrayTemp[b, :, :])
            dsTemp.FlushCache()
            del dsTemp
            num+=1
    print(f"分割完成，结果文件夹：{resultDir} ... 总分割块数量{num}")
    del tifDs

# 选定裁剪次数，动态裁剪遥感影像
def segTif(tifPath,resultDir,segNum=6):
    tifDs = gdal.Open(tifPath) #type: gdal.Dataset
    tifGeoTrans = tifDs.GetGeoTransform()
    tifProject = tifDs.GetProjection()
    tifNp = tifDs.ReadAsArray()
    bandTif, heiTif, weiTif = tifNp.shape
    dataType = tifDs.GetRasterBand(1).DataType
    xsize = math.ceil(weiTif / segNum)
    ysize = math.ceil(heiTif / segNum)
    XSegNum = int(weiTif / xsize) if weiTif%xsize == 0 else int(weiTif / xsize)+1
    YSegNum = int(heiTif / ysize) if heiTif%ysize == 0 else int(heiTif / ysize)+1
    num = 0
    print(f"开始进行动态裁剪{tifPath}")
    for y in range(YSegNum):
        for x in range(XSegNum):
            xOff = x*xsize
            yOff = y*ysize
            xSizeTemp = min(weiTif-xOff,xsize)
            ySizeTemp = min(heiTif-yOff,ysize)
            tifTempPath = osp.join(resultDir, f"{bandTif}_{weiTif}_{heiTif}_{dataType}_{xOff}_{xSizeTemp}_{yOff}_{ySizeTemp}_.tif")
            arrayTemp = tifDs.ReadAsArray(xOff,yOff,xSizeTemp,ySizeTemp)
            tempDriver = gdal.GetDriverByName("GTiff") #type: gdal.Driver
            dsTemp = tempDriver.Create(tifTempPath,xSizeTemp,ySizeTemp,bandTif,dataType) #type: gdal.Dataset
            top_leftX = tifGeoTrans[0] + xOff*tifGeoTrans[1]
            top_leftY = tifGeoTrans[3] + yOff*tifGeoTrans[5]
            transTemp = (top_leftX,tifGeoTrans[1],tifGeoTrans[2],top_leftY,tifGeoTrans[4],tifGeoTrans[5])
            dsTemp.SetGeoTransform(transTemp)
            dsTemp.SetProjection(tifProject)
            for b in range(bandTif):
                dsTemp.GetRasterBand(b + 1).WriteArray(arrayTemp[b, :, :])
            dsTemp.FlushCache()
            del dsTemp
            num+=1
    print(f"分割完成，结果文件夹：{resultDir} ... 总分割块数量{num}")
    del tifDs
    return tifGeoTrans,tifProject


# 选定裁剪的大致尺寸,在不偏离这个大致尺寸的情况下进行动态裁剪遥感影像 (注意: 最后裁剪出的影像不一定是选定的尺寸,尺寸参数的意义仅仅是为裁剪次数提供一个大致的参考)
def segTifByCropSize(tifPath,resultDir,cropSize=1024):
    tifDs = gdal.Open(tifPath) #type: gdal.Dataset
    tifGeoTrans = tifDs.GetGeoTransform()
    tifProject = tifDs.GetProjection()
    tifNp = tifDs.ReadAsArray()
    bandTif, heiTif, weiTif = tifNp.shape
    dataType = tifDs.GetRasterBand(1).DataType
    assert max(heiTif,weiTif) > cropSize,"cropSize is too large or tif img size is too small!!!"
    segNum = max(heiTif,weiTif)//cropSize if max(heiTif,weiTif)//cropSize > 0 else 2
    xsize = math.ceil(weiTif / segNum)
    ysize = math.ceil(heiTif / segNum)
    XSegNum = int(weiTif / xsize) if weiTif%xsize == 0 else int(weiTif / xsize)+1
    YSegNum = int(heiTif / ysize) if heiTif%ysize == 0 else int(heiTif / ysize)+1
    num = 0
    print(f"开始进行动态裁剪{tifPath}")
    for y in range(YSegNum):
        for x in range(XSegNum):
            xOff = x*xsize
            yOff = y*ysize
            xSizeTemp = min(weiTif-xOff,xsize)
            ySizeTemp = min(heiTif-yOff,ysize)
            tifTempPath = osp.join(resultDir, f"{bandTif}_{weiTif}_{heiTif}_{dataType}_{xOff}_{xSizeTemp}_{yOff}_{ySizeTemp}_.tif")
            arrayTemp = tifDs.ReadAsArray(xOff,yOff,xSizeTemp,ySizeTemp)
            tempDriver = gdal.GetDriverByName("GTiff") #type: gdal.Driver
            dsTemp = tempDriver.Create(tifTempPath,xSizeTemp,ySizeTemp,bandTif,dataType) #type: gdal.Dataset
            top_leftX = tifGeoTrans[0] + xOff*tifGeoTrans[1]
            top_leftY = tifGeoTrans[3] + yOff*tifGeoTrans[5]
            transTemp = (top_leftX,tifGeoTrans[1],tifGeoTrans[2],top_leftY,tifGeoTrans[4],tifGeoTrans[5])
            dsTemp.SetGeoTransform(transTemp)
            dsTemp.SetProjection(tifProject)
            for b in range(bandTif):
                dsTemp.GetRasterBand(b + 1).WriteArray(arrayTemp[b, :, :])
            dsTemp.FlushCache()
            del dsTemp
            num+=1
    print(f"分割完成，结果文件夹：{resultDir} ... 总分割块数量{num}")
    del tifDs
    return tifGeoTrans,tifProject

def combineTif(tifDir,resultTif):
    tifList = glob.glob(osp.join(tifDir,"*.tif"))
    infoList = osp.basename(tifList[0]).split("_")
    BAND = int(infoList[0])
    XSize = int(infoList[1])
    YSize = int(infoList[2])
    dataType = int(infoList[3])
    tifDriver = gdal.GetDriverByName("GTiff") #type: gdal.Driver
    tifDs = tifDriver.Create(resultTif,XSize,YSize,BAND,dataType) #type: gdal.Dataset
    tempTif = gdal.Open(tifList[0]) #type: gdal.Dataset
    tempNP = tempTif.ReadAsArray()
    tifDataType = tempNP.dtype
    tifGeoTrans = tempTif.GetGeoTransform()
    tifProject = tempTif.GetProjection()
    del tempNP
    del tempTif
    tifNp = np.zeros((BAND,YSize,XSize),dtype=tifDataType)
    for tifTemp in tqdm(tifList):
        infoList = osp.basename(tifTemp).split("_")
        xOff,xSizeT,yOff,ySizeT = int(infoList[4]),int(infoList[5]),int(infoList[6]),int(infoList[7])
        tempTif = gdal.Open(tifTemp)  # type: gdal.Dataset
        tempNP = tempTif.ReadAsArray()
        #print(BAND,ySizeT,xSizeT)
        #print(tempNP.shape)
        assert tempNP.shape[0] == BAND
        assert tempNP.shape[1] == ySizeT
        assert tempNP.shape[2] == xSizeT
        tifNp[:,yOff:yOff+ySizeT,xOff:xOff+xSizeT] = tempNP
        del tempTif
        del tempNP
    tifDs.SetGeoTransform(tifGeoTrans)
    tifDs.SetProjection(tifProject)
    for b in range(BAND):
        tifDs.GetRasterBand(b + 1).WriteArray(tifNp[b, :, :])
    tifDs.FlushCache()
    del tifDs
    print("已完成栅格影像合并")

def combineSegTif(tifDir,resultTif,geoT,geoP):
    tifList = glob.glob(osp.join(tifDir,"*.tif"))
    infoList = osp.basename(tifList[0]).split("_")
    XSize = int(infoList[1])
    YSize = int(infoList[2])
    tifDriver = gdal.GetDriverByName("GTiff") #type: gdal.Driver
    tifDs = tifDriver.Create(resultTif,XSize,YSize,1,5) #type: gdal.Dataset
    tempTif = gdal.Open(tifList[0]) #type: gdal.Dataset
    tempNP = tempTif.ReadAsArray()
    tifDataType = tempNP.dtype
    tifGeoTrans = tempTif.GetGeoTransform()
    tifProject = tempTif.GetProjection()
    del tempNP
    del tempTif
    tifNp = np.zeros((1,YSize,XSize),dtype=tifDataType)
    for tifTemp in tqdm(tifList):
        infoList = osp.basename(tifTemp).split("_")
        xOff,xSizeT,yOff,ySizeT = int(infoList[4]),int(infoList[5]),int(infoList[6]),int(infoList[7])
        tempTif = gdal.Open(tifTemp)  # type: gdal.Dataset
        tempNP = tempTif.ReadAsArray()
        #print(ySizeT,xSizeT)
        #print(tempNP.shape)
        assert tempNP.shape[0] == ySizeT
        assert tempNP.shape[1] == xSizeT
        tifNp[:,yOff:yOff+ySizeT,xOff:xOff+xSizeT] = tempNP
        del tempTif
        del tempNP
    tifDs.SetGeoTransform(geoT)
    tifDs.SetProjection(geoP)
    tifDs.GetRasterBand(1).WriteArray(tifNp[0, :, :])
    tifDs.FlushCache()
    del tifDs
    del tifNp
    print("已完成栅格影像合并")

def mergeShps(shpDir,resShp,newName):
    shpList = glob.glob(osp.join(shpDir, "*.shp"))
    shpDs = ogr.Open(shpList[0],1) #type: ogr.DataSource
    shpLayer = shpDs.GetLayer(0) #type: ogr.Layer
    for shp in shpList[1:]:
        shpTempDs = ogr.Open(shp,1) #type: ogr.DataSource
        shpTempLayer = shpTempDs.GetLayer(0) #type: ogr.Layer
        for feat in shpTempLayer:
            shpLayer.CreateFeature(feat)
        del shpTempDs
    shpDs.FlushCache()
    del shpDs
    return copyShpFilesAndRename(shpList[0],resShp,newName)

def RasterToPoly(rasterName, shpName):
    """
        栅格转矢量
        :param rasterName: 输入分类后的栅格名称
        :param shpName: 输出矢量名称
        :return:
   """
    inraster = gdal.Open(rasterName)  # 读取路径中的栅格数据
    inband = inraster.GetRasterBand(1)  # 这个波段就是最后想要转为矢量的波段，如果是单波段数据的话那就都是1
    prj = osr.SpatialReference()
    prj.ImportFromWkt(inraster.GetProjection())  # 读取栅格数据的投影信息，用来为后面生成的矢量做准备
    outshp = shpName
    drv = ogr.GetDriverByName("ESRI Shapefile")
    if os.path.exists(outshp):  # 若文件已经存在，则删除它继续重新做一遍
        drv.DeleteDataSource(outshp)
    Polygon = drv.CreateDataSource(outshp)  # 创建一个目标文件
    Poly_layer = Polygon.CreateLayer(shpName[:-4], srs=prj, geom_type=ogr.wkbMultiPolygon)  # 对shp文件创建一个图层，定义为多个面类
    newField = ogr.FieldDefn('Value', ogr.OFTReal)  # 给目标shp文件添加一个字段，用来存储原始栅格的pixel value
    Poly_layer.CreateField(newField)
    gdal.FPolygonize(inband, None, Poly_layer, 0)  # 核心函数，执行的就是栅格转矢量操作
    Polygon.SyncToDisk()
    Polygon = None
    deleteBackground(shpName, 0)  # 删除背景

def deleteBackground(shpName, backGroundValue):
    """
    删除背景,一般背景的像素值为0
    """
    driver = ogr.GetDriverByName('ESRI Shapefile')
    pFeatureDataset = driver.Open(shpName, 1)
    pFeaturelayer = pFeatureDataset.GetLayer(0)
    strValue = backGroundValue
    strFilter = "Value = '" + str(strValue) + "'"
    pFeaturelayer.SetAttributeFilter(strFilter)
    pFeatureDef = pFeaturelayer.GetLayerDefn()
    pLayerName = pFeaturelayer.GetName()
    pFieldName = "Value"
    pFieldIndex = pFeatureDef.GetFieldIndex(pFieldName)
    for pFeature in pFeaturelayer:
        pFeatureFID = pFeature.GetFID()
        pFeaturelayer.DeleteFeature(int(pFeatureFID))
    strSQL = "REPACK " + str(pFeaturelayer.GetName())
    pFeatureDataset.ExecuteSQL(strSQL, None, "")
    pFeatureLayer = None
    pFeatureDataset = None

# 批量栅格转矢量
def tif2shp(tifFolder):
    for raster in glob.glob(os.path.join(tifFolder, '*.tif')):
        shpName = raster.split(".")[0] + ".shp"
        RasterToPoly(raster,shpName)
# 批量栅格转矢量
def tif2shpByProcess(tifFolder,process):
    tifList = glob.glob(os.path.join(tifFolder, '*.tif'))
    lenBi = len(tifList)//2
    if process == "A":
        for i in range(0,lenBi):
            raster = tifList[i]
            shpName = raster.split(".")[0] + ".shp"
            RasterToPoly(raster, shpName)
    if process == "B":
        for i in range(lenBi,len(tifList)):
            raster = tifList[i]
            shpName = raster.split(".")[0] + ".shp"
            RasterToPoly(raster, shpName)


# 单个栅格转矢量
def atif2ashp(tifImg,outputShp):
    inraster = gdal.Open(tifImg) #type: gdal.Dataset
    inband = inraster.GetRasterBand(1)
    prj = osr.SpatialReference()
    prj.ImportFromWkt(inraster.GetProjection())

    drv = ogr.GetDriverByName("ESRI Shapefile") #type: ogr.Driver
    if os.path.exists(outputShp):
        drv.DeleteDataSource(outputShp)
    Polygon = drv.CreateDataSource(outputShp) #type: ogr.DataSource
    polyLayer = Polygon.CreateLayer(tifImg[:-4],srs = prj,geom_type = ogr.wkbMultiPolygon)
    newField = ogr.FieldDefn('value',ogr.OFTReal)
    polyLayer.CreateField(newField)

    gdal.FPolygonize(inband,None,polyLayer,0)
    Polygon.SyncToDisk()
    Polygon = None

    print(f"完成{outputShp}...")

# 将矢量文件转为和目标栅格数据空间位置一致且像元大小一致的数据
def shp2tifGiveMeTifPath(shpPath,tifPath,shpAttr,outputPath):
    tifDs = gdal.Open(tifPath,gdalconst.GA_ReadOnly) # type: gdal.Dataset
    shpDs = ogr.Open(shpPath,0) # type: ogr.DataSource
    geoTrans = tifDs.GetGeoTransform()
    cols = tifDs.RasterXSize
    rows = tifDs.RasterYSize

    x_min = geoTrans[0]
    y_min = geoTrans[3]
    pixelWidth = geoTrans[1]

    shpLayer = shpDs.GetLayer(0)
    #outputFile = osp.join(outputPath,osp.basename(shpPath).split(".")[0]+".tif")
    outputDri = gdal.GetDriverByName('GTiff') #type: gdal.Driver
    outputDs = outputDri.Create(outputPath,xsize=cols,ysize=rows,bands=1,eType=gdal.GDT_Byte) # type: gdal.Dataset
    outputDs.SetGeoTransform(geoTrans)
    outputDs.SetProjection(tifDs.GetProjection())

    outBand = outputDs.GetRasterBand(1) #type: gdal.Band
    outBand.SetNoDataValue(0)
    outBand.FlushCache()
    gdal.RasterizeLayer(outputDs,[1],shpLayer,options=[f"ATTRIBUTE={shpAttr}"])

    del tifDs
    del shpDs
    del outputDs

# 将矢量文件转为和目标栅格数据空间位置一致且像元大小一致的数据
def shp2tif(shpPath,tifPath,shpAttr,outputPath):
    tifDs = gdal.Open(tifPath,gdalconst.GA_ReadOnly) # type: gdal.Dataset
    shpDs = ogr.Open(shpPath,0) # type: ogr.DataSource
    geoTrans = tifDs.GetGeoTransform()
    cols = tifDs.RasterXSize
    rows = tifDs.RasterYSize

    x_min = geoTrans[0]
    y_min = geoTrans[3]
    pixelWidth = geoTrans[1]

    shpLayer = shpDs.GetLayer(0)
    outputFile = osp.join(outputPath,osp.basename(shpPath).split(".")[0]+".tif")
    outputDri = gdal.GetDriverByName('GTiff') #type: gdal.Driver
    outputDs = outputDri.Create(outputFile,xsize=cols,ysize=rows,bands=1,eType=gdal.GDT_Byte) # type: gdal.Dataset
    outputDs.SetGeoTransform(geoTrans)
    outputDs.SetProjection(tifDs.GetProjection())

    outBand = outputDs.GetRasterBand(1) #type: gdal.Band
    outBand.SetNoDataValue(0)
    outBand.FlushCache()
    gdal.RasterizeLayer(outputDs,[1],shpLayer,options=[f"ATTRIBUTE={shpAttr}"])

    del tifDs
    del shpDs
    del outputDs


# 将栅格最小尺寸定位到固定尺寸
def makeTifMin2bigSize(tifPath,bigSize):
    tifDs = gdal.Open(tifPath) # type: gdal.Dataset
    tifNp = tifDs.ReadAsArray()
    dataType = tifDs.GetRasterBand(1).DataType
    c,h,w = tifNp.shape
    H,W = h,w
    if h < bigSize:
        H = bigSize
    if w < bigSize:
        W = bigSize
    newPath = tifPath[:-4] + "_xiufu.tif"
    tempDriver = gdal.GetDriverByName("GTiff")  # type: gdal.Driver
    dsTemp = tempDriver.Create(newPath, W, H, c, dataType)  # type: gdal.Dataset
    tifGeoTrans = tifDs.GetGeoTransform()
    tifProject = tifDs.GetProjection()
    dsTemp.SetGeoTransform(tifGeoTrans)
    dsTemp.SetProjection(tifProject)
    tempNp = np.zeros((c,H, W))
    tempNp[:,:h,:w] = tifNp[:, :, :]
    #tempNp = tempNp.transpose((0,2,1))
    for b in range(c):
        dsTemp.GetRasterBand(b + 1).WriteArray(tempNp[b,:,:])
    dsTemp.FlushCache()
    del dsTemp
    print(f"修复结果位于：{newPath}")

import ctypes
import os
import time
import sys

class MethodProducedRemove():
    def __init__(self, RSR_filename,area_delete,RSR_result_file):
        self.RSR_filename=RSR_filename
        self.area_delete=area_delete
        self.RSR_result_file=RSR_result_file

    def run(self, WORKROOT):  # 自动生产
        if sys.platform == 'linux':
            MethodRSR = ctypes.cdll.LoadLibrary('libs/removeSmallRegion20200910/libremoveSmallRegion.so')
            MethodRSR.removeSmallRegion(self.RSR_filename.encode('gb2312'), self.area_delete,
                                        self.RSR_result_file.encode('gb2312'))
        else:
            os.chdir("libs/")
            os.environ['PATH']=os.getcwd()
            MethodRSR = ctypes.cdll.LoadLibrary('removeSmallRegion.dll')
            #MethodRSR.removeSmallRegion(self.RSR_filename,self.area_delete,self.RSR_result_file)
            MethodRSR.removeSmallRegionSingle(self.RSR_filename,self.area_delete,self.RSR_result_file)
            os.chdir(WORKROOT)

WORKROOT = os.getcwd()
# 批量去碎斑
def removeDir(tifDir,area=100):
    for raster in glob.glob(os.path.join(tifDir, '*.tif')):
        resultTemp = raster[:-4] + "_remove.tif"
        remove = MethodProducedRemove(raster.encode('gbk'), area,
                                       resultTemp.encode('gbk'))  # windows 10

        remove.run(WORKROOT)


# 将栅格中全部为 0 的部分全部变成 1 方便进行计算
def tifadd1():
    tifPath = r"E:\分类文件\变电站\20210506_GF02B.tif"
    resPath = r"E:\分类文件\变电站\20210506_GF02B_xiufu.tif"
    tifDs = gdal.Open(tifPath)
    tifNp = tifDs.ReadAsArray()
    dataType = tifDs.GetRasterBand(1).DataType
    c, h, w = tifNp.shape

    tempDriver = gdal.GetDriverByName("GTiff")  # type: gdal.Driver
    dsTemp = tempDriver.Create(resPath, w, h, c, dataType)  # type: gdal.Dataset
    tifGeoTrans = tifDs.GetGeoTransform()
    tifProject = tifDs.GetProjection()
    dsTemp.SetGeoTransform(tifGeoTrans)
    dsTemp.SetProjection(tifProject)
    tempNp = tifNp
    temp1 = tifNp[0,:,:]
    temp2 = tifNp[1, :, :]
    temp3 = tifNp[2, :, :]
    temp1 = np.where(temp1==0,1,temp1)
    temp2 = np.where(temp2 == 0, 1,temp2)
    temp3 = np.where(temp3 == 0, 1,temp3)
    # tempNp = tempNp.transpose((0,2,1))

    dsTemp.GetRasterBand(1).WriteArray(temp1)
    dsTemp.GetRasterBand(2).WriteArray(temp2)
    dsTemp.GetRasterBand(3).WriteArray(temp3)
    dsTemp.FlushCache()
    del dsTemp

if __name__ == '__main__':
    # shpPath = r"X:\数据三室个人存储\18_PZJ\test2\result4\pieSeg\pieSeg_final.shp"
    # tifPath = r"X:\数据三室个人存储\18_PZJ\test2\img\test.tif"
    # outputPath = r"X:\数据三室个人存储\18_PZJ\test2\result4\pieSeg\pieSeg_final.tif"
    # shp2tif(shpPath,tifPath,"Classify",outputPath)
    #shpWgs2Utm()
    tifadd1()