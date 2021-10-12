#!/bin/bash --login
# this is intended for running DPS jobs; the input directory is where four files have been pulled because download=TRUE in the algorithm_config.yaml file
# a tar file of biomass models, a data table csv, and two raster stack geotiff files

conda activate r-with-gdal

basedir=$( cd "$(dirname "$0")" ; pwd -P )

unset PROJ_LIB

#install requirements packages - R packages

#conda install -c conda-forge -y r-gridExtra r-tidyverse r-randomForest r-raster r-rgdal r-data.table r-rlist r-gdalutils r-stringr r-gdalutils

mkdir output

# Note: the numbered args are fed in with the in_param_dict in the Run DPS chunk of 3.4_dps.ipynb

ATL08_CSV=${1}
TOPO_TIF=${2}
LANDSAT_TIF=${3}
${DO_SLOPE_VALID_MASK}=${4}
ATL08_SAMPLE_CSV=${5}
TAR_FILE=${basedir}/bio_models.tar


#unpack biomass models tar
#tar -xvf input/bio_models.tar

# This will put the *rds in the same dir as the R script
tar -xf ${TAR_FILE}

# This PWD is wherever the job is run (where the .sh is called from) 
OUTPUTDIR="${PWD}/output"

echo Rscript mapBoreal.R ${ATL08_CSV} ${TOPO_TIF} ${LANDSAT_TIF} ${ATL08_SAMPLE_CSV}
Rscript ${basedir}/mapBoreal.R ${ATL08_CSV} ${TOPO_TIF} ${LANDSAT_TIF} ${DO_SLOPE_VALID_MASK} ${ATL08_SAMPLE_CSV}


