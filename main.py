#!/usr/bin/env python3
from math import radians
from time import time

import pygame as pg
from pygame.math import Vector3

import config
from camera import Camera
from objects3d import *


def clamp_vec3(v, lo=0.0, hi=1.0):
    return Vector3(
        max(lo, min(v.x, hi)),
        max(lo, min(v.y, hi)),
        max(lo, min(v.z, hi))
    )


def hadamard(v, w):
    return v.elementwise() * w


def draw_pixel(surface, px, py, camera, objects, lights):
    # This ray starts at the camera's position and passes through the
    # given pixel on the virtual view plane
    ray = Ray(camera.pos, (camera.get_pixel_pos_3d(px, py) - camera.pos))

    # Test the ray against all objects in the scene
    hits = []
    for object in objects:
        hits += object.ray_test(ray)

    # If the ray hits something, compute the color of the pixel at
    # (px, py) using the Phong reflection model
    if hits:
        closest = min(hits)
        lit_color = hadamard(
            config.AMBIENT_LIGHT_COLOR,
            closest.object.matl['ambi']
        )
        for light in lights:
            # Get the normalized vector from the intersection point to
            # the current light source
            to_light = light['pos'] - closest.pos
            light_dir = (to_light).normalize()

            # Strength of diffuse illumination is based on the angle
            # of incidence (the angle between the above vector and the
            # surface normal at the intersection point)
            diff_strength = light_dir.dot(closest.normal)
            if diff_strength > 0:
                diff_color = diff_strength * hadamard(
                    light['diff'],
                    closest.object.matl['diff']
                )
            else:
                diff_color = Vector3()

            # Compute specular illumination for the current light source
            reflect_dir = 2 * diff_strength * closest.normal - light_dir
            camera_dir = (camera.pos - closest.pos).normalize()
            spec_strength = camera_dir.dot(reflect_dir)
            if spec_strength > 0:
                spec_color = (
                    spec_strength ** closest.object.matl['hard']
                    * hadamard(light['spec'], closest.object.matl['spec'])
                )
            else:
                spec_color = Vector3()

            # Determine whether intersection point is in shadow
            shadow_ray = Ray(closest.pos + 0.0001 * closest.normal, light_dir)
            in_shadow = False
            for object in objects:
                hits = object.ray_test(shadow_ray)
                if hits:
                    # We need only test the intersection point with the
                    # smallest t value; if it fails the test then those
                    # with larger t values will necessarily also fail
                    closest = min(hits)
                    if closest.t ** 2 < to_light.magnitude_squared():
                        in_shadow = True
                        # Once we know the point is in shadow, we can
                        # ignore the other objects in the scene
                        break
            if not in_shadow:
                lit_color += diff_color + spec_color

        # Finally, set the given pixel's color
        surface.set_at((px, py), clamp_vec3(lit_color) * 255)
    else:
        # If no objects were hit, set pixel to background color
        surface.set_at((px, py), (128, 128, 128))


def draw_scene(surface, camera, objects, lights):
    for y in range(config.SCREEN_HEIGHT):
        for x in range(config.SCREEN_WIDTH):
            draw_pixel(surface, x, y, camera, objects, lights)
            # Check for user input
            process_events()
        # Update the display after rendering each row
        pg.display.flip()


def process_events():
    for event in pg.event.get():
        if event.type == pg.QUIT:
            pg.quit
            raise SystemExit
        elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
            pg.quit()
            raise SystemExit


def main():
    # Pygame setup
    pg.init()
    screen = pg.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pg.display.set_caption('Pygame Raytracer')

    cam = Camera(
        pos=Vector3(-15.0, 19.0, -30.0),
        coi=Vector3(2.0, 5.0, 3.0),
        up=Vector3(0.0, 1.0, 0.0),
        fov=60.0,
        near=1.5
    )

    matls = {
        'red': {
            'ambi': Vector3(0.3, 0.0, 0.0),
            'diff': Vector3(1.0, 0.0, 0.0),
            'spec': Vector3(1.0, 1.0, 1.0),
            'hard': 10.0
        },
        'green': {
            'ambi': Vector3(0.0, 0.5, 0.0),
            'diff': Vector3(0.0, 1.0, 0.0),
            'spec': Vector3(1.0, 0.0, 0.0),
            'hard': 2.0
        },
        'blue': {
            'ambi': Vector3(0.0, 0.0, 0.1),
            'diff': Vector3(0.0, 0.0, 1.0),
            'spec': Vector3(1.0, 0.0, 1.0),
            'hard': 6.0
        },
        'yellow': {
            'ambi': Vector3(0.5, 0.3, 0.1),
            'diff': Vector3(1.0, 1.0, 0.0),
            'spec': Vector3(0.5, 1.0, 0.5),
            'hard': 30.0
        },
        'purple': {
            'ambi': Vector3(0.2, 0.0, 0.4),
            'diff': Vector3(0.7, 0.0, 0.1),
            'spec': Vector3(1.0, 1.0, 1.0),
            'hard': 50.0
        }
    }

    objects = [
        Plane(
            matls['green'], Vector3(0.0, 5.0, 0.0), Vector3(0.0, 1.0, 0.0)
        ),
        Plane(
            matls['blue'], Vector3(0.0, 4.0, 0.0), Vector3(0.1, 1.0, 0.0)
        ),
        Sphere(matls['red'], Vector3(2, 8, 5), 7),
        box := Box(
            matls['yellow'],
            Vector3(15.0, 12.0, -5.0),
            Vector3(9.0, 5.0, 2.0)
        ),
        TriangleMesh(matls['purple'], Vector3(-10, 22, 0), 'tri.obj')
    ]

    box.rotate_z(radians(45))
    box.rotate_x(radians(15))

    lights = [
        {
            'pos': Vector3(0.0, 50.0, 0.0),
            'diff': Vector3(1.0, 1.0, 1.0),
            'spec': Vector3(1.0, 1.0, 1.0)
        },
        {
            'pos': Vector3(50.0, 50.0, -50.0),
            'diff': Vector3(0.3, 0.0, 0.0),
            'spec': Vector3(0.0, 0.6, 0.0)
        }
    ]

    print('Rendering...', end='', flush=True)

    t0 = time()
    draw_scene(screen, cam, objects, lights)
    t1 = time()

    print(f'Done in {round(t1 - t0, 2)} seconds.')

    pg.image.save(screen, 'out.png')

    # Keep the window open until the user quits
    while True:
        process_events()


if __name__ == '__main__':
    main()
