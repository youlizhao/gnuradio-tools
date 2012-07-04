#!/usr/bin/env python
#
# Copyright 2005, 2006 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

#
# @author: lzyou@inc.cuhk.edu.hk
# @date:   Mar. 31, 2012
# @note:
#   (1) The length of two files should be equivalent;
# TODO:
#   (1) write mimo_msgq_tx.py using msgq: need to solve the mimo timestamp problem
#

from gnuradio import gr, blks2
from gnuradio import uhd
from gnuradio import eng_notation
from gnuradio.eng_option import eng_option
from optparse import OptionParser

import time, struct, sys

class my_top_block(gr.top_block):
    def __init__(self, options):
        gr.top_block.__init__(self)

        self._bandwidth      = options.bandwidth
        self._gain_a         = options.tx_gain_a
        self._gain_b         = options.tx_gain_b
        self._tx_amplitude_a = options.tx_amplitude_a
        self._tx_amplitude_b = options.tx_amplitude_b
        self._tx_freq        = options.tx_freq
        self._args           = options.args
        self._external       = options.external
        self._ant            = options.antenna
        self._spec           = options.spec

        if(options.tx_freq is not None):
	    self.uhd_usrp_sink_0 = uhd.usrp_sink(
		    device_addr=options.args,
		    stream_args=uhd.stream_args(
			    cpu_format="fc32",
			    channels=range(2),
		    ),
	    )
            if options.external:
                self.uhd_usrp_sink_0.set_clock_source("external", 0)
                self.uhd_usrp_sink_0.set_clock_source("external", 1)
                # we use mimo for time synchronization
                self.uhd_usrp_sink_0.set_time_source("internal", 0)
                self.uhd_usrp_sink_0.set_time_source("mimo", 1)
            else:
	        self.uhd_usrp_sink_0.set_clock_source("internal", 0)
	        self.uhd_usrp_sink_0.set_clock_source("mimo", 1)
                self.uhd_usrp_sink_0.set_time_source("internal", 0)
	        self.uhd_usrp_sink_0.set_time_source("mimo", 1)
	    self.uhd_usrp_sink_0.set_samp_rate(self._bandwidth)
	    self.uhd_usrp_sink_0.set_center_freq(self._tx_freq, 0)
	    self.uhd_usrp_sink_0.set_bandwidth(self._bandwidth, 0)
	    self.uhd_usrp_sink_0.set_center_freq(self._tx_freq, 1)	    
	    self.uhd_usrp_sink_0.set_bandwidth(self._bandwidth, 1)	
        else:
            print "ERROR: NO MIMO SINK ..."

        options.interp	= 100e6/options.bandwidth	# FTW-specific convertion

        if (self._gain_a is None) or (self._gain_b is None):
            # if no gain was specified, use the mid-point in dB
            g = self.uhd_usrp_sink_0.get_gain_range()
            self._gain_a = float(g.start()+g.stop())/2
            self._gain_b = self._gain_a
            print "\nNo gain specified."
            print "Setting gain to %f (from [%f, %f])" % \
                (self._gain_a, g.start(), g.stop())
            self.uhd_usrp_sink_0.set_gain(self._gain_a, 0)
            self.uhd_usrp_sink_0.set_gain(self._gain_b, 1)

        # do this after for any adjustments to the options that may
        # occur in the sinks (specifically the UHD sink)
        if (options.from_file_a is not None) and (options.from_file_b is not None):
            self.txpath_a = gr.file_source(gr.sizeof_gr_complex, options.from_file_a)
            self.txpath_b = gr.file_source(gr.sizeof_gr_complex, options.from_file_b)

        self.amp_a = gr.multiply_const_cc(self._tx_amplitude_a)
        self.amp_b = gr.multiply_const_cc(self._tx_amplitude_b)

        self.delay_a = gr.delay(gr.sizeof_gr_complex, 0)
        self.delay_b = gr.delay(gr.sizeof_gr_complex, 0)

        self.connect(self.txpath_a, self.amp_a, self.delay_a, (self.uhd_usrp_sink_0, 0))
        self.connect(self.txpath_b, self.amp_b, self.delay_b, (self.uhd_usrp_sink_0, 1))

        if options.log:
            self.connect(self.amp_a, gr.file_sink(gr.sizeof_gr_complex, 'mimo_a.dat'))
            self.connect(self.amp_b, gr.file_sink(gr.sizeof_gr_complex, 'mimo_b.dat'))

        if options.verbose:
            self._print_verbage()


    def _print_verbage(self):
        """
        Prints information about the UHD transmitter
        """
        print "\nUHD Transmitter:"
        print "UHD Args:    %s"    % (self._args)
        print "Freq:        %sHz"  % (eng_notation.num_to_str(self._tx_freq))
        print "Gain:        %f %f dB" % (self._gain_a, self._gain_b)
        print "Sample Rate: %ssps" % (eng_notation.num_to_str(self._bandwidth))
        print "Antenna:     %s"    % (self._ant)
        print "Subdev Sec:  %s"    % (self._spec)
        if self._external:
            print "Using external Ref Clock and PPS"

# /////////////////////////////////////////////////////////////////////////////
#                                   main
# /////////////////////////////////////////////////////////////////////////////

def main():

    parser = OptionParser(option_class=eng_option, conflict_handler="resolve")

    # add general parser option
    parser.add_option("","--from-file-a", default=None,
                      help="use intput file for packet contents")
    parser.add_option("","--from-file-b", default=None,
                      help="use intput file for packet contents")
    parser.add_option("-v", "--verbose", action="store_true", default=False)
    parser.add_option("-l", "--log", action="store_true", default=False, help="write debug-output of individual blocks to disk")

    parser.add_option("-W", "--bandwidth", type="eng_float",
                      default=0.5e6,
                      help="set symbol bandwidth [default=%default]\
		      20e6  -> 802.11a/g, OFDM-symbolduration=4us, \
		      10e6  -> 802.11p, OFDM-symbolduration=8us")

    parser.add_option("", "--tx-amplitude-a", type="eng_float", default=0.1 , help="set gain factor for complex baseband floats [default=%default]")
    parser.add_option("", "--tx-amplitude-b", type="eng_float", default=0.2 , help="set gain factor for complex baseband floats [default=%default]")

    parser.add_option("-N", "--num", type="int", default=1 , help="set number of packets to send, [default=%default] ")
    parser.add_option("-r", "--repeat", type="int", default=1 , help="set number of HelloWorld (WorldHello) in single packet to send, [default=%default] ")

    # To simplify parser options
    parser.add_option("-a", "--args", type="string", default="addr0=192.168.10.2, addr1=192.168.20.2",
                          help="UHD device address args [default=%default]")
    parser.add_option("", "--spec", type="string", default=None,
                          help="Subdevice of UHD device where appropriate")
    parser.add_option("-A", "--antenna", type="string", default=None,
                          help="select Rx Antenna where appropriate")
    parser.add_option("", "--tx-freq", type="eng_float", default=None,
                          help="set transmit frequency to FREQ [default=%default]",
                          metavar="FREQ")
    parser.add_option("", "--tx-gain-a", type="eng_float", default=None,
                          help="set transmit gain in dB (default is midpoint)")
    parser.add_option("", "--tx-gain-b", type="eng_float", default=None,
                          help="set transmit gain in dB (default is midpoint)")
    parser.add_option("","--external", action="store_true", default=False,
                          help="enable discontinuous")
    
    (options, args) = parser.parse_args ()

    # build the graph    
    tb = my_top_block(options)

    r = gr.enable_realtime_scheduling()
    if r != gr.RT_OK:
       print "Warning: failed to enable realtime scheduling"

    # start flow graph
    tb.start()

    if (options.from_file_a is not None) and (options.from_file_b is not None):
       # send frame        
       counter = 0
       while counter < options.num:
          send_pkt(my_msg_a, my_msg_b, eof = False)
          counter = counter + 1

       print "End of Transmission"
       send_pkt(eof = True)
    else:
       print "Error: You must identfy two files (equal length)"

    # wait for it to finish
    tb.wait()                   

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
