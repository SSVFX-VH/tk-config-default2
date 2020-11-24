
# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import mimetypes
import os
import sys
import re
from datetime import datetime
import sgtk
from tank_vendor import six

ssvfx_script_path = ""
if "SSVFX_PIPELINE" in os.environ.keys():
    ssvfx_script_path = os.path.join(os.environ["SSVFX_PIPELINE"], "ssvfx_scripts" )
    if not os.path.exists(ssvfx_script_path):
            ssvfx_script_path = os.path.join(os.environ["SSVFX_PIPELINE"], "Pipeline", "ssvfx_scripts" )
            if not os.path.exists(ssvfx_script_path):
                sys.stdout.write("Cannot source the ssvfx_scripts! %s" %(ssvfx_script_path))

    sys.path.append(ssvfx_script_path)
else:
    sys.stdout.write("SSVFX_PIPELINE not in env var keys. Using explicit")
    ssvfx_script_path = os.path.join(pipeline_root,"Pipeline\\ssvfx_scripts")

    sys.path.append(ssvfx_script_path)

# from general.file_functions import file_strings
# from general.data_management import json_manager
# from software.nuke.nuke_command_line  import nuke_cmd_functions as ncmd
from shotgun import shotgun_utilities

HookBaseClass = sgtk.get_hook_baseclass()

class BasicSceneCollector(HookBaseClass):
    """
    A basic collector that handles files and general objects.

    This collector hook is used to collect individual files that are browsed or
    dragged and dropped into the Publish2 UI. It can also be subclassed by other
    collectors responsible for creating items for a file to be published such as
    the current Maya session file.

    This plugin centralizes the logic for collecting a file, including
    determining how to display the file for publishing (based on the file
    extension).

    In addition to creating an item to publish, this hook will set the following
    properties on the item::

        path - The path to the file to publish. This could be a path
            representing a sequence of files (including a frame specifier).

        sequence_paths - If the item represents a collection of files, the
            plugin will populate this property with a list of files matching
            "path".

    """
    @property
    def common_file_info(self):
        """
        A dictionary of file type info that allows the basic collector to
        identify common production file types and associate them with a display
        name, item type, and config icon.

        The dictionary returned is of the form::

            {
                <Publish Type>: {
                    "extensions": [<ext>, <ext>, ...],
                    "icon": <icon path>,
                    "item_type": <item type>
                },
                <Publish Type>: {
                    "extensions": [<ext>, <ext>, ...],
                    "icon": <icon path>,
                    "item_type": <item type>
                },
                ...
            }

        See the collector source to see the default values returned.

        Subclasses can override this property, get the default values via
        ``super``, then update the dictionary as necessary by
        adding/removing/modifying values.
        """

        if not hasattr(self, "_common_file_info"):

            # do this once to avoid unnecessary processing
            self._common_file_info = {
                "Alias File": {
                    "extensions": ["wire"],
                    "icon": self._get_icon_path("alias.png"),
                    "item_type": "file.alias",
                },
                "Alembic Cache": {
                    "extensions": ["abc"],
                    "icon": self._get_icon_path("alembic.png"),
                    "item_type": "file.alembic",
                },
                "3dsmax Scene": {
                    "extensions": ["max"],
                    "icon": self._get_icon_path("3dsmax.png"),
                    "item_type": "file.3dsmax",
                },
                "Hiero Project": {
                    "extensions": ["hrox"],
                    "icon": self._get_icon_path("hiero.png"),
                    "item_type": "file.hiero",
                },
                "Houdini Scene": {
                    "extensions": ["hip", "hipnc"],
                    "icon": self._get_icon_path("houdini.png"),
                    "item_type": "file.houdini",
                },
                "Maya Scene": {
                    "extensions": ["ma", "mb"],
                    "icon": self._get_icon_path("maya.png"),
                    "item_type": "file.maya",
                },
                "Motion Builder FBX": {
                    "extensions": ["fbx"],
                    "icon": self._get_icon_path("motionbuilder.png"),
                    "item_type": "file.motionbuilder",
                },
                "Nuke Script": {
                    "extensions": ["nk"],
                    "icon": self._get_icon_path("nuke.png"),
                    "item_type": "file.nuke",
                },
                "Photoshop Image": {
                    "extensions": ["psd", "psb"],
                    "icon": self._get_icon_path("photoshop.png"),
                    "item_type": "file.photoshop",
                },
                "VRED Scene": {
                    "extensions": ["vpb", "vpe", "osb"],
                    "icon": self._get_icon_path("vred.png"),
                    "item_type": "file.vred",
                },
                "Rendered Image": {
                    "extensions": ["dpx", "exr", "png", "jpg", "jpeg"],
                    "icon": self._get_icon_path("image_sequence.png"),
                    "item_type": "file.image",
                },
                "Texture Image": {
                    "extensions": ["tx", "tga", "dds", "rat"],
                    "icon": self._get_icon_path("texture.png"),
                    "item_type": "file.texture",
                },
                "DMP": {
                    "extensions": ["tif", "tiff"],
                    "icon": self._get_icon_path("dmp.png"),
                    "item_type": "file.image",
                },                   
                "3D Equalizer": {
                    "extensions": ["3de"],
                    "icon": self._get_icon_path("lens.png"),
                    "item_type": "file.3de",
                },                             
                "PDF": {
                    "extensions": ["pdf"],
                    "icon": self._get_icon_path("file.png"),
                    "item_type": "file.image",
                },
            }

        return self._common_file_info

    @property
    def settings(self):
        """
        Dictionary defining the settings that this collector expects to receive
        through the settings parameter in the process_current_session and
        process_file methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """
        return {}

    @property
    def user_info(self):

        publisher = self.parent
        ctx = publisher.engine.context 
        user_fields =[
            'login',
            'sg_ip_address'
        ]
        user_filter =[
            ['id', 'is', ctx.user['id']],
        ]
        user_info = publisher.shotgun.find(
            'HumanUser',
            user_filter,
            user_fields
            )    

        return user_info

    @property
    def software_info(self):
        """
        Test SG for all associated software

        :returns: The SG info of the given softwares
        """  
        publisher = self.parent

        software_filters = [
        ['id', 'is_not', 0],
        ['version_names', 'is_not', None]
        # ['sg_pipeline_tools', 'is', True]
        ]
        
        software_fields = [
        'code',
        'products',
        'windows_path',
        'version_names',
        'sg_pipeline_tools'
        ]

        software_info = publisher.shotgun.find(
        'Software',
        software_filters,
        software_fields
        )

        return software_info

    @property
    def codec_info(self):
        """
        Test SG for all associated codec

        :returns: The SG info of the given codecs
        """  
        publisher = self.parent

        codec_filters = []
        
        codec_fields = ['id',
                        'code', 
                        'name', 
                        'sg_nuke_code', 
                        'sg_output_folder']

        codec_info = publisher.shotgun.find(
        'CustomNonProjectEntity08',
        codec_filters,
        codec_fields
        )

        return codec_info

    @property
    def project_info(self):
        """
        A dictionary of relative Project info that is taken from SG Project page
        """

        publisher = self.parent
        ctx = publisher.engine.context
        proj_info = publisher.shotgun.find_one("Project", 
                                            [['id', 'is', ctx.project['id']]], 
                                            ['name',
                                            'id',
                                            'sg_root',
                                            'sg_status',
                                            'sg_date_format',
                                            'sg_short_name',
                                            'sg_frame_rate', 
                                            'sg_vendor_id',
                                            'sg_frame_handles',
                                            'sg_data_type',
                                            'sg_format_width',
                                            'sg_format_height',
                                            'sg_delivery_slate_count',
                                            'sg_client_version_submission',
                                            'sg_incoming_plate_jpg_',
                                            'sg_delivery_default_process',
                                            'sg_incoming_fileset_padding',
                                            'sg_proxy_format_ratio',
                                            'sg_format_pixel_aspect_ratio',
                                            'sg_lut',
                                            'sg_version_zero_lut',
                                            'sg_version_zero_slate',
                                            'sg_version_zero_internal_burn_in',
                                            'sg_burnin_frames_format',
                                            'sg_delivery_qt_dual_lut',
                                            'sg_delivery_format_width',
                                            'sg_delivery_format_height',
                                            'sg_delivery_reformat_filter',
                                            'sg_delivery_fileset_padding',
                                            'sg_delivery_fileset_slate',
                                            'sg_zip_fileset_delivery',
                                            'sg_pixel_aspect_ratio',
                                            'sg_reformat_plates_to_deliverable',
                                            'sg_delivery_fileset',
                                            'sg_delivery_fileset_compression',
                                            'sg_delivery_qt_bitrate',
                                            'sg_delivery_qt_slate',
                                            'sg_delivery_burn_in',
                                            'sg_delivery_qt_codecs',
                                            'sg_delivery_qt_formats',
                                            'sg_delivery_folder_structure',
                                            'sg_color_space',
                                            'sg_project_color_management',
                                            'sg_project_color_management_config',
                                            'sg_timecode',
                                            'sg_upload_qt_formats',
                                            'sg_review_qt_codecs',
                                            'sg_review_burn_in',
                                            'sg_review_qt_slate',
                                            'sg_review_qt_formats',
                                            'sg_slate_frames_format',
                                            'sg_frame_leader',
                                            'sg_review_lut',
                                            'sg_type',
                                            'tank_name',
                                            'sg_3d_settings']
        )     
        proj_info.update({'artist_name' : ctx.user['name']})

        formats = publisher.shotgun.find("CustomNonProjectEntity01",
        [],
        ['code',
        'sg_format_height',
        'sg_format_width',
        ])
        proj_info.update({'formats' : formats})

        local_storage = publisher.shotgun.find("LocalStorage",
        [],
        ["code",
        "windows_path",
        "linux_path",
        "mac_path"])
        
        if "win" in sys.platform:
            path_root = "windows_path"
            sg_root = "local_path_windows"
        elif sys.platform == "linux":
            path_root = "linux_path"
            sg_root = "local_path_linux"

        local_storage_match = next((ls for ls in local_storage if ls[path_root] in proj_info['sg_root'][sg_root]), None)
        proj_info['local_storage'] = local_storage_match

        if proj_info['sg_3d_settings']:
            sg_3d_settings = publisher.shotgun.find("CustomNonProjectEntity03",
            [],
            ['code',
            'sg_primary_render_layer',
            'sg_additional_render_layers',
            'sg_render_engine',
            ])

            proj_info.update({'sg_3d_settings' : sg_3d_settings})

        return proj_info

    def process_current_session(self, settings, parent_item):
        """
        Analyzes the current scene open in a DCC and parents a subtree of items
        under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """
        # default implementation does not do anything
        pass

    def process_file(self, settings, parent_item, path):
        """
        Analyzes the given file and creates one or more items
        to represent it.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        :param path: Path to analyze

        :returns: The main item that was created, or None if no item was created
            for the supplied path
        """
        # Declaring variables for later
        curr_fields = None
        entity = {}
        task = {}
        step = {}
        camera = {}
        primary_render_folder = []
        additional_render_folder = []

        # a path-swap that converts all pix addresses to pix_artist
        path = re.sub(r"^[/\\]{2}pix[a-zA-Z0-9_\.]+", r"//pix_artist", path)

        # various utilities
        publisher = self.parent
        ctx = publisher.engine.context
        sg_reader = shotgun_utilities.ShotgunReader(shotgun=publisher.shotgun)

        # Path string for manipulation
        path = str(sgtk.util.ShotgunPath.normalize(path)).replace('\\','/')
        self.logger.info('Submission path is: %s' % path)

        # use hijacked method to collect info about the path and folder
        path_info = publisher.util.get_frame_sequence_path( {'path': path, 'ignore_folder_list': [], 'seek_folder_list': []} )
        curr_fields = path_info.get('all_fields')

        if curr_fields:

            # run one large shotgun search to collect entity, task, and step info
            search_fields = self._task_fields( curr_fields )

            filters = [
                ["content", "is", curr_fields['task_name']],
                ["project.Project.id", "is", ctx.project['id']]  
                ]

            entity_type = "entity.%s" % curr_fields['type']
            entity_code = "%s.code" % entity_type
            entity_name = curr_fields['Entity']
            filters.append( [entity_code, "is", entity_name] )

            entity_info = self.sgtk.shotgun.find_one("Task", filters, search_fields)

            # Parse search results into entityl, task, step, and camera
            for key in entity_info:
                key_split = key.split(".")
                set_key = key_split[-1]
                
                if len(key_split) == 1:
                    task[key] = entity_info[key]
                
                if key_split[0] == 'step':
                    step[set_key] = entity_info[key]
                elif "sg_main_plate_camera" in key:
                    camera[set_key] = entity_info[key]
                else:
                    entity[set_key] = entity_info[key]

            # add task id to current fields (holdover from previous version of script)
            if task:
                self.logger.info("Task: %s" %(task))
                curr_fields['id'] = task['entity']['id']

            # evaluate step for 3D-specific settings
            if step:
                self.logger.info("Step: %s" %(step))
                if step['sg_department'] == "3D":
                    if self.project_info['sg_3d_settings']:
                        if self.project_info['sg_3d_settings'][0]['sg_primary_render_layer']:
                            primary_render_folder = self.project_info['sg_3d_settings'][0]['sg_primary_render_layer'].split(",")
                        if self.project_info['sg_3d_settings'][0]['sg_additional_render_layers']:
                            for additional in self.project_info['sg_3d_settings'][0]['sg_additional_render_layers'].split(","):
                                additional_render_folder.append(additional)
                            self.logger.debug("Collected additionals %s. Will publish separately." % (additional_render_folder))
            
            # define plugin visibility/enabled
            plugin_bools = None
            if step:   
                plugin_bools = self._set_plugins_from_sg( step )

        render_folders = {
                        'primary_render_folder': primary_render_folder,
                        'additional_render_folder': additional_render_folder,
                        }

        # collect the main plate, if there is one
        main_plate = self._get_published_main_plate(
                                                    sg_reader, 
                                                    self.project_info.get('id'), 
                                                    entity.get('id') 
                                                    )
                                                    
        entity.update( { 
                        'type': curr_fields['type'],
                        'main_plate': main_plate 
                        } )

        for info in path_info['path_info_returns']:
            
            # Construct dictionary of properties with existing values
            properties = {
                # class properties to pass
                'user_info': self.user_info,
                'codec_info': self.codec_info,
                'project_info': self.project_info,
                'software_info': self.software_info,
                
                # assign properties from path_info values
                'fields': info['fields'],
                'folder_name': info['folder_name'],
                'frame_range': info['file_range'],
                'template': info['base_template'],
                'script_file': curr_fields.get('script_file'),
                
                # step and plugin booleons
                'step': step,
                'sg_publish_to_shotgun': plugin_bools['sg_publish_to_shotgun'],
                'sg_slap_comp': plugin_bools['sg_slap_comp'],
                'sg_version_for_review': plugin_bools['sg_version_for_review'],

                # other shotgun dictionaries
                'entity': entity,
                'task': task,
                'camera': camera,
                
                # vendor info for outsource
                'vendor': curr_fields.get('vendor'),
                'workfile_dir': info.get('workfile_dir'),
                'publish_path': info.get('publish_path'),

                # templates and other quicktime info
                'extra_templates': self._get_extra_templates( info['fields'] ),
                }

            if info['single']:
                if info.get('full_path'):
                    path = info.get('full_path')
                properties['sequence_paths'] = [path]
                self._collect_file(parent_item, path, info, render_folders, properties)
            else:
                if info.get('directory'):
                    path = info.get('directory')
                properties['sequence_paths'] = [ os.path.join( os.path.normpath(path), i ) for i in os.listdir( path ) ]
                self._collect_folder(parent_item, path, info, render_folders, properties)

    def _collect_file(self, parent_item, path, path_info, render_folders, properties, frame_sequence=False):
        """
        Process the supplied file path.

        :param parent_item: parent item instance
        :param path: Path to analyze
        :param frame_sequence: Treat the path as a part of a sequence
        :returns: The item that was created
        """
        self.logger.warning( ">>>>> COLLECT_FILE >>>>>" )
        # self.logger.debug( "Collecting file %s..." % path )

        # make sure the path is normalized. no trailing separator, separators
        # are appropriate for the current os, no double separators, etc.
        path = sgtk.util.ShotgunPath.normalize(path)
        publisher = self.parent

        # get info for the extension
        item_info = self._get_item_info(path)
        item_type = item_info["item_type"]
        type_display = item_info["type_display"]

        display_name = publisher.util.get_publish_name(path, sequence=False)

        # create and populate the item
        file_item = parent_item.create_item(item_type, type_display, display_name)
        file_item.set_icon_from_path(item_info["icon_path"])


        # if the supplied path is an image, use the path as the thumbnail.
        if item_type.startswith("file.image") or item_type.startswith("file.texture"):
            file_item.set_thumbnail_from_path(path)
            thumbnail_path = path

            # disable thumbnail creation since we get it for free
            file_item.thumbnail_enabled = False
        else:
            self.logger.debug("Using icon as thumbnail: %s" %(item_info["icon_path"],))
            file_item.set_thumbnail_from_path(item_info["icon_path"])
            thumbnail_path = item_info["icon_path"]

        # all we know about the file is its path. set the path in its
        # properties for the plugins to use for processing.
        file_item.properties['path'] = path

        self.logger.info("Collected file: %s" % (path,))

        # run helper methods that add universial item properties
        self._run_helper_methods( path, file_item, properties)

        file_item.properties['thumbnail_path'] = thumbnail_path

        self.logger.warning( ">>>>> END COLLECT_FILE >>>>>" )

        return file_item

    def _collect_folder(self, parent_item, folder, path_info, render_folders, properties):

        """
        Process the supplied folder path.

        :param parent_item: parent item instance
        :param folder: Path to analyze
        :returns: The item that was created
        """
        self.logger.warning( ">>>>> COLLECT_FOLDER >>>>>" )
        # self.logger.debug( "Collecting folder contents from %s..." % path )

        # make sure the path is normalized. no trailing separator, separators
        # are appropriate for the current os, no double separators, etc.
        folder = sgtk.util.ShotgunPath.normalize(folder)

        publisher = self.parent
        img_sequences = publisher.util.get_frame_sequences(
            folder, self._get_image_extensions()
        )

        file_items = []

        for (image_seq_path, img_seq_files) in img_sequences:

            # get info for the extension
            item_info = self._get_item_info(image_seq_path)
            item_type = item_info["item_type"]
            type_display = item_info["type_display"]

            # the supplied image path is part of a sequence. alter the
            # type info to account for this.
            type_display = "%s Sequence" % (type_display,)
            item_type = "%s.%s" % (item_type, "sequence")
            icon_name = "image_sequence.png"

            # get the first frame of the sequence. we'll use this for the
            # thumbnail and to generate the display name
            img_seq_files.sort()
            first_frame_file = img_seq_files[0]
            display_name = publisher.util.get_publish_name(
                first_frame_file, sequence=True
            )

            # create and populate the item
            file_item = parent_item.create_item(item_type, type_display, display_name)
            icon_path = self._get_icon_path(icon_name)
            file_item.set_icon_from_path(icon_path)

            # use the first frame of the seq as the thumbnail
            file_item.set_thumbnail_from_path(first_frame_file)

            # disable thumbnail creation since we get it for free
            file_item.thumbnail_enabled = False

            # all we know about the file is its path. set the path in its
            # properties for the plugins to use for processing.
            file_item.properties["path"] = image_seq_path

            self.logger.info("Collected file: %s" % (image_seq_path,))

            # run helper methods that add universial item properties
            self._run_helper_methods( image_seq_path, file_item, properties)

            file_items.append(file_item)

        if not file_items:
            self.logger.warn("No image sequences found in: %s" % (folder,))

        self.logger.warning( ">>>>> END COLLECT_FOLDER >>>>>" )

        return file_items

    def _get_item_info(self, path):
        """
        Return a tuple of display name, item type, and icon path for the given
        filename.

        The method will try to identify the file as a common file type. If not,
        it will use the mimetype category. If the file still cannot be
        identified, it will fallback to a generic file type.

        :param path: The file path to identify type info for

        :return: A dictionary of information about the item to create::

            # path = "/path/to/some/file.0001.exr"

            {
                "item_type": "file.image.sequence",
                "type_display": "Rendered Image Sequence",
                "icon_path": "/path/to/some/icons/folder/image_sequence.png",
                "path": "/path/to/some/file.%04d.exr"
            }

        The item type will be of the form `file.<type>` where type is a specific
        common type or a generic classification of the file.
        """

        publisher = self.parent

        # extract the components of the supplied path
        file_info = publisher.util.get_file_path_components(path)
        extension = file_info["extension"]
        filename = file_info["filename"]

        # default values used if no specific type can be determined
        type_display = "File"
        item_type = "file.unknown"

        # keep track if a common type was identified for the extension
        common_type_found = False

        icon_path = None

        # look for the extension in the common file type info dict
        for display in self.common_file_info:
            type_info = self.common_file_info[display]

            if extension in type_info["extensions"]:
                # found the extension in the common types lookup. extract the
                # item type, icon name.
                type_display = display
                item_type = type_info["item_type"]
                icon_path = type_info["icon"]
                common_type_found = True
                break

        if not common_type_found:
            # no common type match. try to use the mimetype category. this will
            # be a value like "image/jpeg" or "video/mp4". we'll extract the
            # portion before the "/" and use that for display.
            (category_type, _) = mimetypes.guess_type(filename)

            if category_type:

                # mimetypes.guess_type can return unicode strings depending on
                # the system's default encoding. If a unicode string is
                # returned, we simply ensure it's utf-8 encoded to avoid issues
                # with toolkit, which expects utf-8
                category_type = six.ensure_str(category_type)

                # the category portion of the mimetype
                category = category_type.split("/")[0]

                type_display = "%s File" % (category.title(),)
                item_type = "file.%s" % (category,)
                icon_path = self._get_icon_path("%s.png" % (category,))

        # fall back to a simple file icon
        if not icon_path:
            icon_path = self._get_icon_path("file.png")

        # everything should be populated. return the dictionary
        return dict(
            item_type=item_type,
            type_display=type_display,
            icon_path=icon_path,
            )

    def _get_icon_path(self, icon_name, icons_folders=None):
        """
        Helper to get the full path to an icon.

        By default, the app's ``hooks/icons`` folder will be searched.
        Additional search paths can be provided via the ``icons_folders`` arg.

        :param icon_name: The file name of the icon. ex: "alembic.png"
        :param icons_folders: A list of icons folders to find the supplied icon
            name.

        :returns: The full path to the icon of the supplied name, or a default
            icon if the name could not be found.
        """
        # ensure the publisher's icons folder is included in the search
        app_icon_folder = os.path.join(self.disk_location, "icons")

        # build the list of folders to search
        if icons_folders:
            icons_folders.append(app_icon_folder)
        else:
            icons_folders = [app_icon_folder]

        # keep track of whether we've found the icon path
        found_icon_path = None

        # iterate over all the folders to find the icon. first match wins
        for icons_folder in icons_folders:
            icon_path = os.path.join(icons_folder, icon_name)
            if os.path.exists(icon_path):
                found_icon_path = icon_path
                break

        # supplied file name doesn't exist. return the default file.png image
        if not found_icon_path:
            found_icon_path = os.path.join(app_icon_folder, "file.png")

        return found_icon_path

    def _get_image_extensions(self):

        if not hasattr(self, "_image_extensions"):

            image_file_types = [
                "Photoshop Image",
                "Rendered Image",
                "Texture Image"
            ]
            image_extensions = set()

            for image_file_type in image_file_types:
                image_extensions.update(
                    self.common_file_info[image_file_type]["extensions"]
                )


            # get all the image mime type image extensions as well
            mimetypes.init()
            types_map = mimetypes.types_map

            for (ext, mimetype) in types_map.items():

                if mimetype.startswith("image/"):
                    image_extensions.add(ext.lstrip("."))

            self._image_extensions = list(image_extensions)

        return self._image_extensions

    def _set_plugins_from_sg(self, step):

        # Set plugin defaults
        plugins_dict = {
                        "sg_publish_to_shotgun": True,
                        "sg_version_for_review": True,
                        "sg_slap_comp": False
                        }

        # Determine which plugins to load
        for key in plugins_dict:
            if step.get(key) != None:
                plugins_dict[key] = step.get(key)

            if key == "sg_version_for_review":
                if not step.get(key):
                    plugins_dict[key] = True
                else:
                    plugins_dict[key] = False

        self.logger.info("Publish: %s | Version: %s | Slap: %s"%(plugins_dict["sg_publish_to_shotgun"],
                                                plugins_dict["sg_version_for_review"],
                                                plugins_dict["sg_slap_comp"]))
        return plugins_dict

    # set of custom helper methods for cleanliness
    def _run_helper_methods(self, path, item, properties):
        '''
        Run all the helper methods
        '''
        # set default properties and link the task context
        self._add_default_properties( item, properties)
        self._link_task( item )

        # check for existing version
        item.properties['existing_version'] = self._get_existing_version( item )

        # set version_data for creating a version in Shotgun
        item.properties['version_data'] = self.set_version_data( path, item )
        
        # set fields to resolve output path
        item.properties['resolve_fields'] = self.set_resolve_fields( item )
        
        # collect template paths
        item.properties['template_paths'] = self._apply_templates( item )
        
        return item

    def _add_default_properties(self, item, properties):
        '''
        Add the default properties and their values
        to a newly created file item
        '''

        for key in properties.keys():
            item.properties[key] = properties[key]

        return item

    def _link_task(self, item):
        '''
        Use Task ID to set context
        '''
        # self._link_task( file_item, global_info.get('task') )
        if not item.properties.get('task'):
            self.logger.warning('Could not auto-set the context for this item. Not a recognised template patern/naming convention. Please set Task/Link manually')
            return

        task = item.properties.get('task')
        item.context = self.sgtk.context_from_entity("Task", task["id"])
        self.logger.info('Context (Task, Link) is ' + str(self.sgtk.context_from_entity("Task", task["id"])))

        return item

    def _get_ampm(self, now):
        '''
        determine appropriate dailies location
        '''
        ampm =""
        if int(now.strftime("%H")) < 11:
            ampm = "AM"
        elif int(now.strftime("%H")) < 16:
            ampm = "PM"            
        else:   
            ampm = "LATE"
        
        return ampm

    def set_version_data(self, path, item):
        '''
        Set version_data dictionary
        '''
        version_data = {
                        "sg_path_to_frames": path,
                        "project": item.context.project,
                        "sg_task": item.context.task,
                        "entity": item.context.entity,
                        "code": item.properties['existing_version'].get('version_name'),
                        "image": item.properties.get("thumbnail_path"),
                        "frame_range": item.properties.get("frame_range"),                   
                        }
        
        return version_data

    def set_resolve_fields(self, item):
        '''
        gather fields for template constructions
        '''
        entity_type = item.properties['fields']['type']
        publish_name = item.properties['existing_version']['publish_name']
        now = datetime.now()

        resolve_fields = {
                        entity_type: publish_name,
                        'task_name': item.context.task['name'],
                        'name': None,
                        'version': item.properties['existing_version']['version_number'],
                        'ampm': self._get_ampm( now ),
                        'YYYY': now.year,
                        'MM': now.month,
                        'DD': now.day,
                        'sg_asset_type': item.properties['fields'].get('sg_asset_type')
                        }
        
        return resolve_fields

    def _get_published_main_plate(self, sg_reader, project_id, entity_id):
        '''
        Get the main plate 
        '''
        if not (project_id and entity_id):
            self.logger.warning("Could not find Main Plate.")
            return

        published_main_plate = sg_reader.get_pushlished_file(
                                                            project_id, 
                                                            "Main Plate", 
                                                            "Shot", 
                                                            entity_id=entity_id, 
                                                            get_latest=True
                                                            )
        
        self.logger.info( "Got main plate of entity %s - %s" % ( str( entity_id ), published_main_plate ) )
        return published_main_plate

    def _get_extra_templates(self, item):
        '''
        Get assorted templates 
        '''
        publisher = self.parent

        nuke_review_template = publisher.engine.get_template_by_name("nuke_review_template2")
        temp_root_template = publisher.engine.get_template_by_name("temp_shot_root")
        info_json_template = publisher.engine.get_template_by_name('info_json_file')  
        review_process_json_template = publisher.engine.get_template_by_name("review_process_json")

        if item['type'] in [ 'shot', 'Shot', 'SHOT' ]:
            temp_root_template = publisher.engine.get_template_by_name("temp_shot_root")
            info_json_template = publisher.engine.get_template_by_name('info_json_file')
            review_process_json_template = publisher.engine.get_template_by_name("shot_review_process_json")

        elif item['type'] in [ 'asset', 'Asset', 'ASSET' ]:
            temp_root_template = publisher.engine.get_template_by_name("temp_asset_render_root")
            info_json_template = publisher.engine.get_template_by_name('asset_json_file')
            review_process_json_template = publisher.engine.get_template_by_name("asset_review_process_json")
        
        extra_templates = {
                            'nuke_review_template': nuke_review_template,
                            'temp_root_template': temp_root_template,
                            'info_json_template': info_json_template,
                            'review_process_json_template': review_process_json_template,
                            }

        return extra_templates

    def _apply_templates(self, item):
        '''
        Assign paths from templates and check path validity
        '''
        templates = item.properties['extra_templates']
        resolve_fields = item.properties['resolve_fields']

        temp_root = templates['temp_root_template'].apply_fields(resolve_fields)

        fields = {}
        nuke_review_file = templates['nuke_review_template'].apply_fields( fields )
        review_process_json = templates['review_process_json_template'].apply_fields( fields )

        template_paths = {
                            'temp_root': temp_root,
                            'nuke_review_file': nuke_review_file,
                            'review_process_json': review_process_json,
                            }
        
        for i in template_paths:
            template_paths[i] = re.sub( "(\s+)", "-", template_paths[i] )
        
        return template_paths

    def _get_existing_version(self, item):
        '''
        Search for existing version in SG
        '''
        publisher = self.parent

        version_name = ""

        # initial input and basic publisher name
        path = item.properties['path']
        is_sequence = len( item.properties['sequence_paths'] ) > 1
        publish_name = publisher.util.get_publish_name(
                                                        path,
                                                        sequence=is_sequence
                                                        )

        # strip values separated by a . at the end of the name
        while os.path.splitext(publish_name)[1]:
            publish_name = os.path.splitext(publish_name)[0]

        # check for version number and either apply it or v000
        underscore_ver = ""
        version_number = publisher.util.get_version_number(item.properties["path"])
        if not version_number:
            underscore_ver = "_v" + "".zfill(3)
        else:
            underscore_ver = "_v%s" % str(version_number).zfill(3)
    
        version_name = "%s%s" % ( publish_name, underscore_ver )

        # search for version and return result
        existing_version_data = [
            ['project', 'is', {'type': 'Project','id': item.properties['project_info']['id']}],
            ["code", "is", version_name]
        ]
        
        existing_version = publisher.shotgun.find_one("Version", 
                                                    existing_version_data,
                                                    ["code"])

        existing_version= {
                            "version": existing_version,
                            "version_number": version_number,
                            "underscore_ver": underscore_ver,
                            "version_name": version_name,
                            "publish_name": publish_name,
                            }

        self.logger.warning(">>>>> version_name: %s" % version_name)

        return existing_version

    def _task_fields(self, curr_fields):
        
        search_fields = [
                        "entity",
                        ]
        
        search_fields.extend( [
                            "step.Step.id",
                            'step.Step.sg_department',
                            'step.Step.sg_publish_to_shotgun', 
                            'step.Step.sg_version_for_review', 
                            'step.Step.sg_slap_comp', 
                            'step.Step.sg_review_process_type', 
                            'step.Step.entity_type',
                            ])

        entity_type = curr_fields['type']
        if entity_type == "Shot":
            search_fields.extend( [
                                "entity.Shot.code",
                                "entity.Shot.id",
                                "entity.Shot.type",
                                "entity.Shot.description",
                                "entity.Shot.created_by",
                                "entity.Shot.sg_episode",
                                "entity.Shot.sg_shot_lut",
                                "entity.Shot.sg_shot_audio",
                                "entity.Shot.sg_status_list",
                                "entity.Shot.sg_project_name",
                                "entity.Shot.sg_plates_processed_date",
                                "entity.Shot.sg_shot_lut",
                                "entity.Shot.sg_shot_ocio",
                                "entity.Shot.sg_without_ocio",
                                "entity.Shot.sg_head_in",
                                "entity.Shot.sg_tail_out",
                                "entity.Shot.sg_lens_info",
                                "entity.Shot.sg_plate_proxy_scale",
                                "entity.Shot.sg_frame_handles",
                                "entity.Shot.sg_shot_ccc",
                                "entity.Shot.sg_seq_ccc",
                                "entity.Shot.sg_vfx_work",
                                "entity.Shot.sg_scope_of_work",
                                "entity.Shot.sg_editorial_notes",
                                "entity.Shot.sg_sequence"
                                "entity.Shot.sg_main_plate",
                                "entity.Shot.sg_latest_version",
                                "entity.Shot.sg_latest_client_version",
                                "entity.Shot.sg_gamma",
                                "entity.Shot.sg_target_age",
                                "entity.Shot.sg_shot_transform",
                                "entity.Shot.sg_main_plate_camera",
                                "entity.Shot.sg_main_plate_camera.code",
                                "entity.Shot.sg_main_plate_camera.sg_format_width",
                                "entity.Shot.sg_main_plate_camera.sg_format_height",
                                "entity.Shot.sg_main_plate_camera.sg_pixel_aspect_ratio",
                                "entity.Shot.sg_main_plate_camera.sg_pump_incoming_transform_switch",
                                ])
                                
        elif entity_type == "Asset":
            search_fields.extend( [
                                "entity.Asset.code",
                                "entity.Asset.id",
                                "entity.Asset.type",
                                "entity.Asset.description",
                                "entity.Asset.created_by",
                                "entity.Asset.sg_status_list",
                                "entity.Asset.sg_head_in",
                                "entity.Asset.sg_tail_out",
                                "entity.Asset.sg_lens_info",
                                "entity.Asset.sg_vfx_work",
                                "entity.Asset.sg_scope_of_work",
                                "entity.Asset.sg_editorial_notes",
                                "entity.Asset.sg_latest_version",
                                "entity.Asset.sg_latest_client_version"
                                ])

        return search_fields
