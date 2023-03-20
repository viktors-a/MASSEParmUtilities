import hou

slots = ("n", "s", "e", "w", "ne", "se", "nw", "sw")


def change_view(change_to):
    try:
        cur_view = hou.ui.paneTabUnderCursor().curViewport()
        view_obj = getattr(hou.geometryViewportType, change_to)
        cur_view.changeType(view_obj)
    except:
        pass


def select_camera(kwargs):
    try:
        pane = kwargs["pane"]
        cur_view = pane.curViewport()
        viewport_path = [pane.pwd().path()]
        # split at / and clean up empty strings entries
        root_path_list = [x for x in viewport_path[0].split("/") if x]
        # if root_path_list exists get first element
        if root_path_list:
            viewport_path.append(root_path_list[0])
        cameras = []
        for path in viewport_path:
            all_nodes = hou.node(path).allNodes()
            for node in all_nodes:
                if node.type().name() == "cam" and node not in cameras:
                    cameras.append(node)
        if cameras:
            # Build a menu from the most recent lights
            menu = {}
            for slot, camera in zip(slots, cameras[:8]):
                menu[slot] = {
                    "type": "script_action",
                    "label": camera.name(),
                    "icon": camera.type().icon(),
                    "script": lambda c=camera, **kwargs: cur_view.settings().setCamera(
                        c)
                }
            return menu
    except:
        pass
    return None
