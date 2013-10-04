#!/usr/bin/env python
#
# Copyright 2005,2006,2011 Free Software Foundation, Inc.
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

from gnuradio import gr
from gnuradio import eng_notation
from gnuradio.eng_option import eng_option
from optparse import OptionParser
import time, struct, sys

from gnuradio import digital

# from current dir
#from transmit_path import transmit_path
from uhd_interface import uhd_transmitter

class my_top_block(gr.top_block):
    def __init__(self, options):
        gr.top_block.__init__(self)

        if(options.tx_freq is not None):
            self.sink = uhd_transmitter(options.args,
                                        options.bandwidth,
                                        options.tx_freq, options.tx_gain,
                                        options.spec, options.antenna,
                                        options.verbose)
        elif(options.to_file is not None):
            self.sink = gr.file_sink(gr.sizeof_gr_complex, options.to_file)
        else:
            self.sink = gr.null_sink(gr.sizeof_gr_complex)

        # do this after for any adjustments to the options that may
        # occur in the sinks (specifically the UHD sink)
        self.txpath = gr.file_source(gr.sizeof_gr_complex, options.data_file)
        self.amp = gr.multiply_const_cc(options.amp)
        self.connect(self.txpath, self.amp, self.sink)
        
# /////////////////////////////////////////////////////////////////////////////
#                                   main
# /////////////////////////////////////////////////////////////////////////////

def main():

    def send_pkt(payload='', eof=False, timeValid=False, timestamp=0):
        if eof:
            msg = gr.message(1)
        else:
            msg = gr.message_from_string(payload)
            if timeValid:
                secs = long(timestamp)
                frac_secs = timestamp - long(timestamp)
                msg.set_timestamp(secs, frac_secs)
        return tb.txpath.msgq().insert_tail(msg)    

    parser = OptionParser(option_class=eng_option, conflict_handler="resolve")
    parser.add_option("-n", "--num", type="eng_float", default=1,
                      help="set number of packets [default=%default]")
    parser.add_option("","--data-file", default=None,
                      help="use complex input file for transmission")
    parser.add_option("","--to-file", default=None,
                      help="Output file for modulated samples")
    parser.add_option("-W", "--bandwidth", type="eng_float",
                      default=4e6,
                      help="set symbol bandwidth [default=%default]")
    parser.add_option("", "--amp", type="eng_float", default=1, 
                      help="set gain factor for complex baseband floats [default=%default]")

    #transmit_path.add_options(parser, expert_grp)
    #digital.ofdm_mod.add_options(parser, expert_grp)
    uhd_transmitter.add_options(parser)

    (options, args) = parser.parse_args ()

    # build the graph
    tb = my_top_block(options)
    
    r = gr.enable_realtime_scheduling()
    if r != gr.RT_OK:
        print "Warning: failed to enable realtime scheduling"

    tb.start()                       # start flow graph
    
    ###########################################################################
    if options.data_file is None:
        sys.stderr.write("You must specify data file\n")
        parser.print_help(sys.stderr)
        sys.exit(1)

    print "End of Tx ..."
    time.sleep(1)
    ###########################################################################
    
    tb.wait()                       # wait for it to finish

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
