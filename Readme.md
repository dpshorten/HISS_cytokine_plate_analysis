# Analysis of Blood Data from Luminex Assay Plates for HISS

## Introduction

This repository contains code for extracting and repackaging the the data from the Luminex assay plates used in the 
HISS-KNOW study. It also infers concentrations of cytokines based on the observed fluorescent intensities of the samples
and those observed for the calibration standard solutions. The main components of this pipeline are:
- Reading the raw data produced by the Luminex assay and transforming it into a more usable format.
- Reading the labelled sample locations on the plates and associating them with the raw data.
- Fitting calibration (standard) curves to the observed flourescent intensities of the calibration standard solutions
and using these to infer the concentrations of the samples.
- Preliminary results analysis.

## Running the Code

1. Change the absolute file paths at the top of `parameter/july_2024_parameters.yaml` to the new locations where you
have cloned this repository.
2. Create a new Python virtual environment and install the required packages using the command `pip install -r requirements.txt`.
The code has been tested inside an Anaconda environment using Python 3.11. If you want to use Anaconda the following should work
```
conda create -n HISS-plates python=3.11
conda activate HISS-plates
pip install -r requirements.txt
```
4. Add the raw data files to the `data` directory. This data is not included in the repository for data security reasons.
Please contact me for access to the data.
5. Run the script `scripts/process_data.sh`. The paths in that script assume that you are running it from the root
directory of this repository. This will run the entire pipeline and write the file `estimated_concentrations.csv` to 
the `output` directory. This file contains the estimated concentrations of the samples as well as raw plate data. 
Intermediate processing files are also written to the `output` directory.
6. Once this script has been run, you can use the notebooks in the `notebooks` directory. Two important notebooks are:
    - `inspect_estimations_and_calibrations_curves.ipynb`. This notebook produces an interactive plot of the calibration 
    curves which allows inspection of how each estimated concentration was calculated.
    - `preliminary_concentration_analysis.ipynb` which produces plots of the estimated concentrations at different time
    points as well plots of differences between the concentrations at different time points.
   
    The other notebooks perform components of the same analysis that is run by the script `scripts/process_data.sh`.
    They allow for visibility into the intermediate steps of the analysis and are useful for debugging. 

## Future Work

1. From the plots produced by `inspect_estimations_and_calibrations_curves.ipynb`, it is clear that there are errors
in the measured fluorescent intensity for some wells. For an example, look at the reads for the calibration standards for 
plate 14. I will be writing code which will attempt to deal with these errors in an automated fashion, however, we may 
need to revert to manual inspection in some cases.
2. Estimating uncertainties for the concentrations.
3. Investigating the use of different calibration curves. 5-parameter logistic curves are currently used. I intend to 
try 4-parameter logistic curves, quadratic curves and possibly others.
4. Further analysis of trends in the cytokine concentrations over time.