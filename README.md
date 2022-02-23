Houdini 19.0+ and python3 only!

To install:
    1. Copy MASSE_parm_utils folder in your Houdini documents folder
    2. Copy json file in "packages" folder in the same documents folder

If you have a previous version of the tool and want to update it, only replace the folder
Example for windows:
    MASSE_parm_utils folder in:
        C:\Users\<your_user_name>>\Documents\houdini19.0\
    MASSE_parms_utils.json in:
        C:\Users\<your_user_name>>\Documents\houdini19.0\packages

Edit json file for easy custom packages paths
For any bugs and suggestions write me an email! houdinielement@gmail.com


I will be updating this tool with more features very soon, so for any new version, just replace the folder. 
Subscribe for me on youtube! https://www.youtube.com/user/vik546


Features:
When the menu is created under HDA node, gives the option to assign parm to the HDA definition
For non-HDA nodes, it will create spare parameters
Jump to parm node menu option 
When references are created they are independent of a tool

NEW in v1.1:
Watch this for all the new features https://youtu.be/YnxL1xpsNVI
    -Multiparm references supported
    -Quickly jump to the node that parm is referencing from(basic click will select node that parm in referencing, alt-click will zoom network editor to the node,ctrl-click will put a visibility flag on that node)

Multiparm workflow:
	For multiparm to work properly, the user needs to assign multiparm folder type and one multiparm node counter. 
For most common workflow:
	-create a new multiparm folder, as a spare or hda definition
	-assign this folder as a multiparm folder, from parm-utils menu
	-create foreach-number loop and right-click on foreach-count node and assign it as a counter node.
	!ATTENTION!
	-it is important for the counter node attribute 'ivalue' and multiparm folder type property 'first instance' to be the same.