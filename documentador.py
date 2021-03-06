#!/usr/bin/env python

""" A simple screen-capture utility.  Utilizes ffmpeg or avconv with h264
support. By default it captures the entire desktop.
"""

###############################################################################
# Criado por Rafael Rodrigues
#
# Este sistema serve para que eu pare de escrever, odeio escrever !!
# Sendo assim ele vai gravar meus procedimentos realizados em video e na próxima
# versão eu vou criar documentações automáticas !!!!!
#
###############################################################################


DEFAULT_FPS = 15
DEFAULT_FILE_EXTENSION = "mkv"
ACCEPTABLE_FILE_EXTENSIONS = ["avi", "mp4", "mov", "mkv", "ogv", "webm"]
DEFAULT_CAPTURE_AUDIO_DEVICE = "pulse"
DEFAULT_CAPTURE_DISPLAY_DEVICE = ":0.0"
DEFAULT_AUDIO_CODEC = "aac"
DEFAULT_VIDEO_CODEC = "h264"

import os
import sys
import os.path
import glob
import optparse
import subprocess
import re


PYTHON_3 = (sys.version_info[0] == 3)


#Pacote opcionais
try:
    import Tkinter
    have_tk = True
except ImportError:
    have_tk = False

try:
    import multiprocessing
    have_multiproc = True
except ImportError:
    have_multiproc = False


# Supported tools (executable names)
tools = ['ffmpeg', 'avconv']

# Video codec lines
vcodecs = {}
vcodecs["h264_lossless"] = ["-c:v", "libx264", "-g", "15", "-crf", "0", "-pix_fmt", "yuv444p"]
vcodecs["h264"] = ["-c:v", "libx264", "-vprofile", "baseline", "-g", "15", "-crf", "1", "-pix_fmt", "yuv420p"]
vcodecs["mpeg4"] = ["-c:v", "mpeg4", "-g", "15", "-qmax", "1", "-qmin", "1"]
#vcodecs["xvid"] = ["-c:v", "libxvid", "-g", "15", "-b:v", "40000k"]
vcodecs["huffyuv"] = ["-c:v", "huffyuv"]
vcodecs["ffv1"] = ["-c:v", "ffv1", "-coder", "1", "-context", "1"]
vcodecs["vp8"] = ["-c:v", "libvpx", "-g", "15", "-qmax", "1", "-qmin", "1"]
vcodecs["theora"] = ["-c:v", "libtheora", "-g", "15", "-b:v", "40000k"]
#vcodecs["dirac"] = ["-c:v", "libschroedinger", "-g", "15", "-b:v", "40000k"]

# Audio codec lines
acodecs = {}
acodecs["pcm"] = ["-c:a", "pcm_s16le"]
#acodecs["flac"] = ["-c:a", "flac"]
acodecs["vorbis"] = ["-c:a", "libvorbis", "-b:a", "320k"]
acodecs["mp3"] = ["-c:a", "libmp3lame", "-b:a", "320k"]
acodecs["aac"] = ["-c:a", "libvo_aacenc", "-b:a", "320k"]
acodecs["faac"] = ["-c:a", "libfaac", "-b:a", "320k"]
acodecs["ffaac"] = ["-strict", "experimental", "-c:a", "aac", "-b:a", "320k"]


def capture_line(fps, x, y, height, width, display_device, audio_device, video_codec, audio_codec, output_path):
    """ Returns the command line to capture video+audio, in a list form
        compatible with Popen.
    """
    threads = 2
    if have_multiproc:
        # Detect the number of threads we have available
        threads = multiprocessing.cpu_count()
    line = [TOOL,
            "-f", "alsa",
            "-ac", "2",
            "-i", str(audio_device),
            "-f", "x11grab",
            "-r", str(fps),
            "-s", "%dx%d" % (int(height), int(width)),
            "-i", display_device + "+" + str(x) + "," + str(y)]
    line += acodecs[audio_codec]
    line += vcodecs[video_codec]
    line += ["-threads", str(threads), str(output_path)]
    return line


def video_capture_line(fps, x, y, height, width, display_device, video_codec, output_path):
    """ Returns the command line to capture video (no audio), in a list form
        compatible with Popen.
    """
    threads = 2
    if have_multiproc:
        # Detect the number of threads we have available
        threads = multiprocessing.cpu_count()

    line = [TOOL,
            "-f", "x11grab",
            "-r", str(fps),
            "-s", "%dx%d" % (int(height), int(width)),
            "-i", display_device + "+" + str(x) + "," + str(y)]
    line += vcodecs[video_codec]
    line += ["-threads", str(threads), str(output_path)]
    return line


def audio_capture_line(audio_device, audio_codec, output_path):
    """ Returns the command line to capture audio (no video), in a list form
        compatible with Popen.
    """
    line = [TOOL,
            "-f", "alsa",
            "-ac", "2",
            "-i", str(audio_device)]
    line += acodecs[audio_codec]
    line += [str(output_path)]
    return line


def get_desktop_resolution():
    """ Returns the resolution of the desktop as a tuple.
    """
    if have_tk:
        # Use tk to get the desktop resolution if we have it
        root = Tkinter.Tk()
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        root.destroy()
        return (width, height)
    else:
        # Otherwise call xdpyinfo and parse its output
        try:
            proc = subprocess.Popen("xdpyinfo", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            return None
        out, err = proc.communicate()
        if PYTHON_3:
            lines = str(out).split("\\n")
        else:
            lines = out.split("\n")
        for line in lines:
            if "dimensions" in line:
                line = re.sub(".*dimensions:[ ]*", "", line)
                line = re.sub("[ ]*pixels.*", "", line)
                wh = line.strip().split("x")
                return (int(wh[0]), int(wh[1]))


def get_window_position_and_size():
    """ Prompts the user to click on a window, and returns the window's
        position and size.
    """
    try:
        proc = subprocess.Popen("xwininfo", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        return None
    out, err = proc.communicate()
    if PYTHON_3:
        lines = str(out).split("\\n")
    else:
        lines = out.split("\n")
    x = 0
    y = 0
    w = 0
    h = 0
    xt = False
    yt = False
    wt = False
    ht = False
    for line in lines:
        if "Absolute upper-left X:" in line:
            x = int(re.sub("[^0-9]", "", line))
            xt = True
        elif "Absolute upper-left Y:" in line:
            y = int(re.sub("[^0-9]", "", line))
            yt = True
        elif "Width:" in line:
            w = int(re.sub("[^0-9]", "", line))
            wt = True
        elif "Height:" in line:
            h = int(re.sub("[^0-9]", "", line))
            ht = True
    if xt and yt and wt and ht:
        return (x, y, w, h)
    else:
        return None


def get_default_output_path(ext=None):
    """ Creates a default output file path.
        Pattern: out_####.ext
    """
    if ext == None:
        ext = DEFAULT_FILE_EXTENSION
    filenames = glob.glob("out_????" + "." + ext)
    for i in range(1, 9999):
        name = "out_" + str(i).rjust(4,'0') + "." + ext
        tally = 0
        for f in filenames:
            if f == name:
                tally += 1
        if tally == 0:
            return name
    return "out_9999" + "." + ext


def print_codecs():
    """ Prints a list of the available audio/video codecs.
    """
    a = []
    v = []
    for i in acodecs:
        a += [i]
    for i in vcodecs:
        v += [i]
    a.sort()
    v.sort()

    print("Audio codecs:")
    for i in a:
        print("  " + str(i))

    print("Video codecs:")
    for i in vcodecs:
        print("  " + str(i))


def check_tool(command):
    try:
        proc = subprocess.Popen([command, "-c:v", "huffyuv"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out, err = proc.communicate()
        if PYTHON_3:
            lines = str(out).split("\\n")
        else:
            lines = out.split("\n")
        for line in lines:
            if "Unrecognized option" in line:
                raise
        return 1
    except:
        return 0


if __name__ == "__main__":
    # Parse command line arguments
    parser = optparse.OptionParser(usage="%prog [options] [output_file" + "." + DEFAULT_FILE_EXTENSION + "]")
    parser.add_option("-w", "--capture-window", action="store_true", dest="capture_window",
                      default=False,
                      help="prompt user to click on a window to capture")
    parser.add_option("-n", "--no-audio", action="store_true", dest="no_audio",
                      default=False,
                      help="don't capture audio")
    parser.add_option("-r", "--fps", dest="fps",
                      type="int", default=DEFAULT_FPS,
                      help="frame rate to capture video at. Default: " + str(DEFAULT_FPS))
    parser.add_option("-p", "--position", dest="xy", metavar="XxY",
                      type="string", default=None,
                      help="upper left corner of the capture area (in pixels from the upper left of the screen). Default: 0x0")
    parser.add_option("-s", "--size", dest="size",
                      type="string", default=None, metavar="WIDTHxHEIGHT",
                      help="resolution of the capture area (in pixels). Default: entire desktop")
    parser.add_option("--crop-top", dest="crop_top",
                      type="int", default=0,
                      help="number of pixels to crop off the top of the capture area")
    parser.add_option("--crop-bottom", dest="crop_bottom",
                      type="int", default=0,
                      help="number of pixels to crop off the bottom of the capture area")
    parser.add_option("--crop-left", dest="crop_left",
                      type="int", default=0,
                      help="number of pixels to crop off the left of the capture area")
    parser.add_option("--crop-right", dest="crop_right",
                      type="int", default=0,
                      help="number of pixels to crop off the right of the capture area")
    parser.add_option("-a", "--audio-device", dest="audio_device",
                      default=DEFAULT_CAPTURE_AUDIO_DEVICE,
                      help="the audio device to capture from (eg. hw:0).  Default: " + DEFAULT_CAPTURE_AUDIO_DEVICE)
    parser.add_option("-d", "--display-device", dest="display_device",
                      default=DEFAULT_CAPTURE_DISPLAY_DEVICE,
                      help="the display device to capture from (eg. :0.0).  Default: " + DEFAULT_CAPTURE_DISPLAY_DEVICE)
    parser.add_option("--acodec", dest="acodec",
                      default=DEFAULT_AUDIO_CODEC,
                      help="the audio codec to encode with.  Default: " + DEFAULT_AUDIO_CODEC)
    parser.add_option("--vcodec", dest="vcodec",
                      default=DEFAULT_VIDEO_CODEC,
                      help="the video codec to encode with.  Default: " + DEFAULT_VIDEO_CODEC)
    parser.add_option("--codecs", action="store_true", dest="list_codecs",
                      default=False,
                      help="display the available audio and video codecs")
    parser.add_option("--container", dest="container",
                      help="the media container format to use if a filename is not given.  "
                           "Specified by file extension.  Default: " + DEFAULT_FILE_EXTENSION)
    parser.add_option("--tool", dest="tool",
                      help="capture and conversion tool to use (autodetected by default)." +
                           "  Supported %s." % ", ".join(tools))

    opts, args = parser.parse_args()

    # Print list of codecs, if requested
    if opts.list_codecs:
        print_codecs()
        exit(0)

    # Checking if tool is requested and available
    if opts.tool:
        if not check_tool(opts.tool):
            exit("Error: tool check failed for %s" % opts.tool)
        TOOL = opts.tool
    # Autodetect tool if not requested
    else:
        for tool in tools:
           if check_tool(tool):
               TOOL = tool
               break
        else:
            print("No supported capture/convertion tool found, try")
            print("to install one of: " + ', '.join(tools))
            exit(-1)

    print("Using '%s' tool for capture and conversion." % TOOL)


    # Check that specified container format is supported
    if opts.container and opts.container not in ACCEPTABLE_FILE_EXTENSIONS:
        print("Error: " + opts.container + " is not a supported container format.")
        exit(-1)

    # Set output path
    outfile = None
    if args:
        outfile = args[0]
    else:
        outfile = get_default_output_path(ext=opts.container)

    # Check that outfile has a valid extension for container
    # If container format is not specified, try to guess it from filename
    container = None
    exts = outfile.rsplit(".", 1)
    if len(exts) == 1 or exts[1] not in ACCEPTABLE_FILE_EXTENSIONS:
        # No container and no valid extension
        if not opts.container:
            container = DEFAULT_FILE_EXTENSION
        # Container is set, but file extension is invalid
        else:
            container = opts.container
        outfile += "." + container
    else:
        # No container, but extension is valid
        if not opts.container:
            container = exts[1]
        else:
            container = opts.container


    acodec = opts.acodec
    vcodec = opts.vcodec
    # Check and fix container/codec constaints
    if container == "webm":
        if vcodec not in ["vp8"]:
            print("Warning: Selected codec (%s) is invalid for webm format\n"
                  "         Changing codec to %s" % (vcodec, "vp8"))
            vcodec = "vp8"
        if acodec not in ["vorbis"]:
            print("Warning: Selected codec (%s) is invalid for webm format\n"
                  "         Changing codec to %s" % (acodec, "vorbis"))
            acodec = "vorbis"

    # Get desktop resolution
    try:
        dres = get_desktop_resolution()
    except:
        print("Error: unable to determine desktop resolution.")
        raise

    # Capture values
    fps = opts.fps
    if opts.capture_window:
        print("Please click on a window to capture.")
        x, y, width, height = get_window_position_and_size()
    else:
        if opts.xy:
            if re.match("^[0-9]*x[0-9]*$", opts.xy.strip()):
                xy = opts.xy.strip().split("x")
                x = int(xy[0])
                y = int(xy[1])
            else:
                raise parser.error("position option must be of form XxY (e.g. 50x64)")
        else:
            x = 0
            y = 0

        if opts.size:
            if re.match("^[0-9]*x[0-9]*$", opts.size.strip()):
                size = opts.size.strip().split("x")
                width = int(size[0])
                height = int(size[1])
            else:
                raise parser.error("size option must be of form HxW (e.g. 1280x720)")
        else:
            width = dres[0]
            height = dres[1]

    # Calculate cropping
    width -= opts.crop_left + opts.crop_right
    height -= opts.crop_top + opts.crop_bottom
    x += opts.crop_left
    y += opts.crop_top

    # Make sure the capture resolution conforms to the restrictions
    # of the video codec.  Crop to conform, if necessary.
    mults = {"h264": 2, "h264_lossless": 2, "mpeg4": 2, "dirac": 2, "xvid": 2, "theora": 8, "huffyuv": 2, "ffv1": 1, "vp8": 1}
    width -= width % mults[vcodec]
    height -= height % mults[vcodec]

    # Verify that capture area is on screen
    if (x + width) > dres[0] or (y + height) > dres[1]:
        parser.error("specified capture area is off screen.")

    # Capture!
    if not opts.no_audio:
        proc = subprocess.Popen(capture_line(fps, x, y, width, height, opts.display_device, opts.audio_device, vcodec, acodec, outfile)).wait()
    else:
        proc = subprocess.Popen(video_capture_line(fps, x, y, width, height, opts.display_device, vcodec, outfile)).wait()

    print("Done!")
