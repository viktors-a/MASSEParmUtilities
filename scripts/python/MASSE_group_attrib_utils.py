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

    def get_groups_or_attribs(self) -> dict:
        """returns dict of ether attibs or groups of the geometry"""
        """get parameter should be ether "Attributes" or "Groups" """
        if isinstance(self.node, hou.SopNode):
            return_dict = defaultdict(list)
            self.geo = self.node.geometry()
            if self.get == "Attributes":
                for attrib_type in attrib_strings:
                    for attrib_str in getattr(self.geo, f"{attrib_type}Attribs")():
                        return_dict[attrib_type].append(attrib_str.name())
                return dict(return_dict)
            if self.get == "Groups":
                for group_type in group_strings:
                    for group_str in getattr(self.geo, f"{group_type}Groups")():
                        return_dict[group_type].append(group_str.name())
                return dict(return_dict)
        else:
            raise HoudiniError("No sop node detected")

    def create_strip_buttons(self, content_dict):
        """create spare strip buttons based on dictionary"""
        # find filder that includes all buttons
        main_folder = self.template_group.findFolder("MASSE group/attrib buttons")
        if main_folder:
            folder_label = self.get
            folder_name = self.get.lower()
            folder_containing_strips = hou.FolderParmTemplate(folder_name, folder_label,
                                                              folder_type=hou.folderType.Simple)
            for entry in content_dict:
                menu_items = content_dict[entry]
                menu_template = hou.MenuParmTemplate("_".join((self.get, entry)).lower(), entry, menu_items,
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
