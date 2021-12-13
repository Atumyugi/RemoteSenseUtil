#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   preProcessCommon.py    
@Contact :   zhijuepeng@foxmail.com
@License :   (C)Copyright 2017-9999,CGWX

@Modify Time      @Author    @Version    @Desciption
------------      -------    --------    -----------
26/7/2021 下午3:52   Yoyi      1.0         None
"""

import os
import os.path as osp
import shutil
import glob
from source.yoyiUtils.shpCommon import ShapeFile


# 也可以递归删除文件
def delAll(path):
    if os.path.isdir(path):
        files = os.listdir(path)  # ['a.doc', 'b.xls', 'c.ppt']
        # 遍历并删除文件
        for file in files:
            p = os.path.join(path, file)
            if os.path.isdir(p):
                # 递归
                delAll(p)
            else:
                os.remove(p)
        # 删除文件夹
        os.rmdir(path)
    else:
        os.remove(path)

def get_all_csv(path, suffix=''):
    itemPath = list(os.walk(path))
    all_csv = []
    for child_path in itemPath:
        if child_path[2]:
            for file in child_path[2]:
                if suffix in file:
                    all_csv.append(child_path[0] + '/' + file)
    return all_csv

def copyFile(srcFile,dstPath,addName='_classify'):
    if not osp.isfile(srcFile):
        print(f"{srcFile} not exist...")
        exit(1)
    else:
        fpath,fname = osp.split(srcFile)
        prefix, postfix = fname.split(".")
        if not osp.exists(dstPath):
            os.makedirs(dstPath)
        res = dstPath+"\\"+prefix+addName+'.'+postfix
        shutil.copy(srcFile,res)
        return res

def copyShpFiles(srcFile,dstPath):
    if not osp.isfile(srcFile):
        print(f"{srcFile} not exist...")
        exit(1)
    else:
        fpath,fname = osp.split(srcFile)
        prefix, postfix = fname.split(".")
        finalDir = osp.join(dstPath,prefix)
        if not osp.exists(finalDir):
            os.makedirs(finalDir)
        for shpTemp in glob.glob(osp.join(fpath,f"{prefix}.*")):
            if shpTemp.endswith("xml") or shpTemp.endswith("lock"):
                continue
            preT,postT = shpTemp.split(".")
            copyTemp = finalDir+'\\'+prefix+'.'+postT
            if osp.isfile(copyTemp):
                print(f"{copyTemp} 已经存在，跳过复制...")
                continue
            tempFile = fpath+'\\'+prefix+'.'+postT
            shutil.copy(tempFile,copyTemp)
    #print(dstPath+'\\'+prefix+addName+'.shp')
    return finalDir+'\\'+prefix+'.shp'

def copyShpFilesAndRename(srcFile,dstPath,newName):
    if not osp.isfile(srcFile):
        print(f"{srcFile} not exist...")
        exit(1)
    else:
        fpath,fname = osp.split(srcFile)
        prefix, postfix = fname.split(".")
        for shpTemp in glob.glob(osp.join(fpath,f"{prefix}.*")):
            if shpTemp.endswith("xml") or shpTemp.endswith("lock") or shpTemp.endswith("tif"):
                continue
            preT,postT = shpTemp.split(".")
            copyTemp = dstPath+'\\'+newName+'.'+postT
            if osp.isfile(copyTemp):
                print(f"{copyTemp} 已经存在，跳过复制...")
                continue
            tempFile = fpath+'\\'+prefix+'.'+postT
            shutil.copy(tempFile,copyTemp)
    #print(dstPath+'\\'+prefix+addName+'.shp')
    return dstPath+'\\'+newName+'.shp'

def copyShpDontCopyTif(sourceDir,targetDir):
    for file in os.listdir(sourceDir):
        sourceFile = osp.join(sourceDir,file)
        if osp.isfile(sourceFile) and not sourceFile.endswith(".tif"):
            shutil.copy(sourceFile,targetDir)


# 根据矢量文件生成palette配置文件
def createPaletteByShp(shpPath,palettePath,classField):
    shpFile = ShapeFile(shpPath)
    cates= shpFile.getCategoriesByField2List(classField)
    if len(cates) > 30:
        print("您的种类太多，抱歉不能生成！！！")
        exit(1)
    SpList = [50,70,90,111,113,130,150,170,190,230,250,253,254,51,52,53,54,55,56,57,58,59,61,62,63,64,65,66,67,68,69,71,72,73,74,75,76,77,78,79,81,82,83,84,85,86,87,88]
    with open(palettePath,"w") as file:
        file.write("{ \n")
        i = 0
        if type(cates[0]) is not str:
            for cate in cates[:-1]:
                file.write(f"\t\"{SpList[i]}\":{cate},\n")
                i += 1
            file.write(f"\t\"{SpList[i]}\":{cates[-1]}\n")
        else:
            for cate in cates[:-1]:
                file.write(f"\t\"{SpList[i]}\":\"{cate}\",\n")
                i += 1
            file.write(f"\t\"{SpList[i]}\":\"{cates[-1]}\"\n")
        file.write("}")
        file.flush()

def createPaletteByDir(shpPath,classField):
    palettePath = shpPath[:-4] + "_Palette.json"
    createPaletteByShp(shpPath,palettePath,classField)
    return palettePath



def removeTempShp(name,dir):
    for file in glob.glob(os.path.join(dir, f'{name}.*'), recursive=True):
        os.remove(file)

if __name__ == '__main__':
    shpPath = r"X:\testV1_2\sample\testClass.shp"
    palettePath = r"X:\testV1_2\sample\palette.json"
    createPaletteByShp(shpPath,palettePath,"Id")
