import hou

slots = ("n", "s", "e", "w", "ne", "se", "nw", "sw")


def change_view(change_to):
    cur_view = hou.ui.paneTabUnderCursor().curViewport()
    view_obj = getattr(hou.geometryViewportType, change_to)
    cur_view.changeType(view_obj)


def select_camera(kwargs):
    pane = kwargs["pane"]
    viewport_path = pane.pwd().path()
    cameras = [node for node in hou.node(viewport_path).allNodes() if node.type().name() == "cam"]
    if cameras:
        # Build a menu from the most recent lights
        menu = {}
        for slot, camera in zip(slots, cameras[:8]):
            menu[slot] = {
                "type": "script_action",
                "label": camera.name(),
                "icon": camera.type().icon(),
                "script": lambda c = camera, **kwargs: pane.curViewport().settings().setCamera(c)
            }
        return menu
    return None
