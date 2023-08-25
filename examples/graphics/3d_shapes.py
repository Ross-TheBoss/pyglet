import pyglet
from pyglet import shapes
from pyglet.math import Mat4, Vec3
from pyglet.window import key

window = pyglet.window.Window()
keyboard = pyglet.window.key.KeyStateHandler()
window.push_handlers(keyboard)
view_position = Vec3(10, 0, 10)
batch = pyglet.graphics.Batch()

backdrop = shapes.Cuboid(x=-2, y=-2, z=-4, width=5, height=5, depth=0, color=(128, 0, 0), batch=batch)

cube = shapes.Cuboid(x=0, y=0, z=0, width=2, height=3, depth=5, color=(0, 0, 255), batch=batch)
cube.opacity = 200
cube.anchor_x = cube.width / 2
cube.anchor_y = cube.height / 2
cube.anchor_z = cube.depth / 2

@window.event
def on_resize(width, height):
    window.viewport = (0, 0, *window.get_framebuffer_size())

    window.projection = Mat4.perspective_projection(window.aspect_ratio, z_near=0.1, z_far=255)
    return pyglet.event.EVENT_HANDLED


@window.event
def on_draw():
    window.clear()
    batch.draw()


@window.event
def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
    if dx > 0:
        cube.pitch -= 1
    elif dx < 0:
        cube.pitch += 1

    if dy > 0:
        cube.yaw -= 1
    elif dy < 0:
        cube.yaw += 1


def update(dt):
    if keyboard[key.LEFT]:
        cube.x -= 0.1
    elif keyboard[key.RIGHT]:
        cube.x += 0.1
    elif keyboard[key.DOWN]:
        if keyboard[key.RSHIFT] or keyboard[key.LSHIFT]:
            cube.z += 0.1
        else:
            cube.y -= 0.1
    elif keyboard[key.UP]:
        if keyboard[key.RSHIFT] or keyboard[key.LSHIFT]:
            cube.z -= 0.1
        else:
            cube.y += 0.1


window.view = Mat4.look_at(position=view_position, target=Vec3(0, 0, 0), up=Vec3(0, 1, 0))
pyglet.clock.schedule_interval(update, 1/60)

pyglet.app.run()