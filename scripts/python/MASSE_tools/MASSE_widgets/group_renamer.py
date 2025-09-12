"""
Author: Viktors Anfimovs
Email: houdinielement@gmail.com
"""
import os
import hou
from PySide6.QtCore import QFile
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QScrollArea, QLabel,\
    QHBoxLayout, QLineEdit, QComboBox
from PySide6.QtUiTools import QUiLoader


class HoudiniError(Exception):
    """Display message in houdini"""


ui_file_path = os.path.join(os.path.dirname(__file__), "ui/group_renamer.ui")


class masseCreateRenamerUI:
    def __init__(self):
        # setup instance attributes thaw will be filled only when nodes are generated
        self.node = None
        self.geometry = None
        self.groups = None
        self.scene_viewer = None
        self.network_viewer = None
        self.current_group_type = None
        self.groups = None
        self.viewport = None
        # import ui file
        super().__init__()
        loader = QUiLoader()
        ui_file = QFile(ui_file_path)
        ui_file.open(QFile.ReadOnly)
        self.the_main_widget = loader.load(ui_file)
        # get interactable widgets
        self.group_type_select = self.the_main_widget.findChildren(QComboBox, "typeSelectBox")[0]
        self.generate_entries = self.the_main_widget.findChildren(QPushButton, "generateEntries")[0]
        self.scroll_area = self.the_main_widget.findChildren(QScrollArea, "scrollArea")[0]
        self.rename_button = self.the_main_widget.findChildren(QPushButton, "renameButton")[0]
        self.current_node_label = self.the_main_widget.findChildren(QLabel, "currentNodeButton")[0]
        self.shading_mode = None

        def group_vertical_layout():
            # get current viewport
            try:
                self.scene_viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
            except AttributeError:
                raise HoudiniError("Viewpoint not found")
            # get node
            nodes = hou.selectedNodes()
            if len(nodes) == 1:
                if isinstance(nodes[0], hou.SopNode):
                    self.node = nodes[0]
                    self.geometry = self.node.geometry()
                else:
                    raise HoudiniError("Make sure single Sop node selected")
            else:
                raise HoudiniError("Make sure one node is selected in Network editor")
            # get group type
            self.current_group_type = self.group_type_select.currentText()
            # get list of current geometry groups of selected group type
            self.groups = [prim_group for prim_group in getattr(self.geometry,
                                                                       f"{self.current_group_type}Groups")()]
            if self.groups:
                # set current node label
                self.current_node_label.setText(f"CURRENT NODE: {self.node.path()}")
                # call screenshot methode
                root_screensot_path = self.get_screenshot_path()
                # setup for geometry selection methode
                geo_type_dict = {"prim": hou.geometryType.Primitives, "edge": hou.geometryType.Edges,
                                  "point": hou.geometryType.Points, "vertex": hou.geometryType.Vertices}
                geo_type = geo_type_dict[self.current_group_type]
                # make sure gemomety selection type is same as group type
                self.scene_viewer.setSelectionMode(hou.selectionMode.Geometry)
                self.scene_viewer.setPickGeometryType(geo_type)
                # # get current viewport and frame group geometry
                bbox = self.geometry.boundingBox()
                self.viewport = self.scene_viewer.curViewport()
                self.viewport.frameBoundingBox(bbox)
                # set shading mode basedo on user preference
                self.shading_mode = self.the_main_widget.findChildren(QComboBox, "shadingModeComboBox")[0]
                sel_object_shading = self.viewport.settings().displaySet(hou.displaySetType.DisplayModel)
                current_shading_mode = sel_object_shading.shadedMode()
                if self.shading_mode.currentIndex() == 0:
                    sel_object_shading.setShadedMode(hou.glShadingType.WireGhost)
                #  make sure node has display flag in
                self.node.setGenericFlag(hou.nodeFlag.Display, 1)
                # modify universal flipbook settings
                flipbook_settings = self.scene_viewer.flipbookSettings()
                flipbook_settings_copy = flipbook_settings.stash()
                flipbook_settings_copy.resolution((256, 256))
                flipbook_settings_copy.outputToMPlay(False)
                flipbook_settings_copy.frameRange((1, 1))
                if self.current_group_type in ["prim", "edge"]:
                    flipbook_settings_copy.beautyPassOnly(True)
                else:
                    flipbook_settings_copy.beautyPassOnly(False)
                # camera setup
                # check if camera already exist if not create one
                camera = [node for node in hou.node("/obj").children() if node.type().name() == "cam" and
                           node.comment() == "MASSE_screenshot_camera"]
                if camera:
                    camera = camera[0]
                if not camera:
                    camera = hou.node("/obj").createNode("cam", "MASSE_screenshot_camera")
                    camera.setComment("MASSE_screenshot_camera")
                    camera.parmTuple("res").set((256, 256))
                # lock camera to viewport
                self.viewport.setCamera(camera)
                self.viewport.lockCameraToView(camera)
                # widgets that will hold looped groups
                group_verical_layout = QVBoxLayout()
                group_vertical_widget = QWidget()
                for group in self.groups:
                    group_name = group.name()
                    group_contents = None
                    group_horizontal_layout = QHBoxLayout()
                    group_horizontal_widget = QWidget()
                    if self.current_group_type == "edge":
                        group_contents = group.edges()
                    if self.current_group_type == "point":
                        group_contents = group.points()
                    if self.current_group_type == "prim":
                        group_contents = group.prims()
                    if self.current_group_type == "vertex":
                        group_contents = group.vertices()
                    # selct group in a viewport before taking a screenshot
                    self.scene_viewer.setSelectionMode(hou.selectionMode.Geometry)
                    self.scene_viewer.setPickGeometryType(geo_type)
                    selection = hou.Selection(group_contents)
                    self.scene_viewer.setCurrentGeometrySelection(geo_type, (self.node,), (selection,))
                    # move camera to framed selection
                    self.viewport.frameSelected()
                    self.viewport.saveViewToCamera(camera)
                    # flipbook setup for each group
                    screenshot_path = f"{root_screensot_path}\\{group_name}.png"
                    flipbook_settings_copy.output(screenshot_path)
                    self.scene_viewer.flipbook(settings=flipbook_settings_copy)
                    # add screenshot widget
                    new_label = QLabel(group.name())
                    pix_map = QPixmap(screenshot_path)
                    new_label.setPixmap(pix_map)
                    group_horizontal_layout.addWidget(new_label)
                    # add group name widget
                    group_name_widget = QLabel(group_name)
                    group_horizontal_layout.addWidget(group_name_widget)
                    # add line edit
                    group_new_name_widget = QLineEdit()
                    group_horizontal_layout.addWidget(group_new_name_widget)
                    group_horizontal_widget.setLayout(group_horizontal_layout)
                    group_verical_layout.addWidget(group_horizontal_widget)
                # set widgets
                group_vertical_widget.setLayout(group_verical_layout)
                self.scroll_area.setWidget(group_vertical_widget)
                # unlock the camera
                self.viewport.lockCameraToView(False)
                sel_object_shading.setShadedMode(current_shading_mode)

        # generate entries when button is pressed]
        def rename_groups():
            old_names = [name.text() for name in self.scroll_area.findChildren(QLabel) if name.text()]
            new_names = [name.text() for name in self.scroll_area.findChildren(QLineEdit) if name.text()]
            rename_dict = {}
            for old, new in zip(old_names, new_names):
                if new:
                    rename_dict[old] = new

            if rename_dict:
                rename_node = None
                rename_outputs = [node for node in self.node.outputs() if node.type().name() == "grouprename"]
                if rename_outputs:
                    rename_node = rename_outputs[0]
                else:
                    rename_node = self.node.parent().createNode("grouprename", "MASSE_group_renamer",
                                                                force_valid_node_name=True)
                    rename_node.setInput(0, self.node)
                    rename_node.moveToGoodPosition()
                # put rename node a visability flag and make it a current node
                rename_node.setGenericFlag(hou.nodeFlag.Display, 1)
                self.network_viewer = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
                if self.network_viewer:
                    self.network_viewer.setCurrentNode(rename_node)
                # reset get mulriparm counter parm and reset that counter
                rename_parm = rename_node.parm("renames")
                rename_parm.set(0)

                for rename in rename_dict:
                    new_group_name = rename_dict[rename]
                    multiparm_index = rename_parm.evalAsInt()
                    rename_parm.insertMultiParmInstance(multiparm_index)
                    rename_node.parm("".join(("group", str(multiparm_index+1)))).set(rename)
                    rename_node.parm("".join(("newname", str(multiparm_index+1)))).set(new_group_name)

        self.generate_entries.clicked.connect(group_vertical_layout)
        self.rename_button.clicked.connect(rename_groups)

    @staticmethod
    def get_screenshot_path():
        temp_folder = "".join((hou.getenv("TEMP"), "\\houdini_temp\\masse_viewport_screenshots"))
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)
        files = ["\\".join((temp_folder, file_name)) for file_name in os.listdir(temp_folder)]
        if files:
            [os.remove(file) for file in files]
        return temp_folder
