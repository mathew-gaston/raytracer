from math import radians, tan

import config


class Camera(object):

    def __init__(self, pos, coi, up, fov, near):
        self.pos = pos
        self.z_axis = (coi - pos).normalize()
        self.x_axis = up.cross(self.z_axis).normalize()
        self.y_axis = self.z_axis.cross(self.x_axis)
        self.view_height = 2 * near * tan(0.5 * radians(fov))
        self.view_width = config.ASPECT_RATIO * self.view_height
        self.view_origin = (
            pos
            - (self.x_axis * 0.5 * self.view_width)
            + (self.y_axis * 0.5 * self.view_height)
            + (self.z_axis * near)
        )

    def get_pixel_pos_3d(self, px, py):
        perc_x = px / (config.SCREEN_WIDTH - 1)
        perc_y = py / (config.SCREEN_HEIGHT - 1)
        return (
            self.view_origin
            + (self.x_axis * self.view_width * perc_x)
            - (self.y_axis * self.view_height * perc_y)
        )
