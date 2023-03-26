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

ADD YOUR OWN EXPRESSONS TO PASTER EXPRESSION MENU:

    1. copy userPreferences.json to root of MASSEParmUtilities folder
    2. edit userPreferences.json to add your expressions

    -You can add any expression, but it must be under "parmExpressions" in userPreferences.json file.
    -When expression is selected, user will be prompted to add prefix and ability to edit selected expression.
    - Based on whether "geo_ref" in found in expression, menu after expression selection will be different.
    - If spare input parms are found on node, they will be added to menu as buttons and if selected it
    will replace "geo_ref" on expression.
