IMPORTANT:
-This package is not supported by Side Effects Software. Please do not contact Side Effects Software for support of this package.
            
    -For any tools that use userPreferences.json file, for tools to find the file, place it at the root of this package folder.
    -For how json file should look, open userPreferences.json in this folder, edit and copy to root of the package.
[Playlist of videos showing how to use the tools](https://youtube.com/playlist?list=PLUBK6gGjWEeojLKIa3_HQVU8L4jUja_dy)

MULTIPLE EXTERNAL EDITOR SELECTION GUIDE:

    1. make sure labs package is installed
    2. copy userPreferences.json to root of MASSEParmUtilities folder
    3. edit userPreferences.json to add your external editors
    -The implementation is just a simple extension of labs open in external editor, before external editor is launched
    we set up environment variable "EDITOR" to path in a json file, after launch we delete it, so that config file labs
    tool creates still determines what editor is launched when using labs menu items.

ADD YOUR OWN EXPRESSONS TO PASTE EXPRESSION MENU:

    1. copy userPreferences.json to root of MASSEParmUtilities folder
    2. edit userPreferences.json to add your expressions

    -You can add any expression, but it must be under "parmExpressions" in userPreferences.json file.
    -When expression is selected, user will be prompted to add prefix and ability to edit selected expression.
    - Based on whether "geo_ref" in found in expression, menu after expression selection will be different.
    - If spare input parms are found on node, they will be added to menu as buttons and if selected it
    will replace "geo_ref" on expression.


REFERENCE CURRENT PARM NODE:

    1. for menu to appear, you must have select one nodea as a active parm node under [MASSE_TOOLS -> Set as parm node] op menu
    2. now user can reference current parm node in parms
    -default behavior is to replace current parm value with parm node parm relative path
    -if alt is pressed when menu item is selected, tool will append to current parm value
    -although this tools intention is to reference parm from parm node selected by user, it can be used to reference any node parm
    
GET PDG ATTRIBUTES:

    1. make sure that active work item is present for menu to appear
    2. alt click on menu will append selected attributes to parm, else it will replace current parm value
    3. default behavior is to joint all attribute expressions without spaces, if ctrl is pressed when menu item is selected
    tool will add _ between attribute, this is done to make it easier to use attributes in dynamic file names/paths when rendering with pdg

OBJECT MERGE SELECTED NODES:

    1. select nodes you want to object merge
    2. right click on object merge node and select "MASSE tools -> Object merge selected nodes"
    3. menu will only appear if thare are multiple selected nodes and menu was called on object merge node
    4. Default behavior that relative path will be used, you can alt-click for absolute path, ctrl-click 
    to remove any entries in object merge node before adding selected nodes