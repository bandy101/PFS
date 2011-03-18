# encoding: UTF-8
#
# PhotoFilmStrip - Creates movies out of your pictures.
#
# Copyright (C) 2011 Jens Goepfert
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

import time

import wx

try:
    import cairo
    import wx.lib.wxcairo
except ImportError:
    cairo = None

from core.OutputProfile import OutputProfile
from core.BaseRenderer import BaseRenderer

from core.backend.CairoBackend import CairoBackend
from core.backend.Transformer import Transformer


class CairoRenderer(BaseRenderer):
    
    def __init__(self):
        BaseRenderer.__init__(self)
        self._backend = CairoBackend()
        self._ctx = None
        self._mainClock = Clock()
        self._framerate = None
        
        self._screen = wx.Frame(wx.GetApp().GetTopWindow(), 
                                style=wx.DEFAULT_FRAME_STYLE | wx.RESIZE_BORDER)
        self._screen.Bind(wx.EVT_PAINT, self.OnPaint)
        self._screen.Show()
        
    @staticmethod
    def GetName():
        return u"Cairo"
    
    @staticmethod
    def CheckDependencies(msgList):
        BaseRenderer.CheckDependencies(msgList)
        if cairo is None:
            msgList.append("cairo not installed!")

    @staticmethod
    def GetProperties():
        return BaseRenderer.GetProperties() + ["RenderSubtitle"]

    @staticmethod
    def GetDefaultProperty(prop):
        if prop == "RenderSubtitle":
            return "false"
        return BaseRenderer.GetDefaultProperty(prop)

    def _GetFrameRate(self):
        if self.PProfile.GetVideoNorm() == OutputProfile.PAL:
            framerate = 25.0
        else:
            framerate = 30000.0 / 1001.0
        return framerate
    
    def ProcessFinalize(self, backendCtx):
        if backendCtx:
            cairoImg = Transformer(backendCtx).ToCairo()
            self._ctx = cairoImg
        self._mainClock.tick(self._framerate)
            
        wx.CallAfter(self._screen.Refresh)
    
    def ProcessAbort(self):
        wx.CallAfter(self._screen.Destroy)

    def Prepare(self):
        self._screen.SetClientSizeWH(*self.GetProfile().GetResolution())
        
        self._framerate = self._GetFrameRate()
        self._mainClock.reset()
        
    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self._screen)
#        dc.SetBackground(wx.Brush('black'))
#        dc.Clear()

        if self._ctx:
            w = self._ctx.get_width()
            h = self._ctx.get_height()
            data = self._ctx.get_data()
            wxbmp = wx.BitmapFromBufferRGBA(w, h, data)        
            dc.DrawBitmap(wxbmp, 0, 0)

#        if self._ctx:
#            ctx = wx.lib.wxcairo.ContextFromDC(dc)
#            ctx.set_source_surface(self._ctx, 0, 0)
#            ctx.paint()            
        event.Skip()
        
    def Finalize(self):
        wx.CallAfter(self._screen.Destroy)
        
    def EnsureFramerate(self):
        if get_fps(self._mainClock, self._framerate):
            return True
        else:
            return False
        
#    def CropAndResize(self, ctx, rect):
#        if self._mainClock.get_fps() > 1 and self._mainClock.get_fps() < self._framerate:
#            if self._ctx is not None:
#                return None
#        
#        return BaseRenderer.CropAndResize(self, ctx, rect)
#        
#    def Transition(self, kind, ctx1, ctx2, percentage):
#        if ctx1 is None or ctx2 is None:
#            return None
#        if self._mainClock.get_fps() > 1 and self._mainClock.get_fps() < self._framerate:
#            if self._ctx is not None:
#                return None
#        
#        return BaseRenderer.Transition(self, kind, ctx1, ctx2, percentage)
        

class Clock(object):
    def __init__(self):
        self.fps = 0.0
        self.fps_count = 0
        self.start = 0
        
    def reset(self):
        self.start = time.time()
    
    def tick(self, framerate):
        nowtime = time.time()
        self.fps_count += 1
        
        timepassed = nowtime - self.start
        
        self.fps = 1.0 / (timepassed / self.fps_count)
        
        endtime = (1.0 / framerate) * self.fps_count
        delay = endtime - timepassed
        if delay < 0:
            delay = 0
        time.sleep(delay)
    
    def get_fps(self):
        return self.fps


def get_fps(clock, value):
    fps = clock.get_fps()
    tol = 0.1
#    print fps, abs(fps - value), abs(fps * tol)
    return not (fps > 1 and abs(fps - value) <= abs(fps * tol))
