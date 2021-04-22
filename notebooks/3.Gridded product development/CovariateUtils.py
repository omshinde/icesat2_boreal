import numpy
from rasterio import enums
from rasterio.io import MemoryFile
from rasterio.crs import CRS
from rasterio.vrt import WarpedVRT
from rasterio.warp import array_bounds, calculate_default_transform
from rio_cogeo.profiles import cog_profiles
from rio_tiler.utils import create_cutline
from rio_cogeo.cogeo import cog_translate

def write_cog(stack, out_fn, in_crs, src_transform, bandnames, out_crs=None, clip_geom=None, clip_crs=None, align=False):
    '''
    Write a cloud optimized geotiff with compression from a numpy stack of bands with labels
    Reproject if needed, Clip to bounding box if needed.
    
    Parameters:
    stack: np.array 
        3d numpy array (bands, height, width) 
    out_fn: str
        Output Filename
    in_crs: str
        CRS of input raster
    src_transform: Affine
        Affine transform of imput raster
    bandnames: list[str]
        List of bandnames in band/dimension order that matches stack
    out_crs: CRS, optional
        If reprojecting, the output CRS
    clip_geom: dict, optional
        Polygon geometry as geojson dictionary
    clip_crs: CRS, optional
        CRS of clip_geom
    align: bool, optional
        True aligns the output raster with the top left corner of the clip_geom. clip_geom CRS must be the same as
        the out_crs.
    '''
    
    if out_crs is None:
        out_crs = in_crs
   
    # Set the profile for the in memory raster based on the ndarry stack
    src_profile = dict(
        driver="GTiff",
        height=stack.shape[1],
        width=stack.shape[2],
        count=stack.shape[0],
        dtype=stack.dtype,
        crs=in_crs,
        transform=src_transform,
        nodata=numpy.nan)

    # Set the reproject parameters for the WarpedVRT read
    vrt_params = {}
    if out_crs is not None:
        vrt_params["crs"] = out_crs
        vrt_params["src_crs"] = in_crs
        vrt_params["dtype"] = str(stack.dtype)
        vrt_params["nodata"] = numpy.nan
        vrt_params["resampling"] = enums.Resampling.bilinear
        
        #TODO: Add  transform with resolution specification
        if out_crs != in_crs:
            left, bottom, right, top = array_bounds(height = src_profile["height"],
                   width = src_profile["width"], 
                   transform = src_profile["transform"])
            vrt_params["transform"], vrt_params["width"], vrt_params["height"] = calculate_default_transform(
                src_crs = in_crs,
                dst_crs = out_crs,
                left = left,
                bottom = bottom,
                right = right,
                top = top,
                width = src_profile["width"],
                height = src_profile["height"],
                resolution = (30, 30)
                )
        if align is True:
            left, bottom, right, top = clip_geom.total_bounds
            vrt_params["transform"], vrt_params["width"], vrt_params["height"] = calculate_default_transform(
                src_crs = in_crs,
                dst_crs = out_crs,
                left = left,
                bottom = bottom,
                right = right,
                top = top,
                width = src_profile["width"],
                height = src_profile["height"],
                resolution = (30, 30)
                )
            
    print('Orig stack shape: ',stack.shape)
        
    # Get the rio-cogeo profile for deflate compression, modify some of the options
    dst_profile = cog_profiles.get("deflate")
    dst_profile['blockxsize']=256
    dst_profile['blockysize']=256
    dst_profile['predictor']=2
    dst_profile['zlevel']=7
    
    with MemoryFile() as memfile:
        with memfile.open(**src_profile) as mem:
            # Populate the input file with NumPy array
            # HERE; this memory file can be reprojected then saved
            mem.write(stack)

            if clip_geom is not None:
                # Do the clip to geometry (rasterio takes this; not in_bbox)
                # # https://rasterio.readthedocs.io/en/latest/topics/masking-by-shapefile.html
                #mem, clipped_transform = rasterio.mask.mask(mem, clip_geom, crop=True)
                #out_meta = mem.meta
                #out_meta.update({"driver": "GTiff",
                #                 "height": mem.shape[1],
                #                 "width": mem.shape[2],
                #                 "transform": clipped_transform})
                clip_geom_json = clip_geom.__geo_interface__['features'][0]['geometry']
                vrt_params["cutline"] = create_cutline(mem, clip_geom_json, geometry_crs = clip_crs)
            
                               
            print('Writing img to memory...')
            
            for n in range(len(bandnames)):
                mem.set_band_description(n+1, bandnames[n])
        
            with WarpedVRT(mem,  **vrt_params) as vrt:
                print(vrt.profile)
                cog_translate(
                    vrt,
                    # To avoid rewriting over the infile
                    out_fn,
                    dst_profile,
                    add_mask=True,
                    in_memory=True,
                    quiet=False)

    print('Image written to disk: ', out_fn)