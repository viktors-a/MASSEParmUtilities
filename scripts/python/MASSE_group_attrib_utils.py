"""Module for retirving geometry attributes/groups on nodes that can reference them, like group/attribute rename"""
import hou
import pyperclip
from collections import defaultdict
from MASSE_parm_utils import HoudiniError

attrib_strings = ["point", "prim", "vertex", "global"]
group_strings = ["point", "prim", "edge", "vertex"]


class AttribGroupUtils:
    def __init__(self, node, get):
        self.node = node
        self.get = get
        self.template_group = self.node.parmTemplateGroup()
        self.geo = None
        self.read_from_node = None

    def get_groups_or_attribs(self) -> dict:
        """returns dict of ether attibs or groups of the geometry"""
        # get node to read groups/attribs from
        get_from_index = self.node.parm("MASSE_input_index")
        if get_from_index:
            node_geo_list = list(self.node.inputs())
            node_geo_list.insert(0, self.node)
            node_geo_dict = {index - 1: node for index, node in enumerate(node_geo_list) if node}
            """get parameter should be ether "Attributes" or "Groups" """
            if isinstance(self.node, hou.SopNode):
                try:
                    self.geo = node_geo_dict[get_from_index.eval()-1].geometry()
                except KeyError:
                    HoudiniError("No geometry found at input index")
                if self.geo:
                    return_dict = defaultdict(list)
                    if self.get == "Attributes":
                        for attrib_type in attrib_strings:
                            for attrib in getattr(self.geo, f"{attrib_type}Attribs")():
                                attrib_name = attrib.name()
                                attib_is_array = attrib.isArrayType()
                                is_array = ""
                                if attib_is_array:
                                    is_array = " array"
                                attrib_data_type = attrib.dataType().name()
                                attrib_label = f"{attrib_name}({attrib_data_type}{is_array})"
                                return_dict[attrib_type].append([attrib_name, attrib_label])
                        return dict(return_dict)
                    if self.get == "Groups":
                        for group_type in group_strings:
                            for group_str in getattr(self.geo, f"{group_type}Groups")():
                                group_name = group_str.name()
                                return_dict[group_type].append([group_name, group_name])
                        return dict(return_dict)
                else:
                    raise HoudiniError("No sop node detected")

    def create_strip_buttons(self, content_dict):
        """create spare strip buttons based on dictionary"""
        # find filder that includes all buttons
        main_folder = self.template_group.findFolder("MASSE group/attrib buttons")
        if main_folder:
            parm_list = []
            folder_label = self.get
            folder_name = self.get.lower()
            folder_containing_strips = hou.FolderParmTemplate(folder_name, folder_label,
                                                              folder_type=hou.folderType.Collapsible)
            for entry in content_dict:
                parm_name = "_".join((self.get, entry)).lower()
                parm_list.append(parm_name)
                # create two different list for names and labels
                menu_items = []
                menu_labels = []
                for name, label in content_dict[entry]:
                    menu_items.append(name)
                    menu_labels.append(label)
                menu_template = hou.MenuParmTemplate(parm_name, entry, menu_items, menu_labels,
                                                     is_button_strip=True, menu_type=hou.menuType.StringToggle,
                                                     join_with_next=True)
                menu_template.setScriptCallback \
                    (r"""__import__("MASSE_group_attrib_utils").AttribGroupUtils.button_strip_callback(kwargs)""")
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
    def create_group_attrib_names(node, get):
        """Used as a callback for a generated attrib/groups buttons"""
        new_instance = AttribGroupUtils(node, get)
        button_dict = AttribGroupUtils(node, get).get_groups_or_attribs()
        new_instance.create_strip_buttons(button_dict)

    @staticmethod
    def button_strip_callback(kwargs):
        """button callback to create string from selected buttons that can be pasted"""
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
                               if folder.label() in ["Attributes", "Groups"] for template in folder.parmTemplates()]
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
