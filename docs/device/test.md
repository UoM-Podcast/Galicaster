Test Device modules
===================

Videotest
---------

[] videotest: Mock video device.
       * name: Name assigned to the device.
       * device: Device type: videotest
       * flavor: Opencast "flavor" associated to the track. (presenter|presentation|other)
       * location: Device's mount point in the system (e.g. /dev/video0).
       * file: The file name where the track will be recorded.
       * active: Whether the device will be played and recorded. (True|False)
       * caps:  GStreamer capabilities of the device.
       * pattern: type of pattern to show. Run gst-inspect-0.10 videotestsrc fore more information. (0-20)
       * color1:  pattern foreground color, indicated on Big endian ARGB. Run gst-inspect-0.10 videotestsrc fore more information. (0,4294967495)
       * color2: pattern background color, indicated on Big endian ARGB. Run gst-inspect-0.10 videotestsrc fore more information. (0,4294967495)


       Pattern options
       	 	 	   (0): smpte            - SMPTE 100% color bars
                           (1): snow             - Random (television snow)
                           (2): black            - 100% Black
                           (3): white            - 100% White
                           (4): red              - Red
                           (5): green            - Green
                           (6): blue             - Blue
                           (7): checkers-1       - Checkers 1px
                           (8): checkers-2       - Checkers 2px
                           (9): checkers-4       - Checkers 4px
                           (10): checkers-8       - Checkers 8px
                           (11): circular         - Circular
                           (12): blink            - Blink
                           (13): smpte75          - SMPTE 75% color bars
                           (14): zone-plate       - Zone plate
                           (15): gamut            - Gamut checkers
                           (16): chroma-zone-plate - Chroma zone plate
                           (17): solid-color      - Solid color
                           (18): ball             - Moving ball
                           (19): smpte100         - SMPTE 100% color bars
                           (20): bar              - Bar

Audiotest
---------

 [] audiotest: Mock audio device.
       * name: Name assigned to the device.
       * device: Device type: pulse
       * flavor: Opencast "flavor" associated to the track. (presenter|presentation|other)
       * location: PulseAudio source name. Use default to select the same Input as the Sound Control. To list PulseAudio devices run: `pactl list | grep "Source" -A 5` and use "Name:" as the location field.
       * file: The file name where the track will be recorded.
       * wave: Generated waveform sample. Run gst-inspect-0.10 audiotestsrc fore more information. (0-12)
       * frequency: Test signal central frequency. (0-20000)
       * volume: Percent volume of the pattern. (0-1)
       * active: Whether the device will be played and recorded. (True|False)
       * vumeter: Activates data sending to the program's vumeter. (True|False) Only one device should be activated.
       * amplification: Gstreamer amplification value: < 1 decreases and > 1 increases volume. Values between 1 and 2 are commonly used. (0-10)
       * player:  Whether the audio input would be played on preview. (True|False)  

       Wave options
			   (0): sine             - Sine
                           (1): square           - Square
                           (2): saw              - Saw
                           (3): triangle         - Triangle
                           (4): silence          - Silence
                           (5): white-noise      - White uniform noise
                           (6): pink-noise       - Pink noise
                           (7): sine-table       - Sine table
                           (8): ticks            - Periodic Ticks
                           (9): gaussian-noise   - White Gaussian noise
                           (10): red-noise        - Red (brownian) noise
                           (11): blue-noise       - Blue noise
                           (12): violet-noise     - Violet noise
