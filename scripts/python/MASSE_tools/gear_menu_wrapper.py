"""Module for wrapping other modules for use in gear menus in Houdini"""
import hou


def spare_button_delete(node):
    """two buttons for deletring all or last spare parm that isn't in any folder, useful for wrangle nodes that create
    spare parms """
    template_group = node.parmTemplateGroup()
    button_list = []
    # create two buttons
    for parm_dif in [("all_spares_parms", True), ("last_spare_parm", False)]:
        to_delete, delete_all = parm_dif
        name = f"MASSE_delete_{to_delete}"
        label = f"""Delete {to_delete.replace("_", " ").title()}"""
        new_button = hou.ButtonParmTemplate(name, label, join_with_next=True)
        # callback for deleting parms
        new_button.setScriptCallbackLanguage(hou.scriptLanguage.Python)
        callback_string = f"""__import__("MASSE_tools.parm_utils").parm_utils.parmUtils.remove_spare_parm(kwargs["node"],
delete_all={delete_all}) """
        new_button.setScriptCallback(callback_string)
        button_list.append(new_button)
    folder_name = "MASSE_delete_spares"
    folder_label = folder_name.replace("_", " ")
    button_holder = hou.FolderParmTemplate(folder_name, folder_label, button_list, folder_type=hou.folderType.Collapsible)
    # add new parm template to node
    folder_exist = template_group.findFolder(folder_label)
    if folder_exist:
        template_group.replace(folder_exist, button_holder)
        node.setParmTemplateGroup(template_group)
    else:
        template_group.insertBefore([0], button_holder)
        node.setParmTemplateGroup(template_group)


def attrib_group_fetch_buttons(node):
    """created two buttons for fetching ether attribs or groups of the node"""
    template_group = node.parmTemplateGroup()
    """creates two spare buttons on a node tha when pressed will generate ether attrib or group button strip"""
    folder_name = "MASSE_group_attrib_buttons"
    label = "MASSE group/attrib buttons"
    button_folder = hou.FolderParmTemplate(folder_name, label, folder_type=hou.folderType.Collapsible)
    button_types = ["attributes", "groups"]
    button = hou.ButtonParmTemplate(f"MASSE_fetch_goeo_data", f"Fetch geo data",
                                    join_with_next=True)
    button.setScriptCallback \
        (fr"""__import__("MASSE_tools.group_attrib_utils").group_attrib_utils.AttribGroupUtils.create_group_attrib_names(kwargs["node"]) """)
    button.setScriptCallbackLanguage(hou.scriptLanguage.Python)
    button_folder.addParmTemplate(button)
    node_path = hou.MenuParmTemplate("MASSE_input_index", "Node input index:",
                                     ("This node", "0", "1", "2", "3", "Custom path"),
                                     is_button_strip=True, menu_type=hou.menuType.Normal, join_with_next=True)
    custom_path_string = hou.StringParmTemplate("MASSE_custom_path", "Path", 1, default_value=("-1",))
    button_folder.addParmTemplate(node_path)
    button_folder.addParmTemplate(custom_path_string)
    # if folder already exist, remove it
    content_folder = template_group.find(folder_name)
    if content_folder:
        template_group.remove(content_folder)
    template_group.insertBefore(template_group.parmTemplates()[0], button_folder)
    node.setParmTemplateGroup(template_group)
