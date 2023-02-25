from typing import Iterable, Optional, Tuple, Generator
import itertools
import re
import hou
import os


class HoudiniError(Exception):
    """Display message in houdini"""


class parmUtils:

    def __init__(self, kwargs) -> None:
        self.kwargs = kwargs
        self.parm_inst = kwargs["parms"][0]
        self.parm_node = self.parm_inst.node()
        self.parm_tuple = self.parm_inst.tuple()
        self.parm_group = self.parm_node.parmTemplateGroup()
        self._parm = self.parm_tuple.parmTemplate()  # original parm

    @property
    def parm_controll_node(self) -> Optional[str]:
        # node on witch set referenced parms
        env = hou.getenv("MASSE_PARM_NODE")
        if env:
            return hou.node(env)

    @property
    def multiparm_folder(self) -> Optional[str]:
        # multiparm folder
        env = hou.getenv("MASSE_MULTIPARM_COUNTER_NODE")
        if env:
            return hou.node(env)

    @property
    def channel_type(self):
        # channel expression funchtion name based on data type its holds
        if isinstance(self._parm, hou.StringParmTemplate):
            return "chs"
        return "ch"

    @property
    def hda_template_group(self) -> Optional[hou.ParmTemplateGroup]:
        # check if the active parm node is a  hda, if is returns hda parm template group
        if self.parm_controll_node.type().definition():
            return self.parm_controll_node.type().definition().parmTemplateGroup()
        else:
            return None

    @staticmethod
    def rename_selected_node():
        # rename multiple nodes at once
        rename_message = "Rename selected nodes"
        nodes = {node.name(): node for node in hou.selectedNodes()}
        if nodes:
            input = hou.ui.readMultiInput(
                rename_message, input_labels=list(nodes.keys()), buttons=("Rename", "Cancel"))
            if input[0] == 0:
                for node, new_name in zip(nodes.values(), input[1]):
                    if new_name:
                        node.setName(new_name, unique_name=True)

    @staticmethod
    def all_parm_template_names(group_or_folder: hou.ParmTemplateGroup) -> Iterable[str]:
        """Generator of parm names"""
        for parm_template in group_or_folder.parmTemplates():
            yield parm_template.name()
            if parm_template.type() == hou.parmTemplateType.Folder:
                for sub_parm_template in MultiparmUtils.all_parm_template_names(parm_template):
                    yield sub_parm_template

    @staticmethod
    def all_node_parms(node: hou.Node) -> Iterable[str]:
        # combines both the spare parms and definition parms
        to_check = [node.parmTemplateGroup(), ]
        node_type = node.type()
        node_def = node_type.definition()
        if node_def:
            to_check.append(node_def.parmTemplateGroup())
        for group in itertools.chain(to_check):
            for name in parmUtils.all_parm_template_names(group):
                yield name
        else:
            return None

    @staticmethod
    def jump_to_node(env: str, parm_type: str) -> None:
        # frame network editor to node
        network_editor = hou.ui.paneTabUnderCursor()
        choice = hou.ui.displayCustomConfirmation(
            f"Active {parm_type} node path: {env}", buttons=("Jump to node", "Ok"))
        if choice == 0 and isinstance(network_editor, hou.NetworkEditor):
            node_obj = hou.node(env)
            network_editor.setCurrentNode(node_obj)
            network_editor.homeToSelection()

    @staticmethod
    def create_spare_parm_from_expression(parms: Tuple, parm_type: hou.ParmTemplate, min: int = 1,
                                          max: int = 10) -> None:
        # using regular expressions, find parm referenced, if parm doesn't exist generate spare parm
        re_expr = re.compile(
            r"(?P<ch_type>chs?)\((?:'|\")(?P<parm_name>[A-Za-z0-9_ ]+)(?:'|\")\)")
        for parm in parms:
            if not parm.getReferencedParm() != parm:
                # get expression parm name
                parm_temp = parm.parmTemplate()
                parm_expr = None
                node = parm.node()
                if isinstance(parm_temp, hou.StringParmTemplate):
                    parm_expr = parm.unexpandedString()
                else:
                    try:
                        parm_expr = parm.expression()
                    except hou.OperationFailed:
                        raise HoudiniError("No expression found")
                re_match = re.findall(re_expr, parm_expr)
                if re_match:
                    for parm in re_match:
                        parm_name = parm[1].strip()
                        group = node.parmTemplateGroup()
                        if not parm_type == hou.StringParmTemplate:
                            new_parm = parm_type(
                                parm_name, parm_name, 1, (0,), min, max)
                        else:
                            new_parm = parm_type(parm_name, parm_name, 1)
                        group.append(new_parm)
                        node.setParmTemplateGroup(group)
                else:
                    raise HoudiniError("Parm is controlled by some other parm")

    @staticmethod
    # todo allow changing of range also for HDAs
    def change_parm_range(parms: Tuple) -> None:
        # changes spare parm range
        for parm in parms:
            if parm.isSpare():
                node = parm.node()
                parm_temp = parm.parmTemplate()
                if parm_temp.numComponents() == 1:
                    parm_name = parm_temp.name()
                    parm_label = parm_temp.label()
                    new_range = hou.ui.readInput("Input new range")[1].split()
                    parm_class = parm_temp.__class__
                    if len(new_range) == 2:
                        min, max = new_range
                        min, max = float(min), float(max)
                        # cast appropriate value type, so parm
                        if isinstance(parm_temp, hou.IntParmTemplate):
                            min, max = int(min), int(max)
                        replace_parm = parm_class(
                            parm_name, parm_label, 1, (0,), min, max)
                        group = node.parmTemplateGroup()
                        group.replace(parm_name, replace_parm)
                        node.setParmTemplateGroup(group)
                else:
                    raise HoudiniError(
                        "Range change only supported for 1D float/integer values")
            else:
                raise HoudiniError("Not a spare parm")

    @staticmethod
    def invalid_schemes() -> Generator:
        # invalid parm schemes objects for parm conversion
        schemes = ("XYWH", "BeginEnd", "StartEnd", "MinMax", "MaxMin")
        for scheme in schemes:
            yield getattr(hou.parmNamingScheme, scheme)

    @staticmethod
    def set_parm_labels(kwargs):
        # create parm labels based on parm names
        node = kwargs["node"]
        group = node.parmTemplateGroup()
        spare_names = [parm.parmTemplate().name()
                       for parm in node.spareParms()]
        all_templates = group.entries() + group.entriesWithoutFolders()
        for parm in all_templates:
            parm_name = parm.name()
            if parm_name in spare_names:
                original_parm = parm.name()
                parm_name = re.sub(r'\d+', '', original_parm)
                label = parm_name.replace("_", " ").title()
                parm.setLabel(label)
                group.replace(original_parm, parm)
        node.setParmTemplateGroup(group)

    @staticmethod
    def remove_spare_parm(node, delete_all=False):
        # remove spare parms that are not in a folder, used for wrangle nodes that create ch() calls
        parmt_temp_group = node.parmTemplateGroup()
        spare_parms = [parm for parm in node.parmTuples() if not
        isinstance(parm.parmTemplate(), (hou.FolderSetParmTemplate, hou.FolderParmTemplate)) and parm.isSpare()]
        # get only parms that are not in any folder
        not_in_folder = []
        for parm in spare_parms:
            # exclude spares that don't have a containingFolders, like separator items
            try:
                in_folder = parm.containingFolders()
                if not in_folder:
                    not_in_folder.append(parm.parmTemplate())
            except IndexError:
                continue
        if not_in_folder:
            if delete_all:
                for template in not_in_folder:
                    parmt_temp_group.remove(template)
                node.setParmTemplateGroup(parmt_temp_group)
                return
            parmt_temp_group.remove(not_in_folder[-1])
            node.setParmTemplateGroup(parmt_temp_group)

    @staticmethod
    def find_valid_env_in_string(kwargs):
        # find env variables value in a parm string and give and option to replace part of the string with env variables
        # only get envs that are actual file paths
        possibe_envs = {key: os.environ[key] for key in os.environ if os.path.exists(os.environ[key])}
        new_parm_val_options = []
        re_slashes = r'[\\/]+'
        parm = kwargs["parms"][0]
        # strip leading characters of file. This string occurs when file path is copied in clipboard
        init_parm_val = parm.eval()
        file_prefix = re.match(r"^file:[/\\]+", init_parm_val)
        if file_prefix:
            init_parm_val = init_parm_val[file_prefix.end():]
        equal_slashes_parm = re.sub(re_slashes, "/", init_parm_val)
        # check if data in parm is a string
        if isinstance(init_parm_val, str):
            for key in possibe_envs:
                env_start_str = f"${key}"
                env_middle_str = f"/${key}"
                equal_slashes_env = re.sub(re_slashes, "/", possibe_envs[key])
                matches_found = re.findall(equal_slashes_env, equal_slashes_parm)
                if matches_found:
                    # add env key without a slash if env val is found at the beggining, othervise add "/" to it
                    if re.match(equal_slashes_env, equal_slashes_parm):
                        new_parm_val_options.append(re.sub(equal_slashes_env, env_start_str, equal_slashes_parm))
                    else:
                        new_parm_val_options.append(re.sub(equal_slashes_env, env_middle_str, equal_slashes_parm))
            # if any vals found sort them by length and create selectFromList window
            if new_parm_val_options:
                new_parm_val_options.sort(key=len)
                selection = hou.ui.selectFromList(new_parm_val_options, title="Found environment variables",
                                                  message="Select new parameter value")
                if selection:
                    selected = selection[0]
                    new_parm_val = new_parm_val_options[selected]
                    parm.set(new_parm_val)
            else:
                raise HoudiniError("No environment variables found in a string.")
        else:
            raise HoudiniError("No string found.")

    def valid_temp(self, invalid_parm_node: hou.Node) -> hou.ParmTemplate:
        # sets up parm that won't interfere with other parms already in parm node
        base_parm = self._parm
        name = base_parm.name()
        parm_names = set(parmUtils.all_node_parms(invalid_parm_node))
        if name in parm_names:
            strip_parm = re.sub(r"[\d_]+$", "",
                                self._parm.name(), flags=re.IGNORECASE)
            for id in itertools.count(0, 1):
                check = "".join((strip_parm, "_", str(id)))
                if check not in parm_names:
                    base_parm.setName(check)
                    break
        # to not throw an error when user creates references from unsupported parms, convert parm to supported
        if base_parm.namingScheme() in parmUtils.invalid_schemes():
            base_parm.setNamingScheme(hou.parmNamingScheme.Base1)

        base_parm.setConditional(hou.parmCondType.HideWhen, "")
        return base_parm

    def create_relative_parm_reference(self, assign_to_definition: bool = True) -> None:
        # if parm node is set, creates parm on that node and creates expression that refrences newly created parm
        if self.parm_controll_node:
            if not self.parm_inst.isMultiParmInstance():
                parm_val_tuple = self.parm_tuple.eval()
                # if node is an hda, give option to add parm to hda definition or spare parm
                if self.hda_template_group:
                    if assign_to_definition:
                        set_on = self.parm_controll_node.type().definition()
                    else:
                        set_on = self.parm_controll_node
                else:
                    set_on = self.parm_controll_node
                # create new folder that will store all the nodes form one node
                folder_id = self.parm_node.path()
                folder_id = folder_id.replace("/", "_").strip("_")
                group = set_on.parmTemplateGroup()
                if group.findFolder(folder_id):
                    found_folder = group.findFolder(folder_id)
                    valid_temp = self.valid_temp(self.parm_controll_node)
                    group.appendToFolder(
                        found_folder, valid_temp)
                    set_on.setParmTemplateGroup(
                        group, rename_conflicting_parms=True)
                    self.parm_controll_node.parmTuple(valid_temp.name()).set(parm_val_tuple)
                else:
                    # if the user tries to write parm to hda definition on a node that's already referenced in a sapre parms, trow an exception to avoid confusion
                    if self.hda_template_group and assign_to_definition:
                        if self.parm_controll_node.parmTemplateGroup().findFolder(folder_id):
                            raise HoudiniError(
                                "Folder found in a spare parameters of the node")
                    # create a folder that will be named after the full path of the node, and put all parameters from that node in it
                    valid_temp = self.valid_temp(self.parm_controll_node)
                    new_folder = hou.FolderParmTemplate(
                        folder_id, folder_id, (valid_temp,), folder_type=hou.folderType.Simple)
                    group.append(new_folder)
                    set_on.setParmTemplateGroup(
                        group, rename_conflicting_parms=True)
                    self.parm_controll_node.parmTuple(valid_temp.name()).set(parm_val_tuple)

            else:
                raise HoudiniError("Parm is a multiparm instance")

            # set up an expression for referencing new parm
            refeshed_folder = set_on.parmTemplateGroup().findFolder(folder_id)
            latest_temp = refeshed_folder.parmTemplates()[-1].name()
            parm_to_ref = self.parm_controll_node.parmTuple(latest_temp)

            for to_set, to_fetch in zip(parm_to_ref, self.parm_tuple):
                parm_name = to_set.name()
                refrence_path = self.parm_node.relativePathTo(self.parm_controll_node)
                parm_path = f"{self.channel_type}(\"{refrence_path}/{parm_name}\")"
                # if parm is a ramp, create a parm without expression, the user will have to link them manually
                if not isinstance(self.parm_inst.parmTemplate(), hou.RampParmTemplate):
                    to_fetch.setExpression(
                        parm_path, language=hou.exprLanguage.Hscript)
        else:
            raise HoudiniError("No parm enviroment parm found")

    def delete_parm(self):
        # make sure we can only delete parms that could have been referenced in other nodes
        if not self.parm_tuple.isMultiParmInstance():
            if not isinstance(self.parm_tuple.parmTemplate(), hou.FolderSetParmTemplate):
                if self.parm_inst.isSpare():
                    # remove keyframes form all the parms referencting this parm
                    for parm in self.parm_tuple:
                        for parm_ref in parm.parmsReferencingThis():
                            parm_ref.deleteAllKeyframes()
                    self.parm_node.removeSpareParmTuple(self.parm_tuple)
                    return
                # if parm not found in spares, and its an editable hda, go find it and update hda definition
                if self.parm_node.type().definition():
                    group = self.parm_group
                    for parm in self.parm_tuple:
                        for parm_ref in parm.parmsReferencingThis():
                            parm_ref.deleteAllKeyframes()
                    group.remove(self._parm.name())
                    self.parm_node.type().definition().setParmTemplateGroup(group)
            else:
                raise HoudiniError("Can't delete folder")
        else:
            raise HoudiniError("Parm is a multiparm instance")

    def create_pdg_attrib_expression(self):
        # todo fetch pdg attribute
        pass


class MultiparmUtils(parmUtils):

    @property
    def get_multiparm_folder(self) -> Optional[str]:
        # get multiparm folder, if it's set up
        folder_str = hou.getenv("MASSE_MULTIPARM_FOLDER")
        if folder_str:
            return hou.parm(folder_str)

    @staticmethod
    def create_multiparm_counter_expr(counter_node: hou.Node, mp_folder: hou.Parm) -> None:
        # create reference to user set multiparm folder that will control how many for-each iterations to run
        end_node_rel = counter_node.parm("blockpath").eval()
        end_node_name = re.search(r"\w+$", end_node_rel).group()
        # get end block node object
        parent = counter_node.parent().path()
        end_node_path = f"{parent}/{end_node_name}"
        end_node_obj = hou.node(end_node_path)

        iter_parm = end_node_obj.parm("iterations")
        rel_path = end_node_obj.relativePathTo(mp_folder.node())

        mp_folder_name = mp_folder.name()
        # set expression for mp folder, to reference end block iteration count
        iter_parm.setExpression(
            f"ch(\"{rel_path}/{mp_folder_name}\")", hou.exprLanguage.Hscript)

    @staticmethod
    def set_multiparm_init_counter_index(mp_folder: hou.Parm) -> None:
        # methode for making sure that for each counter node and multiparm folder start index matches
        node = mp_folder.node()
        folder_template = mp_folder.parmTemplate()
        folder_name = folder_template.name()
        tags = folder_template.tags()
        offset = tags.get("multistartoffset")
        if offset != "0":
            tags["multistartoffset"] = "0"
        if mp_folder.isSpare():
            group = node.parmTemplateGroup()
            set_on = node
        else:
            set_on = node.type().definition()
            group = set_on.parmTemplateGroup()
        template = group.find(folder_name)
        template.setTags(tags)
        group.replace(folder_name, template)
        set_on.setParmTemplateGroup(group)

    @staticmethod
    def add_spare_input(kwargs):
        # when two nodes are selected in network viewer, creates spare input parm for node that OPmenu was triggered
        # for referencing the second node
        node = kwargs["node"]
        group = node.parmTemplateGroup()
        invalid_parms = MultiparmUtils.all_node_parms(node)
        base_spare = None
        for id in itertools.count(0):
            base_spare = f"spare_input{id}"
            if base_spare not in invalid_parms:
                break
        spare_parm = hou.StringParmTemplate(
            base_spare, base_spare, 1, string_type=hou.stringParmType.NodeReference)
        # set up tags and help
        parm_id = int(re.search("\d+", base_spare).group()) + 1
        spare_input_help = f"Refer to this in expressions as -{parm_id}, such as: npoints(-{parm_id})"
        spare_tags = {"opfilter": "!!SOP!!",
                      "oprelative": ".", "cook_dependent": "1"}
        # set tags and help
        spare_parm.setHelp(spare_input_help)
        spare_parm.setTags(spare_tags)
        group.append(spare_parm)
        node.setParmTemplateGroup(group, rename_conflicting_parms=True)
        # set relative reference to a node
        spare_input_node = None
        for sel_node in hou.selectedNodes():
            if sel_node != node:
                spare_input_node = sel_node

        rel_path = node.relativePathTo(spare_input_node)
        node.parm(base_spare).set(rel_path)

    def create_multiparm_reference(self):
        # creates expression referencing multiparm folder index
        if not self.get_multiparm_folder.containingFolders() and self.multiparm_folder:
            mp_folder = self.get_multiparm_folder
            mp_folder_name = mp_folder.name()
            mp_folder_temp = mp_folder.parmTemplate()
            mp_node = mp_folder.node()
            to_append = self.valid_temp(mp_node)
            to_append.setName("".join((to_append.name(), "#")))
            # clear out conditionals for parm to be visible
            to_append.setConditional(hou.parmCondType.HideWhen, "")
            if self.get_multiparm_folder.isSpare():
                set_on = mp_node
                group = mp_folder.node().parmTemplateGroup()
            else:
                set_on = mp_node.type().definition()
                group = mp_node.type().definition().parmTemplateGroup()

            if set_on and group:
                group.appendToFolder(mp_folder_temp, to_append)
                set_on.setParmTemplateGroup(
                    group, rename_conflicting_parms=True)
            # set up expression
            path_to_multi_folder = self.parm_node.relativePathTo(mp_node)
            path_to_attrib = self.parm_node.relativePathTo(
                self.multiparm_folder)
            # get attrib reference
            attrib_ref = f"detail(\"{path_to_attrib}\",\"iteration\",0)"
            # exact name of the parm user has just added to the multiparm folder
            parm_to_ref = set_on.parmTemplateGroup().find(
                mp_folder_name).parmTemplates()[-1].name()
            # replace "#" with a string of reference to the detail attrib
            parm_sub = re.sub("#", f" {attrib_ref} ", parm_to_ref)
            parm_split = [split for split in re.split(" ", parm_sub) if split]
            for id, parm_part in enumerate(parm_split):
                if parm_part != attrib_ref:
                    parm_split[id] = f"\"{parm_part}\""
            for scheme, parm in enumerate(self.parm_tuple):
                _parm_split = list(parm_split)
                parm_name = parm.name()
                if len(self.parm_tuple) == 1:
                    pass
                else:
                    re_invalid_check = r"(\w+)(max|min|end|begin|start)"
                    if re.match(re_invalid_check, parm_name):
                        parm_scheme = str(scheme + 1)
                    else:
                        parm_scheme = parm.name()[-1]
                    _parm_split.append(f"\"{parm_scheme}\"")

                parm_str = " + ".join(_parm_split)
                full_expr = f"{self.channel_type}(strcat(\"{path_to_multi_folder}/\", {parm_str}))"
                parm.setExpression(
                    full_expr, language=hou.exprLanguage.Hscript)
