"""Module for retirving geometry attributes/groups on nodes that can reference them, like group/attribute rename"""
import hou
import re
from . import pyperclip
from collections import defaultdict
from .parm_utils import HoudiniError

attrib_strings = ["point", "prim", "vertex", "global"]
group_strings = ["point", "prim", "edge", "vertex"]


class AttribGroupUtils:
    def __init__(self, node):
        self.node = node
        self.template_group = self.node.parmTemplateGroup()
        self.geo = None
        self.read_from_node = None

    def get_groups_and_attribs(self) -> dict:
        """returns dict of ether attibs or groups of the geometry"""
        # get node to read groups/attribs from
        get_from_index = self.node.parm("MASSE_input_index")
        if get_from_index:
            node_geo_list = list(self.node.inputs())
            node_geo_list.insert(0, self.node)
            node_geo_dict = {index - 1: node for index, node in enumerate(node_geo_list) if node}
            if isinstance(self.node, hou.SopNode):
                try:
                    if get_from_index.eval() == 5:
                        custom_path = self.node.parm("MASSE_custom_path").eval()
                        if hou.node(custom_path):
                            self.geo = hou.node(custom_path).geometry()
                        else:
                            # find any spare input parms
                            re_spare_input = re.compile(r"spare_input(?P<index>\d+)")
                            spare_input_dict = {}
                            for parm in self.node.spareParms():
                                # get match object
                                match = re_spare_input.match(parm.name())
                                if match:
                                    parm_index = match.group("index")
                                    parm_key = str(0 - (int(parm_index)+1))
                                    # check if parm point to node
                                    has_node = self.node.node(parm.eval())
                                    if has_node:
                                        node_geo = has_node.geometry()
                                        if node_geo:
                                            spare_input_dict[parm_key] = node_geo
                            # eval custom path parm
                            custom_path_parm_val = self.node.parm("MASSE_custom_path").eval()
                            if custom_path_parm_val in spare_input_dict:
                                self.geo = spare_input_dict[custom_path_parm_val]
                    else:
                        self.geo = node_geo_dict[get_from_index.eval()-1].geometry()
                except KeyError:
                    HoudiniError("No geometry found")
                if self.geo:
                    return_dict = defaultdict(list)
                    for attrib_type in attrib_strings:
                        for attrib in getattr(self.geo, f"{attrib_type}Attribs")():
                            attrib_name = attrib.name()
                            attib_is_array = attrib.isArrayType()
                            is_array = ""
                            if attib_is_array:
                                is_array = " array"
                            attrib_data_type = attrib.dataType().name()
                            attrib_label = f"{attrib_name}({attrib_data_type}{is_array})"
                            return_dict[f"attrib_{attrib_type}"].append([attrib_name, attrib_label])
                    for group_type in group_strings:
                        for group_str in getattr(self.geo, f"{group_type}Groups")():
                            group_name = group_str.name()
                            return_dict[f"group_{group_type}"].append([group_name, group_name])
                    return dict(return_dict)
                else:
                    raise HoudiniError("No node detected")

    def create_strip_buttons(self, content_dict):
        """create spare strip buttons based on dictionary"""
        # find folder that contains all controls
        main_folder = self.template_group.findFolder("MASSE group/attrib buttons")
        if main_folder:
            # create new folder that will contain all group/attrib buttons
            parm_list = content_dict.keys()
            folder_label = "Geo data"
            folder_name = "MASSE_geo_data"
            folder_containing_strips = hou.FolderParmTemplate(folder_name, folder_label,
                                                              folder_type=hou.folderType.Simple)
            for entry in content_dict:
                # create two different list for names and labels
                menu_items = []
                menu_labels = []
                # create label for button strip
                # split entry at _
                data_type = entry.split("_")[0]
                if data_type == "attrib":
                    label_prefix = "[A]"
                else:
                    label_prefix = "[G]"
                # replace data_type with full name for easier reading of data
                parm_label = entry.replace(data_type, label_prefix)
                for name, label in content_dict[entry]:
                    menu_items.append(name)
                    menu_labels.append(label)
                menu_template = hou.MenuParmTemplate(entry, parm_label, menu_items, menu_labels,
                                                     is_button_strip=True, menu_type=hou.menuType.StringToggle,
                                                     join_with_next=False)
                menu_template.setScriptCallback \
                    (r"""__import__("MASSE_tools.group_attrib_utils").group_attrib_utils.AttribGroupUtils.button_strip_callback(kwargs)""")
                menu_template.setScriptCallbackLanguage(hou.scriptLanguage.Python)
                folder_containing_strips.addParmTemplate(menu_template)
            if folder_name in [parm.name() for parm in main_folder.parmTemplates()]:
                self.template_group.replace(folder_name, folder_containing_strips)
            else:
                self.template_group.appendToFolder(main_folder, folder_containing_strips)
            self.node.setParmTemplateGroup(self.template_group)
            for parm in parm_list:
                self.node.parm(parm).set(0)

    @staticmethod
    def create_group_attrib_names(node):
        """Used as a callback for a generated attrib/groups buttons"""
        new_instance = AttribGroupUtils(node)
        button_dict = AttribGroupUtils(node).get_groups_and_attribs()
        new_instance.create_strip_buttons(button_dict)

    @staticmethod
    def button_strip_callback(kwargs):
        """button callback to handle copy logic and deselect other buttons"""
        node = kwargs["node"]
        parm = kwargs["parm"]
        parm_name = kwargs["parm_name"]
        script_value = kwargs["script_value"]
        node_group_template = node.parmTemplateGroup()
        parm_template = parm.parmTemplate()
        menu_tags = parm_template.tags()
        menu_items = parm_template.menuItems()
        button_val_dict = {pow(2, index): item for index, item in enumerate(menu_items)}
        main_folder = node_group_template.findFolder("MASSE group/attrib buttons")
        if main_folder:
            strip_templates = [template for folder in main_folder.parmTemplates()
                               if folder.name() == "MASSE_geo_data" for template in folder.parmTemplates()]
            unselected_strips = [strip for strip in strip_templates if strip.name() != parm_name]
            if "MASSE_pre_press_val" not in menu_tags.keys():
                menu_tags["MASSE_pre_press_val"] = str(script_value)
                button_val = script_value
            else:
                check_button_val = int(script_value) - int(menu_tags["MASSE_pre_press_val"])
                if check_button_val > 0:
                    button_val = check_button_val
                else:
                    button_val = script_value
                menu_tags["MASSE_pre_press_val"] = str(button_val)
            # unselect any other menu strips and delete custom dictionary entry
            for unselected in unselected_strips:
                node.parm(unselected.name()).set(0)
                template_tags = unselected.tags()
                if "MASSE_pre_press_val" in template_tags.keys():
                    template_tags.pop("MASSE_pre_press_val")
                    unselected.setTags(template_tags)
                    node_group_template.replace(unselected.name(), unselected)
            parm_template.setTags(menu_tags)
            parm.set(int(button_val))
            # set new tags for node
            node_group_template.replace(parm_name, parm_template)
            node.setParmTemplateGroup(node_group_template)
            if button_val != "0":
                pyperclip.copy(button_val_dict[int(button_val)])
            if button_val == "0":
                pyperclip.copy("")
