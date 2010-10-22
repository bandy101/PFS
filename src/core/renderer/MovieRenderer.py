# encoding: UTF-8
#
# PhotoFilmStrip - Creates movies out of your pictures.
#
# Copyright (C) 2010 Jens Goepfert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import os
import sys
import re
from subprocess import Popen, PIPE, STDOUT

from core.Aspect import Aspect
from core.OutputProfile import OutputProfile
from core.renderer.SingleFileRenderer import SingleFileRenderer


class MEncoderRenderer(SingleFileRenderer):
    
    def __init__(self):
        SingleFileRenderer.__init__(self)
        
        self._encOut = None
        self._encErr = None
        
        self._procEncoder = None
        
    @staticmethod
    def CheckDependencies(msgList):
        SingleFileRenderer.CheckDependencies(msgList)
        
        proc = Popen("mencoder", stdout=PIPE, stderr=STDOUT, shell=True)
        proc.wait()
        output = proc.stdout.read()
        if not re.search("^(mplayer|mencoder)", output, re.I):
            msgList.append(_(u"mencoder (mencoder) required!"))

    @staticmethod
    def GetProperties():
        return SingleFileRenderer.GetProperties() + ["Bitrate", "RenderSubtitle"]

    @staticmethod
    def GetDefaultProperty(prop):
        if prop == "RenderSubtitle":
            return False
        return SingleFileRenderer.GetDefaultProperty(prop)

    def ProcessFinalize(self, image):
        image.save(self._procEncoder.stdin, "JPEG")
    
    def __CleanUp(self):
        self._procEncoder.communicate()

        for log in [self._encOut, self._encErr]:
            if log:
                log.close()
        
    def ProcessAbort(self):
        self.__CleanUp()

    def Prepare(self):
        self._encOut = open(os.path.join(self.GetOutputPath(), "mencoder_out.log"), 'w')
        self._encErr = open(os.path.join(self.GetOutputPath(), "mencoder_err.log"), 'w')
        
        cmd = self._GetCmd()
        self._procEncoder = Popen(cmd, stdin=PIPE, stdout=self._encOut, stderr=self._encErr, shell=True)
        
    def Finalize(self):
        self.__CleanUp()
        
        if self.__class__.GetProperty("RenderSubtitle"):
            # delete subtitle file, if subtitle is rendered in video
            srtPath = os.path.join(self.GetOutputPath(), "output.srt")
            if os.path.exists(srtPath):
                os.remove(srtPath)

    def _GetCmd(self):
        raise NotImplementedError()
    
    def _GetSubArgs(self):
        if self.__class__.GetProperty("RenderSubtitle"):
            subArgs = "-sub \"%s%soutput.srt\" -subcp utf8 -font \"%s\"" % (self.GetOutputPath(), os.sep, r"C:\Dokumente und Einstellungen\jens\Anwendungsdaten\PhotoFilmStrip\extBin\mplayer\mplayer\font.desc")
        else:
            subArgs = ""
        return subArgs
    
    def _GetAudioArgs(self):
        if self.PAudioFile is None:
            audioArgs = ""
        else:
            audioArgs = "-audiofile \"%s\"" % self.PAudioFile
        return audioArgs
    
    def _GetFrameRate(self):
        if self.PProfile.GetVideoNorm() == OutputProfile.PAL:
            framerate = "25/1"
        else:
            framerate = "30000/1001"
        return framerate
    
    def _GetBitrate(self):
        if self.__class__.GetProperty("Bitrate") == self.__class__.GetDefaultProperty("Bitrate"):
            bitrate = self.PProfile.GetBitrate()
        else:
            bitrate = self.__class__.GetProperty("Bitrate")
        return bitrate


class MovieRenderer(MEncoderRenderer):
    
    def __init__(self):
        MEncoderRenderer.__init__(self)
        
    @staticmethod
    def GetName():
        return _(u"Video clip (AVI)")
    
    @staticmethod
    def GetProperties():
        return MEncoderRenderer.GetProperties() + ["FFOURCC"]

    @staticmethod
    def GetDefaultProperty(prop):
        if prop == "FFOURCC":
            return "XVID"
        return MEncoderRenderer.GetDefaultProperty(prop)

    def _GetCmd(self):
        if self.PProfile.GetName() in ["VCD", "SVCD", "DVD"]:
            cmd = self.__ProcessMpegOutput()
        else:
            cmd = self.__ProcessAviOutput()
        return cmd
        
    def __ProcessMpegOutput(self):
        aspect = "%.3f" % Aspect.ToFloat(self._aspect)
        if self.PProfile.GetVideoNorm() == OutputProfile.PAL:
            keyint = 15
            res = self.PProfile.GetResolution()
        else:
            keyint = 18
            res = self.PProfile.GetResolution()
            
        if self.PProfile.GetName() == "VCD":
            mpgFormat = "xvcd"
            srate = "44100"
            lavcopts = "vcodec=mpeg1video:keyint=%(keyint)s:vrc_buf_size=327:vrc_minrate=1152:vbitrate=1152:vrc_maxrate=1152:acodec=mp2:abitrate=224:aspect=%(aspect)s" % {"keyint": keyint,
                                                                                                                                                                           "aspect": aspect}
        elif self.PProfile.GetName() == "SVCD":
            mpgFormat = "xsvcd"
            srate = "44100"
            lavcopts = "vcodec=mpeg2video:mbd=2:keyint=%(keyint)s:vrc_buf_size=917:vrc_minrate=600:vbitrate=2500:vrc_maxrate=2500:acodec=mp2:abitrate=224:aspect=%(aspect)s" % {"keyint": keyint,
                                                                                                                                                                                "aspect": aspect}
        elif self.PProfile.GetName() == "DVD":
            mpgFormat = "dvd:tsaf"
            srate = "48000"
            lavcopts = "vcodec=mpeg2video:vrc_buf_size=1835:vrc_maxrate=9800:vbitrate=5000:keyint=%(keyint)s:vstrict=0:acodec=ac3:abitrate=192:aspect=%(aspect)s" % {"keyint": keyint,
                                                                                                                                                                     "aspect": aspect}
        else:
            raise RuntimeError('format not supported')
            
#              "-vf scale=%(resx)d:%(resy)d,harddup " \
#              "-of mpeg -mpegopts format=%(format)s " \
#              "-ofps %(framerate)s " \
        cmd = "mencoder -cache 1024 -demuxer lavf -fps 25 -lavfdopts format=mjpeg "\
              "%(audioArgs)s " \
              "%(subArgs)s " \
              "-oac lavc -ovc lavc " \
              "-of lavf -lavfopts format=mpg " \
              "-srate %(srate)s -af lavcresample=%(srate)s " \
              "-lavcopts %(lavcopts)s " \
              "-ofps 25 " \
              "-o \"%(path)s%(sep)soutput.mpg\" -" % {'path': self.GetOutputPath(),
                                                      'sep': os.sep,
                                                      'audioArgs': self._GetAudioArgs(),
                                                      "subArgs": self._GetSubArgs(),
                                                      'framerate': self._GetFrameRate(),
                                                      'format': mpgFormat,
                                                      'resx': res[0],
                                                      'resy': res[1],
                                                      'srate': srate,
                                                      'lavcopts': lavcopts}
        
        return cmd


    def __ProcessAviOutput(self):
        cmd = "mencoder -cache 1024 -demuxer lavf -fps 25 -lavfdopts format=mjpeg " \
              "%(audioArgs)s " \
              "%(subArgs)s " \
              "-oac mp3lame -lameopts cbr:br=192 -srate 44100 " \
              "-ovc lavc -lavcopts vcodec=mpeg4:vbitrate=%(bitrate)d:vhq:autoaspect -ffourcc %(ffourcc)s " \
              "-ofps %(framerate)s " \
              "-o \"%(path)s%(sep)soutput.avi\" -" % {'path': self.GetOutputPath(),
                                                      'sep': os.sep,
                                                      'ffourcc': MovieRenderer.GetProperty('FFOURCC'),
                                                      'bitrate': self._GetBitrate(),
                                                      'audioArgs': self._GetAudioArgs(),
                                                      "subArgs": self._GetSubArgs(),
                                                      'framerate': self._GetFrameRate()}
        return cmd


class FlashMovieRenderer(MEncoderRenderer):
    
    def __init__(self):
        MEncoderRenderer.__init__(self)
        
    @staticmethod
    def GetName():
        return _(u"Flash-Video (FLV)")
    
    @staticmethod
    def GetProperties():
        return MEncoderRenderer.GetProperties()

    @staticmethod
    def GetDefaultProperty(prop):
        return MEncoderRenderer.GetDefaultProperty(prop)

    def _GetCmd(self):
        cmd = "mencoder -cache 1024 -fps 25 -demuxer lavf -lavfdopts format=mjpeg " \
              "%(audioArgs)s " \
              "%(subArgs)s " \
              "-oac mp3lame -lameopts cbr:br=128 -srate 44100 " \
              "-ovc lavc -lavcopts vcodec=flv:vbitrate=%(bitrate)d:mbd=2:mv0:trell:v4mv:cbp:last_pred=3 " \
              "-of lavf " \
              "-ofps %(framerate)s " \
              "-o \"%(path)s%(sep)soutput.flv\" -" % {'path': self.GetOutputPath(),
                                                      'sep': os.sep,
                                                      'bitrate': self._GetBitrate(),
                                                      'audioArgs': self._GetAudioArgs(),
                                                      "subArgs": self._GetSubArgs(),
                                                      'framerate': self._GetFrameRate()}
        return cmd


class MJPEGRenderer(MEncoderRenderer):
    
    def __init__(self):
        MEncoderRenderer.__init__(self)
        
    @staticmethod
    def GetName():
        return _(u"Motion-JPEG (MJPEG)")
    
    @staticmethod
    def GetProperties():
        return MEncoderRenderer.GetProperties()

    @staticmethod
    def GetDefaultProperty(prop):
        return MEncoderRenderer.GetDefaultProperty(prop)

    def _GetCmd(self):
        cmd = "mencoder -cache 1024 -fps 25 -demuxer lavf -lavfdopts format=mjpeg " \
              "%(audioArgs)s " \
              "%(subArgs)s " \
              "-oac mp3lame -lameopts cbr:br=192 -srate 44100 " \
              "-ovc lavc -lavcopts vcodec=mjpeg " \
              "-of lavf " \
              "-ofps %(framerate)s " \
              "-o \"%(path)s%(sep)soutput.avi\" -" % {'path': self.GetOutputPath(),
                                                      'sep': os.sep,
                                                      'audioArgs': self._GetAudioArgs(),
                                                      "subArgs": self._GetSubArgs(),
                                                      'framerate': self._GetFrameRate()}
        return cmd
