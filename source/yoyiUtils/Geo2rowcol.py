import numpy as np
from matplotlib.path import Path
from osgeo import gdal, osr,ogr

def geo2imagexy(dataset, x, y):
    '''
    根据GDAL的六 参数模型将给定的投影或地理坐标转为影像图上坐标（行列号）
    :param dataset: GDAL地理数据
    :param x: 投影或地理坐标x
    :param y: 投影或地理坐标y
    :return: 影坐标或地理坐标(x, y)对应的影像图上行列号(row, col)
    '''
    trans = dataset.GetGeoTransform()
    a = np.array([[trans[1], trans[2]], [trans[4], trans[5]]])
    b = np.array([x - trans[0], y - trans[3]])
    return np.linalg.solve(a, b)  # 使用numpy的linalg.solve进行二元一次方程的求解

def latlon2pixel(lat, lon, input_raster='', targetsr='', geom_transform=''):
    # type: (object, object, object, object, object) -> object

    sourcesr = osr.SpatialReference()
    #4326 就是 WGS84的代码
    sourcesr.ImportFromEPSG(4326)

    geom = ogr.Geometry(ogr.wkbPoint)
    geom.AddPoint(lon, lat)

    if targetsr == '':
        src_raster = gdal.Open(input_raster)
        targetsr = osr.SpatialReference()
        targetsr.ImportFromWkt(src_raster.GetProjectionRef())
    coord_trans = osr.CoordinateTransformation(sourcesr, targetsr)
    if geom_transform == '':
        src_raster = gdal.Open(input_raster)
        transform = src_raster.GetGeoTransform()
    else:
        transform = geom_transform

    x_origin = transform[0]
    # print(x_origin)
    y_origin = transform[3]
    # print(y_origin)
    pixel_width = transform[1]
    # print(pixel_width)
    pixel_height = transform[5]
    # print(pixel_height)
    geom.Transform(coord_trans)
    # print(geom.GetPoint())
    x_pix = (geom.GetPoint()[0] - x_origin) / pixel_width
    y_pix = (geom.GetPoint()[1] - y_origin) / pixel_height

    return (x_pix, y_pix)

def Judge_inside(numpys):
    inside_points=[]
    x_min=np.min(numpys[:,0])
    x_max=np.max(numpys[:,0])
    y_min = np.min(numpys[:, 1])
    y_max = np.max(numpys[:, 1])
    p=Path(numpys)
    for x in range(x_min,x_max+1):
        for y in range(y_min,y_max+1):
            if p.contains_points([(x,y)]):
                inside_points.append([x,y])
    return inside_points

def List2Numpy(list):
    num=len(list)
    array=np.zeros((int(num/2),2),dtype=np.double)
    for i in range (int(num/2)):
        array[i,0]=list[i*2]
        array[i,1]=list[i*2+1]
    return array

def Project2pixel(Y, X, targetsr, geom_transform):
    sourcesr = osr.SpatialReference()
    sourcesr.ImportFromEPSG(4326)
    #ct = osr.CoordinateTransformation(targetsr, sourcesr)
    #coords = ct.TransformPoint(X, Y)
    x_origin = geom_transform[0]
    # print(x_origin)
    y_origin = geom_transform[3]
    # print(y_origin)
    pixel_width = geom_transform[1]
    # print(pixel_width)
    pixel_height = geom_transform[5]
    # print(pixel_height)
    # print(geom.GetPoint())
    x_pix = (X - x_origin) / pixel_width#coords[0]
    y_pix = (Y - y_origin) / pixel_height#coords[1]#修2019.04.16
    return (x_pix, y_pix)

def field3_3(row,col):
    """Returns
        返回当前点坐标为中心的3邻域范围的坐标集合
    """
    content = []
    for i in range(row-1,row+2):
        for j in range(col-1,col+2):
            content.append([i,j])
    return content

if __name__ == '__main__':
    a = []
    content = field3_3(2,2)
    content2 =  field3_3(5,5)
    a.append(content)
    a.append(content2)
    print(a[0])