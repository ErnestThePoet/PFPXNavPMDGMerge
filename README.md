# PFPXNav2PMDG

If you have a PFPX nav database containing additional data to a PMDG nav database, this script makes it possible to merge these extra navdata into a new PMDG nav database.  
In detail, additional waypoints, airports, navaids and airways are merged, whereas additional SID/STARs are not because SID/STARs in PFPX database are made up of bare waypoints, without altitude and speed constraints required for PMDG.

## How To Use
- In the directory containing our `.py` files, create three directories named `PFPX`, `PMDG` and `merged`. Place your PFPX and PMDG navdata files inside `PFPX` and `PMDG`, which should contain the following files.
```
-PFPX
|navdata.nav

-PMDG
|airports.dat
|wpNavAID.txt
|wpNavAPT.txt
|wpNavFIX.txt
|wpNavRTE.txt
```

- Run `pfpx_navdata_decode.py`, which decodes the PFPX nav database into `PFPX/decoded.nav`.  
- Run `merge.py`, which merges navdata and puts them in directory `merged`.  
- That's Done.