
# Useful tools for GNURadio programming

## matlab/
Matlab codes for read and write samples

*  Correlation.m: cross-correlation program, with different kind of preambles

## python/
Python codes for tx/rx samples. It should be used with the grforwarder project, which supports timestamp mechanism.

*  raw_msgqtx.py: transmitting modulated raw symbols
*  uhd_interface.py: modified version for supporting timestamp
*  uhd_rx_cfile.py: rx sampling program

## examples/
Python codes from gr-digital. We run examples here instead of in gr-digital to escape update changes :-(
