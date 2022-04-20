from typing import Iterable, Optional, Tuple, Generator
import itertools
import re
import hou


class HoudiniError(Exception):
    """Display message in houdini"""


def allParmTemplateNames(group_or_folder: hou.ParmTemplateGroup) -> Iterable[str]:
    '''Generator of parm names'''
    for parm_template in group_or_folder.parmTemplates():
        yield parm_template.name()
        if parm_template.type() == hou.parmTemplateType.Folder:
            for sub_parm_template in allParmTemplateNames(parm_template):
                yield sub_parm_template


class parmUtils():

    def __init__(self, kwargs) -> None:
        self.kwargs = kwargs
        self.parm_inst = kwargs["parms"][0]
        self.parm_node = self.parm_inst.node()
        self.parm_tuple = self.parm_inst.tuple()
        self.parm_group = self.parm_node.parmTemplateGroup()
        self._parm = self.parm_tuple.parmTemplate()  # original parm

    @property
    # node on witch set referenced parms
    def envNode_parm(self) -> Optional[str]:
        env = hou.getenv("MASSE_PARM_NODE")
        if env:
            return hou.node(env)

    @property
    def envNode_multi_counter(self) -> Optional[str]:
        env = hou.getenv("MASSE_MULTIPARM_COUNTER_NODE")
        if env:
            return hou.node(env)

    @property
    def channelType(self):
        if isinstance(self._parm, hou.StringParmTemplate):
            return "chs"
        return "ch"

    @property
    # check if the active parm node is an hda, if is returns hda group
    def hdaGroup(self) -> Optional[hou.ParmTemplateGroup]:
        if self.envNode_parm.type().definition():
            return self.envNode_parm.type().definition().parmTemplateGroup()
        else:
            return None

    @property
    def refrencePath(self):
        return self.parm_node.relativePathTo(self.envNode_parm)

    @staticmethod
    # combines both the spare parms and definition parms
    def allNodeParms(node: hou.Node) -> Iterable[str]:
        to_check = [node.parmTemplateGroup(), ]
        node_type = node.type()
        node_def = node_type.definition()
        if node_def:
            to_check.append(node_def.parmTemplateGroup())
        for group in itertools.chain(to_check):
            for name in allParmTemplateNames(group):
                yield name
        else:
            return None

    @staticmethod
    def jumpToNode(env: str, parm_type: str) -> None:
        network_editor = hou.ui.paneTabUnderCursor()
        choice = hou.ui.displayCustomConfirmation(
            f"Active {parm_type} node path: {env}", buttons=("Jump to node", "Ok"))
        if choice == 0 and isinstance(network_editor, hou.NetworkEditor):
            node_obj = hou.node(env)
            network_editor.setCurrentNode(node_obj)
            network_editor.homeToSelection()

    # using regular expressions, find parm referenced, if parm doesn't exist generate spare parm
    @staticmethod
    def createSpareParmFromExpression(parms: Tuple, parm_type: hou.ParmTemplate, min: int = 1, max: int = 10) -> None:
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
                re_match = re.search(re_expr, parm_expr)
                if re_match:
                    parm_name = re_match.group("parm_name").strip()
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
    def changeRange(parms: Tuple) -> None:
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
                        group.replace(parm_name,replace_parm)
                        node.setParmTemplateGroup(group)
                else:
                    raise HoudiniError(
                        "Range change only supported for 1D float/integer values")
            else:
                raise HoudiniError("Not a spare parm")

    # invalid parm schemes objects for parm conversion
    @staticmethod
    def invalidSchemes() -> Generator:
        schemes = ("XYWH", "BeginEnd", "StartEnd", "MinMax", "MaxMin")
        for scheme in schemes:
            yield getattr(hou.parmNamingScheme, scheme)

    def valid_temp(self, invalid_parm_node: hou.Node) -> hou.ParmTemplate:
        base_parm = self._parm
        name = base_parm.name()
        parm_names = set(parmUtils.allNodeParms(invalid_parm_node))
        if name in parm_names:
            strip_parm = re.sub(r"[\d_]+$", "",
                                self._parm.name(), flags=re.IGNORECASE)
            for id in itertools.count(0, 1):
                check = "".join((strip_parm, "_", str(id)))
                if check not in parm_names:
                    base_parm.setName(check)
                    break
        # to not throw an error when user creates references from unsupported parms, convert parm to supported
        if base_parm.namingScheme() in parmUtils.invalidSchemes():
            base_parm.setNamingScheme(hou.parmNamingScheme.Base1)
            
        base_parm.setConditional(hou.parmCondType.HideWhen, "")
        return base_parm

    def createRelativeReference(self, assign_to_definition: bool = True) -> None:
        # only wrks on non-multiparms and if parm node is set up
        if self.envNode_parm:
            if not self.parm_inst.isMultiParmInstance():
                # if node is an hda, give option to add parm to hda definition or spare parm
                if self.hdaGroup:
                    if assign_to_definition:
                        set_on = self.envNode_parm.type().definition()
                    else:
                        set_on = self.envNode_parm
                else:
                    set_on = self.envNode_parm
            # create new folder that will store all the nodes form one node
                folder_id = self.parm_node.path()
                folder_id = folder_id.replace("/", "_").strip("_")
                group = set_on.parmTemplateGroup()
                if group.findFolder(folder_id):
                    found_folder = group.findFolder(folder_id)
                    group.appendToFolder(
                        found_folder, self.valid_temp(self.envNode_parm))
                    set_on.setParmTemplateGroup(
                        group, rename_conflicting_parms=True)
                else:
                    # if the user tries to write parm to hda definition on a node that's already referenced in a sapre parms, trow an exception to avoid confusion
                    if self.hdaGroup and assign_to_definition:
                        if self.envNode_parm.parmTemplateGroup().findFolder(folder_id):
                            raise HoudiniError(
                                "Folder found in a spare parameters of the node")
                    # create a folder that will be named after the full path of the node, and put all parameters from that node in it
                    new_folder = hou.FolderParmTemplate(
                        folder_id, folder_id, (self.valid_temp(self.envNode_parm),), folder_type=hou.folderType.Simple)
                    group.append(new_folder)
                    set_on.setParmTemplateGroup(
                        group, rename_conflicting_parms=True)

            else:
                raise HoudiniError("Parm is a multiparm instance")

            # set up an expression for referencing new parm
            refeshed_folder = set_on.parmTemplateGroup().findFolder(folder_id)
            latest_temp = refeshed_folder.parmTemplates()[-1].name()
            parm_to_ref = self.envNode_parm.parmTuple(latest_temp)

            for to_set, to_fetch in zip(parm_to_ref, self.parm_tuple):
                parm_name = to_set.name()
                parm_path = f"{self.channelType}(\"{self.refrencePath}/{parm_name}\")"
            # if parm is a ramp, create a parm without expression, the user will have to link them manually
                if not isinstance(self.parm_inst.parmTemplate(), hou.RampParmTemplate):
                    to_fetch.setExpression(
                        parm_path, language=hou.exprLanguage.Hscript)
        else:
            raise HoudiniError("No parm enviroment parm found")

    def deleteParm(self):
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


class MultiparmUtils(parmUtils):

    @property
    def envNode_multiparm_folder(self) -> Optional[str]:
        folder_str = hou.getenv("MASSE_MULTIPARM_FOLDER")
        if folder_str:
            return hou.parm(folder_str)

    @staticmethod
    def createMultiParmCounterExpr(counter_node: hou.Node, mp_folder: hou.Parm) -> None:
        end_node_rel = counter_node.parm("blockpath").eval()
        end_node_name = re.search(r"\w+", end_node_rel).group()
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
    def setMultiParmFirstInstance(mp_folder: hou.Parm) -> None:
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
    def createSpareCounterReference(kwargs):
        node = kwargs["node"]
        group = node.parmTemplateGroup()
        invalid_parms = MultiparmUtils.allNodeParms(node)
        base_spare = None
        for id in itertools.count(0):
            base_spare = f"spare_input{id}"
            if base_spare not in invalid_parms:
                break
        spare_parm = hou.StringParmTemplate(
            base_spare, base_spare, 1, string_type=hou.stringParmType.NodeReference)
        # set up tags and help
        parm_id = int(re.search("\d+", base_spare).group()) + 1
        help = f"Refer to this in expressions as -{parm_id}, such as: npoints(-{parm_id})"
        spare_tags = {"opfilter": "!!SOP!!",
                      "oprelative": ".", "cook_dependent": "1"}
        # set tags and help
        spare_parm.setHelp(help)
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

    def createMultiparmReference(self):
        if not self.envNode_multiparm_folder.containingFolders() and self.envNode_multi_counter:
            mp_folder = self.envNode_multiparm_folder
            mp_folder_name = mp_folder.name()
            mp_folder_temp = mp_folder.parmTemplate()
            mp_node = mp_folder.node()
            to_append = self.valid_temp(mp_node)
            to_append.setName("".join((to_append.name(), "#")))
            # clear out conditionals for parm to be visible
            to_append.setConditional(hou.parmCondType.HideWhen, "")
            if self.envNode_multiparm_folder.isSpare():
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
                self.envNode_multi_counter)
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
                        parm_scheme = str(scheme+1)
                    else:
                        parm_scheme = parm.name()[-1]
                    _parm_split.append(f"\"{parm_scheme}\"")

                parm_str = " + ".join(_parm_split)
                full_expr = f"{self.channelType}(strcat(\"{path_to_multi_folder}/\", {parm_str}))"
                parm.setExpression(
                    full_expr, language=hou.exprLanguage.Hscript)
