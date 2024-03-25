""" Assortment of useful functions"""
import hou


# function called on a spare button in a group node, for custom bbox size based on viewport selection.
def get_viewport_selection_bbox(kwargs):
    scane_viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
    parent_node = kwargs["node"]
    if scane_viewer:
        geo_selection = scane_viewer.currentGeometrySelection()
        if geo_selection:
            selected_nodes = geo_selection.nodes()
            # make sure that selection is only from node that calls this function
            if len(selected_nodes) == 1:
                if parent_node == selected_nodes[0]:
                    selection_bbox = geo_selection.boundingBox()
                    size_parms = parent_node.parmTuple("size")
                    scale_parms = parent_node.parmTuple("bbox_multiplier")
                    bbox_sizes = selection_bbox.sizevec()
                    # set multiplier and bbox size
                    if size_parms and scale_parms:
                        for size_parm, scale_parm, bbox_size in zip(size_parms, scale_parms, bbox_sizes):
                            size_parm.set(bbox_size * scale_parm.eval())
                        # set center
                        parent_node.parmTuple("t").set(selection_bbox.center())
            else:
                parent_node.parm("initbounds").pressButton()

# get volume atribute values, used for caching and loading landscape files
def generateVolumeMenu(geometry, attib_name="name") -> list:
    volume_menu = []
    if geometry:
        for geo in geometry.prims():
            if geo.type() == hou.primType.Volume:
                volume_name = geo.stringAttribValue(attib_name)
                if volume_name and volume_name not in volume_menu:
                    volume_menu.append(volume_name)
                    volume_menu.append(volume_name)
    return volume_menu
