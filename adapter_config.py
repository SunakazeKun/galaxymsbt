from adapter_smg2 import SuperMarioGalaxy2Adapter
from typing import Any

import os
import json

__all__ = ["initialize_custom_smg2_adapter_maker"]


__CONFIG_FILE_NAME__ = "adapter_config.json"


def initialize_custom_smg2_adapter_maker() -> type[SuperMarioGalaxy2Adapter]:
    """
    Creates a copy of the SMG2 adapter class using the information provided in the config file. The resulting class copy
    will be returned.

    :return: a copy of the SMG2 adapter class.
    """
    adapter_maker: type[SuperMarioGalaxy2Adapter] = type("CustomSuperMarioGalaxy2Adapter",
                                                         tuple([SuperMarioGalaxy2Adapter]),
                                                         dict(SuperMarioGalaxy2Adapter.__dict__))
    config_data: dict[str, Any] | None = None

    # Try to load config data from file
    if os.path.isfile(__CONFIG_FILE_NAME__):
        with open(__CONFIG_FILE_NAME__, "r", encoding="utf-8-sig") as f:
            config_data = json.load(f)

    # Create config file from default data if missing
    if config_data is None:
        picture_icons = {name: code for name, code in zip(adapter_maker.PICTURE_NAMES, adapter_maker.PICTURE_CODES)}
        config_data = {
            "font_colors": adapter_maker.FONT_COLORS,
            "font_sizes": adapter_maker.FONT_SIZES,
            "race_times": adapter_maker.RACE_TIMES,
            "picture_icons": picture_icons,
            "message_sounds": adapter_maker.MESSAGE_SOUNDS,
            "talk_types": adapter_maker.TALK_TYPES,
            "balloon_types": adapter_maker.BALLOON_TYPES,
            "camera_types": adapter_maker.CAMERA_TYPES
        }

        with open(__CONFIG_FILE_NAME__, "w", encoding="utf-8-sig") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)

        return adapter_maker

    # Verify syntax of config is correct
    if type(config_data) != dict:
        raise SyntaxError("Can't parse config because root element is not a dict")

    _check_list_and_elements_type_(config_data, "font_colors", str)
    _check_list_and_elements_type_(config_data, "font_sizes", str)
    _check_list_and_elements_type_(config_data, "race_times", str)
    _check_dict_and_elements_type_(config_data, "picture_icons", int)
    _check_list_and_elements_type_(config_data, "message_sounds", str)
    _check_list_and_elements_type_(config_data, "talk_types", str)
    _check_list_and_elements_type_(config_data, "balloon_types", str)
    _check_list_and_elements_type_(config_data, "camera_types", str)

    # Overwrite adapter maker's lists
    if "font_colors" in config_data:
        adapter_maker.FONT_COLORS = config_data["font_colors"]

    if "font_sizes" in config_data:
        adapter_maker.FONT_SIZES = config_data["font_sizes"]

    if "race_times" in config_data:
        adapter_maker.RACE_TIMES = config_data["race_times"]

    if "picture_icons" in config_data:
        picture_names = list(config_data["picture_icons"].keys())
        picture_codes = list(config_data["picture_icons"].values())
        adapter_maker.PICTURE_NAMES = picture_names
        adapter_maker.PICTURE_CODES = picture_codes

    if "message_sounds" in config_data:
        adapter_maker.MESSAGE_SOUNDS = config_data["message_sounds"]

    if "talk_types" in config_data:
        adapter_maker.TALK_TYPES = config_data["talk_types"]

    if "balloon_types" in config_data:
        adapter_maker.BALLOON_TYPES = config_data["balloon_types"]

    if "camera_types" in config_data:
        adapter_maker.CAMERA_TYPES = config_data["camera_types"]

    return adapter_maker


def _check_list_and_elements_type_(config_data: dict, key: str, element_type: type):
    if key not in config_data:
        return

    if type(config_data[key]) != list:
        raise SyntaxError(f"Config entry '{key}' is not a list")

    for element in config_data[key]:
        if type(element) != element_type:
            raise SyntaxError(f"Not all entries for config entry '{key}' are of type '{str(element_type)}'")


def _check_dict_and_elements_type_(config_data: dict, key: str, element_type: type):
    if key not in config_data:
        return

    if type(config_data[key]) != dict:
        raise SyntaxError(f"Config entry '{key}' is not a dict")

    for element in config_data[key].values():
        if type(element) != element_type:
            raise SyntaxError(f"Not all values for config entry '{key}' are of type '{str(element_type)}'")
