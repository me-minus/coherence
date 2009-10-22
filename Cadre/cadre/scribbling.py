# Licensed under the MIT license
# http://opensource.org/licenses/mit-license.php

# Copyright 2009 Frank Scholz <coherence@beebits.net>

import os

# Twisted
from twisted.internet import reactor

from coherence import log

import pango

# Clutter
import clutter
from clutter import cogl

class TextureReflection (clutter.Clone):
    # taken from the reflection.py example of pyclutter

    """
    TextureReflection (clutter.Clone)

    An actor that paints a reflection of a texture. The
    height of the reflection can be set in pixels. If set
    to a negative value, the same size of the parent texture
    will be used.

    The size of the TextureReflection actor is by default
    the same size of the parent texture.
    """
    __gtype_name__ = 'TextureReflection'

    def __init__ (self, parent):
        clutter.Clone.__init__(self, parent)
        self._reflection_height = -1

    def set_reflection_height (self, height):
        self._reflection_height = height
        self.queue_redraw()

    def get_reflection_height (self):
        return self._reflection_height

    def do_paint (self):
        parent = self.get_source()
        if (parent is None):
            return

        # get the cogl handle for the parent texture
        cogl_tex = parent.get_cogl_texture()
        if not cogl_tex:
            return

        (width, height) = self.get_size()

        # clamp the reflection height if needed
        r_height = self._reflection_height
        if (r_height < 0 or r_height > height):
            r_height = height

        rty = float(r_height / height)

        opacity = self.get_paint_opacity()

        # the vertices are a 6-tuple composed of:
        #  x, y, z: coordinates inside Clutter modelview
        #  tx, ty: texture coordinates
        #  color: a clutter.Color for the vertex
        #
        # to paint the reflection of the parent texture we paint
        # the texture using four vertices in clockwise order, with
        # the upper left and the upper right at full opacity and
        # the lower right and lower left and 0 opacity; OpenGL will
        # do the gradient for us
        color1 = cogl.color_premultiply((1, 1, 1, opacity/255.))
        color2 = cogl.color_premultiply((1, 1, 1, 0))
        vertices = ( \
            (    0,        0, 0, 0.0, 1.0,   color1), \
            (width,        0, 0, 1.0, 1.0,   color1), \
            (width, r_height, 0, 1.0, 1.0-rty, color2), \
            (    0, r_height, 0, 0.0, 1.0-rty, color2), \
        )

        cogl.push_matrix()

        cogl.set_source_texture(cogl_tex)
        cogl.polygon(vertices=vertices, use_color=True)

        cogl.pop_matrix()


class Canvas(log.Loggable):

    logCategory = 'canvas'

    def __init__(self, fullscreen=1):
        self.fullscreen = fullscreen
        self.stage = clutter.Stage()
        if self.fullscreen == 1:
            self.stage.set_fullscreen(True)
        else:
            self.stage.set_size(1200, 800)

        size = self.stage.get_size()
        print "%r" % (size,)

        display_width = size[0]*0.7
        display_height = size[1]*0.7

        self.stage.set_color(clutter.Color(0,0,0))
        if self.fullscreen == 1:
            self.stage.connect('button-press-event', lambda x,y: reactor.stop())
        self.stage.connect('destroy', lambda x: reactor.stop())

        group = clutter.Group()
        self.stage.add(group)

        self.texture = clutter.Texture()
        self.texture.set_keep_aspect_ratio(True)
        self.texture.set_size(display_width,display_height)

        reflect = TextureReflection(self.texture)
        reflect.set_reflection_height(display_height/3)
        reflect.set_opacity(100)

        x_pos = float((self.stage.get_width() - self.texture.get_width()) / 2)

        group.add(self.texture, reflect)
        group.set_position(x_pos, 20.0)
        reflect.set_position(0.0, (self.texture.get_height() + 20))

        self.stage.show()

    def set_title(self,title):
        self.stage.set_title(title)

    def add_overlay(self,overlay):
        screen_width,screen_height = self.stage.get_size()
        texture = clutter.Texture()
        texture.set_keep_aspect_ratio(True)
        texture.set_size(int(overlay['width']),int(overlay['height']))
        print overlay['url']
        texture.set_from_file(filename=overlay['url'])

        def get_position(item_position,item_width):
            p = float(str(item_position))
            try:
                orientation = item_position['orientation']
            except:
                orientation = 'left'
            try:
                unit = item_position['unit']
            except:
                unit = 'px'
            if unit in ['%']:
                p = screen_width * (p/100.0)
            else:
                position = int(p)

            if orientation == 'right':
                p -= int(item_width)

            return p

        position_x = get_position(overlay['position_x'],overlay['width'])
        position_y = get_position(overlay['position_y'],overlay['width'])
        print position_x, position_y
        texture.set_position(position_x, position_y)
        self.stage.add(texture)

    def show_image(self,image,title=''):
        #FIXME - we have the image as data already, there has to be
        #        a better way to get it into the texture
        self.warning("show image %r" % title)
        if image.startswith("file://"):
            filename = image[7:]
        else:
            from tempfile import mkstemp
            fp,filename = mkstemp()
            os.write(fp,image)
            os.close(fp)
            remove_file_after_loading = True
        #self.texture.set_load_async(True)
        self.warning("loading image from file %r" % filename)
        self.texture.set_from_file(filename=filename)
        self.set_title(title)
        try:
            if remove_file_after_loading:
                os.unlink(filename)
        except:
            pass