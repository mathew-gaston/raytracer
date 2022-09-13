from math import cos, sin, sqrt

from pygame.math import Vector3


def flatten(L):
    return [item for sublist in L for item in sublist]


class Ray(object):

    def __init__(self, pos, dir):
        self.pos = pos
        self.dir = dir.normalize()

    def get_point(self, t):
        return self.pos + t * self.dir


class RayIntersection(object):

    def __init__(self, ray, object, pos, normal, t):
        self.ray = ray
        self.object = object
        self.pos = pos
        self.normal = normal.normalize()
        self.t = t

    def __lt__(self, other):
        return self.t < other.t


class Plane(object):

    def __init__(self, matl, pos, normal):
        self.matl = matl
        self.pos = pos
        self.normal = normal.normalize()
        self.d = pos.dot(self.normal)

    def ray_test(self, ray):
        if self.normal.dot(ray.dir) == 0:
            # Ray is parallel to plane
            return []
        t = (self.d - ray.pos.dot(self.normal)) / self.normal.dot(ray.dir)
        if t > 0:
            return [RayIntersection(
                ray, self, ray.get_point(t), self.normal, t
            )]
        return []


class Sphere(object):

    def __init__(self, matl, pos, radius):
        self.matl = matl
        self.pos = pos
        self.radius = radius
        self.radius2 = radius ** 2

    def ray_test(self, ray):
        # The vector from the ray's origin to the sphere's center
        L = self.pos - ray.pos
        # The magnitude of the component of L parallel to the ray
        tca = L.dot(ray.dir)
        if tca < 0:
            return []
        # The magnitude (squared) of the component of L perpendicular
        # to the ray
        d2 = L.magnitude_squared() - tca ** 2
        if d2 > self.radius2:
            return []
        # The distance along the ray from the first collision point to
        # the perpendicular component of L
        thc = sqrt(self.radius2 - d2)
        t0 = tca - thc
        t1 = tca + thc
        if t0 > t1:
            t0, t1 = t1, t0
        if t0 < 0:
            # If t0 is negative, use t1 instead
            t0 = t1
            if t0 < 0:
                # Both t0 and t1 are negative
                return []
        point = ray.get_point(t0)
        return [RayIntersection(
            ray, self, point, (point - self.pos).normalize(), t0
        )]


class Box(object):

    def __init__(self, matl, pos, extents):
        self.matl = matl
        self.pos = pos
        self.extents = extents
        self.axes = [
            Vector3(1.0, 0.0, 0.0),
            Vector3(0.0, 1.0, 0.0),
            Vector3(0.0, 0.0, 1.0)
        ]

    def ray_test(self, ray):
        hits = []
        # Perform this test on all 3 axes, in both the + and - direction
        for axis, extent in zip(self.axes, self.extents):
            d0, d1 = (
                (self.pos - extent * axis).dot(-axis),
                (self.pos + extent * axis).dot(axis)
            )
            for normal, d in ((-axis, d0), (axis, d1)):
                try:
                    t = (d - ray.pos.dot(normal)) / ray.dir.dot(normal)
                except ZeroDivisionError:
                    # Ray is parallel to this side of the box
                    continue
                if t >= 0:
                    p = ray.get_point(t)
                    # The local coordinates of the intersection point
                    # TODO: Store this in RayIntersection.misc_data?
                    lp = self.pos - p
                    ex, ey, ez = (
                        self.extents[0], self.extents[1], self.extents[2]
                    )
                    if (-ex - 0.0001 < lp.dot(self.axes[0]) < ex + 0.0001 and
                        -ey - 0.0001 < lp.dot(self.axes[1]) < ey + 0.0001 and
                        -ez - 0.0001 < lp.dot(self.axes[2]) < ez + 0.0001):
                        hits.append(RayIntersection(ray, self, p, normal, t))
        return hits

    def rotate_x(self, radians):
        c, s = cos(radians), sin(radians)
        for i, axis in enumerate(self.axes):
            self.axes[i] = Vector3(
                axis.x,
                axis.y * c - axis.z * s,
                axis.y * s + axis.z * c
            )

    def rotate_y(self, radians):
        c, s = cos(radians), sin(radians)
        for i, axis in enumerate(self.axes):
            self.axes[i] = Vector3(
                axis.x * c + axis.z * s,
                axis.y,
                -axis.x * s + axis.z * c
            )

    def rotate_z(self, radians):
        c, s = cos(radians), sin(radians)
        for i, axis in enumerate(self.axes):
            self.axes[i] = Vector3(
                axis.x * c - axis.y * s,
                axis.x * s + axis.y * c,
                axis.z
            )


class Triangle(object):

    def __init__(self, matl, a, b, c):
        self.matl = matl
        self.a = a
        self.b = b
        self.c = c

    def ray_test(self, ray):
        ab = self.b - self.a
        ac = self.c - self.a
        normal = ab.cross(ac).normalize()
        dp = normal.dot(ray.dir)
        if dp == 0:
            # Ray is parallel to triangle
            return []
        t = (normal.dot(self.a) - ray.pos.dot(normal)) / dp
        if t < 0:
            return []
        p = ray.get_point(t)
        ap = p - self.a
        area_abc = ab.cross(ac).magnitude() / 2
        area_abp = ab.cross(ap).magnitude() / 2
        area_apc = ap.cross(ac).magnitude() / 2
        area_pbc = (self.b - p).cross(self.c - p).magnitude() / 2
        # Compensate for floating point error
        if (area_abp + area_apc + area_pbc) / area_abc <= 1.0001:
            return [RayIntersection(ray, self, p, normal, t)]
        return []


class TriangleMesh(object):

    def __init__(self, matl, offset, filename):
        self.matl = matl
        verts = []
        self.tris = []
        min_vert = None
        max_vert = None
        with open(filename, 'r') as fp:
            for line in fp:
                line = line.strip()
                if line.startswith('v'):  # Vertex
                    new_vert = Vector3(*(
                        float(val) + offset[i]
                        for i, val
                        in enumerate(line.split(' ')[1:])
                    ))
                    verts.append(new_vert)
                    if min_vert is None:
                        # Make copies of the first vertex
                        min_vert = Vector3(new_vert)
                        max_vert = Vector3(new_vert)
                    else:
                        # Ugly, but more efficient than using min()
                        if new_vert.x < min_vert.x: min_vert.x = new_vert.x
                        if new_vert.y < min_vert.y: min_vert.y = new_vert.y
                        if new_vert.z < min_vert.z: min_vert.z = new_vert.z
                        if new_vert.x > max_vert.x: max_vert.x = new_vert.x
                        if new_vert.y > max_vert.y: max_vert.y = new_vert.y
                        if new_vert.z > max_vert.z: max_vert.z = new_vert.z
                elif line.startswith('f'):  # Face
                    i0, i1, i2 = (int(val) - 1 for val in line.split(' ')[1:])
                    self.tris.append(Triangle(
                        matl,
                        verts[i0],
                        verts[i1],
                        verts[i2]
                    ))
        self.box = Box(
            matl, (min_vert + max_vert) / 2, (max_vert - min_vert) / 2
        )

    def ray_test(self, ray):
        if not self.box.ray_test(ray):
            return []
        return flatten([tri.ray_test(ray) for tri in self.tris])

    @property
    def pos(self):
        return self.box.pos
