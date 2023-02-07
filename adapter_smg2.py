from __future__ import annotations
from pymsb import LMSAdapter, LMSException, BinaryMemoryIO
import io

__all__ = ["SuperMarioGalaxy2Adapter"]


class SuperMarioGalaxy2Adapter(LMSAdapter):
    """
    An adapter to handle game exclusive MSBT/MSBF aspects for Super Mario Galaxy 2.
    """
    def __init__(self):
        super(SuperMarioGalaxy2Adapter, self).__init__()
        self.charset = "utf-16-be"
        self.set_big_endian()

    def use_fixed_buckets(self):
        return True

    @property
    def supports_flows(self) -> bool:
        return True

    # ------------------------------------------------------------------------------------------------------------------

    def read_tag(self, stream: BinaryMemoryIO):
        tag_position = stream.tell()
        group_id = stream.read_u16()
        tag_id = stream.read_u16()
        len_data = stream.read_u16()

        # System
        if group_id == 0:
            if tag_id == 0:
                len_kanji = stream.read_u16()
                len_furigana = stream.read_u16()

                try:
                    furigana = stream.read(len_furigana).decode(self.charset)
                    kanji = stream.read(len_kanji).decode(self.charset)
                except:
                    raise LMSException(f"Couldn't decode ruby characters (tag at 0x{tag_position})")

                return f'[ruby:{kanji};{furigana}]'

            if tag_id == 3:
                if len_data != 2:
                    raise LMSException(f"Color tag length should be 2 (tag at 0x{tag_position})")

                color_id = stream.read_u16()

                if color_id == 0xFFFF:
                    return '[defcolor]'

                if 0 <= color_id < len(self.FONT_COLORS):
                    return f'[color:{self.FONT_COLORS[color_id]}]'

                raise LMSException(f"Illegal Color tag color ID: {color_id} (tag at 0x{tag_position})")

        # Display
        elif group_id == 1:
            if tag_id == 0:
                if len_data != 2:
                    raise LMSException(f"Wait tag length should be 2 (tag at 0x{tag_position})")

                wait_time = stream.read_u16()
                return f'[wait:{wait_time}]'
            elif tag_id == 1:
                if len_data != 0:
                    raise LMSException(f"Page break tag length should be 0 (tag at 0x{tag_position})")

                return '[pagebreak]'
            elif tag_id == 2:
                if len_data != 0:
                    raise LMSException(f"Offset page tag length should be 0 (tag at 0x{tag_position})")

                return '[ycenter]'
            elif tag_id == 3:
                if len_data != 0:
                    raise LMSException(f"Center page tag length should be 0 (tag at 0x{tag_position})")

                return '[xcenter]'

        # Sound
        elif group_id == 2:
            if len_data < 2:
                raise LMSException(f"Minimum Sound tag length should be 2 (tag at 0x{tag_position})")

            len_sound = stream.read_u16()
            raw_sound = stream.read(len_sound)
            sound_name = raw_sound.decode(self.charset)

            return f'[sound:{sound_name}]'

        # Picture
        elif group_id == 3:
            if len_data != 2:
                raise LMSException(f"Picture group tag length should be 2 (tag at 0x{tag_position})")

            picture_offset = stream.read_u16()

            if 0 <= tag_id < len(self.PICTURE_NAMES):
                return f'[icon:{self.PICTURE_NAMES[tag_id]}]'

            raise LMSException(f"Illegal Picture group tag ID: {tag_id} (tag at 0x{tag_position})")

        # FontSize
        elif group_id == 4:
            if len_data != 0:
                raise LMSException(f"FontSize group tag length should be 0 (tag at 0x{tag_position})")

            if 0 <= tag_id < len(self.FONT_SIZES):
                return f'[size:{self.FONT_SIZES[tag_id]}]'

            raise LMSException(f"Illegal FontSize group tag ID: {tag_id} (tag at 0x{tag_position})")

        # Localize
        elif group_id == 5:
            if len_data != 2:
                raise LMSException(f"Localize group tag length should be 2 (tag at 0x{tag_position})")

            if tag_id == 0:
                preset_type = stream.read_u8()
                unknown_arg = stream.read_u8()
                return f'[player:{preset_type}]'

            raise LMSException(f"Illegal Localize group tag ID: {tag_id} (tag at 0x{tag_position})")

        # Number
        elif group_id == 6:
            if len_data != 8:
                raise LMSException(f"Number group tag length should be 8 (tag at 0x{tag_position})")

            default_value = stream.read_s32()
            va_arg_idx = stream.read_u32()
            return f'[intvar:{tag_id};{va_arg_idx};{default_value}]'

        # String
        elif group_id == 7:
            if len_data != 8:
                raise LMSException(f"String group tag length should be 8 (tag at 0x{tag_position})")

            unknown_arg_1 = stream.read_u32()
            va_arg_idx = stream.read_u32()
            return f'[stringvar:{tag_id};{va_arg_idx};0x{unknown_arg_1:08X}]'

        # RaceTime
        elif group_id == 9:
            if len_data != 0:
                raise LMSException(f"RaceTime group tag length should be 0 (tag at 0x{tag_position})")

            if 0 <= tag_id < len(self.RACE_TIMES):
                return f'[race:{self.RACE_TIMES[tag_id]}]'

            raise LMSException(f"Illegal RaceTime group tag ID: {tag_id} (tag at 0x{tag_position})")

        # Font
        elif group_id == 10:
            if len_data < 2:
                raise LMSException(f"Minimum Sound tag length should be 2 (tag at 0x{tag_position})")

            len_sound = stream.read_u16()
            raw_sound = stream.read(len_sound)
            sound_name = raw_sound.decode(self.charset)

            return f'[numberfont:{sound_name}]'

        data = stream.read(len_data)
        return f"[{group_id}:{tag_id};{data.hex()}]"

    # ------------------------------------------------------------------------------------------------------------------

    def write_tag(self, stream: BinaryMemoryIO, tag: str):
        if tag.find(":") >= 0:
            tag_name, tag_attrs = tag.split(":", 1)
            tag_name = tag_name.strip()
            tag_attrs = tag_attrs.strip().split(";")
        else:
            tag_name = tag.strip()
            tag_attrs = ()

        if tag_name == "":
            raise LMSException("Empty tag found!")

        # System
        if tag_name == "ruby":
            self._verify_tag_attr_size_(tag_name, tag_attrs, 2, tag)

            try:
                encoded_kanji = tag_attrs[0].encode(self.charset)
                encoded_furigana = tag_attrs[1].encode(self.charset)
            except Exception:
                raise LMSException(f"Couldn't write ruby tag. Full tag was '{tag}'")

            data_size = 4 + len(encoded_kanji) + len(encoded_furigana)

            self._write_tag_info_(stream, 0, 0, data_size)
            stream.write_u16(len(encoded_kanji))
            stream.write_u16(len(encoded_furigana))
            stream.write(encoded_furigana)
            stream.write(encoded_kanji)

        elif tag_name == "defcolor":
            self._verify_tag_attr_size_(tag_name, tag_attrs, 0, tag)
            self._write_tag_info_(stream, 0, 3, 2)
            stream.write_u16(0xFFFF)

        elif tag_name == "color":
            self._verify_tag_attr_size_(tag_name, tag_attrs, 1, tag)
            color_name = tag_attrs[0]

            if color_name in self.FONT_COLORS:
                color_id = self.FONT_COLORS.index(color_name)
            else:
                raise LMSException(f"Invalid text color '{color_name}', full tag was '{tag}'")

            self._write_tag_info_(stream, 0, 3, 2)
            stream.write_u16(color_id)

        # Display
        elif tag_name == "wait":
            self._verify_tag_attr_size_(tag_name, tag_attrs, 1, tag)
            wait_time = self._get_tag_attr_u16_(tag_attrs[0], tag)

            self._write_tag_info_(stream, 1, 0, 2)
            stream.write_u16(wait_time)

        elif tag_name == "pagebreak":
            self._verify_tag_attr_size_(tag_name, tag_attrs, 0, tag)
            self._write_tag_info_(stream, 1, 1, 0)

        elif tag_name == "ycenter":
            self._verify_tag_attr_size_(tag_name, tag_attrs, 0, tag)
            self._write_tag_info_(stream, 1, 2, 0)

        elif tag_name == "xcenter":
            self._verify_tag_attr_size_(tag_name, tag_attrs, 0, tag)
            self._write_tag_info_(stream, 1, 3, 0)

        # Sound
        elif tag_name == "sound":
            self._verify_tag_attr_size_(tag_name, tag_attrs, 1, tag)
            sound_name = tag_attrs[0]
            encoded_name = sound_name.encode(self.charset)
            encoded_len = len(encoded_name)

            self._write_tag_info_(stream, 2, 0, 2 + encoded_len)
            stream.write_u16(encoded_len)
            stream.write(encoded_name)

        # Picture
        elif tag_name == "icon":
            self._verify_tag_attr_size_(tag_name, tag_attrs, 1, tag)
            icon_name = tag_attrs[0]

            if icon_name in self.PICTURE_NAMES:
                tag_id = self.PICTURE_NAMES.index(icon_name)
            else:
                raise LMSException(f"Invalid icon name '{icon_name}', full tag was '{tag}'")

            self._write_tag_info_(stream, 3, tag_id, 2)
            stream.write_u16(self.PICTURE_CODES[tag_id])

        # FontSize
        elif tag_name == "size":
            self._verify_tag_attr_size_(tag_name, tag_attrs, 1, tag)
            size_name = tag_attrs[0]

            if size_name in self.FONT_SIZES:
                tag_id = self.FONT_SIZES.index(size_name)
            else:
                raise LMSException(f"Invalid font size '{size_name}', full tag was '{tag}'")

            self._write_tag_info_(stream, 4, tag_id, 0)

        # Localize
        elif tag_name == "player":
            self._verify_tag_attr_size_(tag_name, tag_attrs, 1, tag)
            preset_type = self._get_tag_attr_u8_(tag_attrs[0], tag)

            self._write_tag_info_(stream, 5, 0, 2)
            stream.write_u8(preset_type)
            stream.write_u8(0xCD)

        # Number
        elif tag_name == "intvar":
            self._verify_tag_attr_size_(tag_name, tag_attrs, 3, tag)
            tag_id = self._get_tag_attr_u16_(tag_attrs[0], tag)
            va_arg_idx = self._get_tag_attr_u32_(tag_attrs[1], tag)
            def_val = self._get_tag_attr_s32_(tag_attrs[2], tag)

            self._write_tag_info_(stream, 6, tag_id, 8)
            stream.write_u32(def_val)
            stream.write_u32(va_arg_idx)

        # String
        elif tag_name == "stringvar":
            self._verify_tag_attr_size_(tag_name, tag_attrs, 3, tag)
            tag_id = self._get_tag_attr_u16_(tag_attrs[0], tag)
            va_arg_idx = self._get_tag_attr_u32_(tag_attrs[1], tag)
            def_ptr = self._get_tag_attr_u32_(tag_attrs[2], tag)

            self._write_tag_info_(stream, 7, tag_id, 8)
            stream.write_u32(def_ptr)
            stream.write_u32(va_arg_idx)

        # RaceTime
        elif tag_name == "race":
            self._verify_tag_attr_size_(tag_name, tag_attrs, 1, tag)
            race_name = tag_attrs[0]

            if race_name in self.RACE_TIMES:
                tag_id = self.RACE_TIMES.index(race_name)
            else:
                raise LMSException(f"Invalid race name '{race_name}', full tag was '{tag}'")

            self._write_tag_info_(stream, 9, tag_id, 0)

        # Font
        elif tag_name == "numberfont":
            self._verify_tag_attr_size_(tag_name, tag_attrs, 1, tag)
            number_text = tag_attrs[0]

            encoded_text = number_text.encode(self.charset)
            encoded_len = len(encoded_text)

            self._write_tag_info_(stream, 10, 0, 2 + encoded_len)
            stream.write_u16(encoded_len)
            stream.write(encoded_text)

        else:
            self._verify_tag_attr_size_(tag_name, tag_attrs, 2, tag)
            tag_id = self._get_tag_attr_u16_(tag_name, tag)
            group_id = self._get_tag_attr_u16_(tag_attrs[0], tag)

            try:
                data = bytes.fromhex(tag_attrs[1])
                len_data = len(data)
            except Exception:
                raise LMSException(f"Couldn't write arbitrary tag. Full tag was '{tag}'")

            if len_data & 1:
                self._write_tag_info_(stream, tag_id, group_id, len_data + 1)
                stream.write(data)
                stream.write_u8(0)
            else:
                self._write_tag_info_(stream, tag_id, group_id, len(data))
                stream.write(data)

    def _write_tag_info_(self, stream: BinaryMemoryIO, group_id: int, tag_id: int, data_size: int):
        self.write_chars(stream, "\u000E")
        stream.write_u16(group_id)
        stream.write_u16(tag_id)
        stream.write_u16(data_size)

    def _verify_tag_attr_size_(self, tag_name: str, tag_attrs: tuple[...], expected_size: int, tag: str):
        if len(tag_attrs) != expected_size:
            raise LMSException(f"Unexpected attributes count for tag '{tag_name}'. Expected {expected_size}, "
                               f"found {len(tag_attrs)}. Full tag was '{tag}'")

    def _get_tag_attr_u8_(self, attr: str, tag: str) -> int:
        try:
            value = int(attr, 0)
        except Exception:
            raise LMSException(f"Couldn't parse tag attribute '{attr}' as integer. Full tag was '{tag}'")
        if value < 0 or 255 < value:
            raise LMSException(f"Tag attribute '{value}' out of range. Full tag was {tag}")
        return value

    def _get_tag_attr_u16_(self, attr: str, tag: str) -> int:
        try:
            value = int(attr, 0)
        except Exception:
            raise LMSException(f"Couldn't parse tag attribute '{attr}' as integer. Full tag was '{tag}'")
        if value < 0 or 65535 < value:
            raise LMSException(f"Tag attribute '{value}' out of range. Full tag was {tag}")
        return value

    def _get_tag_attr_s32_(self, attr: str, tag: str) -> int:
        try:
            value = int(attr, 0)
        except Exception:
            raise LMSException(f"Couldn't parse tag attribute '{attr}' as integer. Full tag was '{tag}'")
        if value < -0x80000000 or 0x7FFFFFFF < value:
            raise LMSException(f"Tag attribute '{value}' out of range. Full tag was {tag}")
        return value

    def _get_tag_attr_u32_(self, attr: str, tag: str) -> int:
        try:
            value = int(attr, 0)
        except Exception:
            raise LMSException(f"Couldn't parse tag attribute '{attr}' as integer. Full tag was '{tag}'")
        if value < 0 or 0xFFFFFFFF < value:
            raise LMSException(f"Tag attribute '{value}' out of range. Full tag was {tag}")
        return value

    # ------------------------------------------------------------------------------------------------------------------

    @property
    def supports_attributes(self):
        return True

    @property
    def attributes_size(self) -> int:
        return 12

    def create_default_attributes(self):
        return {
            "talk_type": 0,
            "balloon_type": 0,
            "msg_link_id": 255,
            "sound_id": 1,
            "camera_type": 0,
            "camera_id": 0,
            "unk7": 255,
            "comment": ""
        }

    def parse_attributes(self, stream: BinaryMemoryIO, root_offset: int, root_size: int) -> dict:
        end_offset = root_offset + root_size

        # Read attributes
        sound_id = stream.read_u8()
        camera_type = stream.read_u8()
        talk_type = stream.read_u8()
        balloon_type = stream.read_u8()
        camera_id = stream.read_u16()
        msg_link_id = stream.read_u8()
        unk7 = stream.read_u8()
        off_comment = stream.read_u32()

        # Read comment string
        stream.seek(root_offset + off_comment)
        comment = ""

        while root_offset < end_offset:
            ch = self.read_char(stream)

            if ch == "\0":
                break
            else:
                comment += ch

        # Pack and return result
        return {
            "talk_type": talk_type,
            "balloon_type": balloon_type,
            "msg_link_id": msg_link_id,
            "sound_id": sound_id,
            "camera_type": camera_type,
            "camera_id": camera_id,
            "unk7": unk7,
            "comment": comment
        }

    def write_attributes(self, stream: BinaryMemoryIO, attributes: dict):
        stream.write_u8(attributes.get("sound_id", 1))
        stream.write_u8(attributes.get("camera_type", 0))
        stream.write_u8(attributes.get("talk_type", 0))
        stream.write_u8(attributes.get("balloon_type", 0))
        stream.write_u16(attributes.get("camera_id", 0))
        stream.write_u8(attributes.get("msg_link_id", 255))
        stream.write_u8(attributes.get("unk7", 255))
        stream.write_u32(stream.size)

        stream.seek(0, io.SEEK_END)
        self.write_chars(stream, attributes.get("comment", "") + "\0")

    # ------------------------------------------------------------------------------------------------------------------

    FONT_COLORS = ["black", "red", "green", "blue", "yellow", "purple", "orange", "grey"]
    FONT_SIZES = ["small", "normal", "large"]
    RACE_TIMES = ["jungle_glider", "challenge_glider", "last"]
    PICTURE_CODES = list(range(0, 44)) + list(range(49, 78))
    PICTURE_NAMES = [
        "a_button",
        "b_button",
        "c_button",
        "wiimote",
        "nunchuck",
        "1_button",
        "2_button",
        "star",
        "launch_star",
        "pull_star",
        "pointer",
        "purple_starbit",
        "coconut",
        "orange_arrow",
        "star_bunny",
        "analog_stick",
        "x_mark",
        "coin",
        "mario",
        "dpad",
        "blue_chip",
        "star_chip",
        "home_button",
        "minus_button",
        "plus_button",
        "z_button",
        "silver_star",
        "grand_star",
        "luigi",
        "co_pointer",
        "purple_coin",
        "green_comet",
        "gold_crown",
        "cross_hair",
        "blank",
        "bowser",
        "hand_grab",
        "hand_point",
        "hand_hold",
        "rainbow_starbit",
        "peach",
        "letter",
        "white_qmark",
        "current_player",
        "1up_mushroom",
        "life_mushroom",
        "hungry_luma",
        "luma",
        "comet",
        "green_qmark",
        "stopwatch",
        "master_luma",
        "yoshi",
        "comet_medal",
        "silver_crown",
        "yoshi_grapple",
        "checkpoint_flag",
        "empty_star",
        "empty_comet_medal",
        "empty_comet",
        "empty_secret_star",
        "bronze_star",
        "blimp_fruit",
        "platinum_crown",
        "bronze_grand_star",
        "topman",
        "goomba",
        "coins",
        "dpad_up",
        "dpad_down",
        "orange_luma",
        "toad",
        "bronze_comet"
    ]

    TALK_TYPES = ["Normal", "Shout", "Auto", "Global"]
    BALLOON_TYPES = ["White box", "White box (1)", "\"Call\"", "Signboard", "Icon bubble"]
    CAMERA_TYPES = ["Normal", "Event"]
    MESSAGE_SOUNDS = [
        "null (0)",
        "Default",
        "SE_SV_KINOPIO_TALK_HEY",
        "SE_SV_KINOPIO_TALK_YAHOO",
        "SE_SV_KINOPIO_TALK_ANGRY",
        "SE_SV_KINOPIO_TALK_SAD",
        "SE_SV_KINOPIO_TALK_HAPPY",
        "SE_SV_KINOPIO_TALK_SLEEP",
        "SE_SV_KINOPIO_TALK_WELCOME",
        "SE_SV_KINOPIO_TALK_BEAUTIFUL",
        "SE_SV_KINOPIO_TALK_SURPRISE",
        "SE_SV_KINOPIO_PUHA",
        "SE_SV_KINOPIO_TALK_HELP",
        "SE_SV_KINOPIO_TALK_TREMBLE",
        "SE_SV_KINOPIO_TALK_STRONG",
        "SE_SV_KINOPIO_TALK_LOOK_OUT",
        "SE_SV_KINOPIO_TALK_WOW",
        "SE_SV_KINOPIO_TALK_WATER",
        "SE_SV_KINOPIO_TALK_HEY_SNOR",
        "SE_SV_KINOPIO_TALK_SAD_SNOR",
        "SE_SV_KINOPIO_NO_MAIL",
        "SE_SV_KINOPIO_LOOK_MAIL",
        "SE_SV_KINOPIO_TALK_SHOUT",
        "SE_SV_KINOPIO_TALK_TIRED",
        "SE_SV_KINOPIO_TALK_JOYFUL",
        "SE_SV_RABBIT_TALK_NORMAL",
        "SE_SV_RABBIT_TALK_CAUGHT",
        "SE_SV_RABBIT_TALK_THATS",
        "SE_SV_RABBIT_TALK_HELP",
        "SE_SV_RABBIT_TALK_THANKS",
        "SE_SV_PENGUIN_L_TALK_NORMAL",
        "SE_SV_PENGUIN_L_TALK_PLEASED",
        "SE_SV_PENGUIN_L_TALK_NG",
        "SE_SV_PENGUIN_L_TALK_QUESTION",
        "SE_SV_PENGUIN_L_TALK_DISTANT",
        "SE_SV_PENGUIN_L_TALK_NORMAL_L",
        "SE_SV_PENGUIN_L_TALK_PLEASED_L",
        "SE_SV_PENGUIN_L_TALK_NG_L",
        "SE_SV_PENGUIN_L_TALK_QUESTION_L",
        "SE_SV_PENGUIN_L_TALK_OH",
        "SE_SV_PENGUIN_S_TALK_NORMAL",
        "SE_SV_PENGUIN_S_TALK_GLAD",
        "SE_SV_PENGUIN_S_TALK_GLAD_HIGH",
        "SE_SV_PENGUIN_S_TALK_ANGRY",
        "SE_SV_PENGUIN_S_TALK_SAD",
        "SE_SV_PENGUIN_S_TALK_HAPPY",
        "SE_SV_PENGUIN_S_TALK_STRONG",
        "SE_SV_PENGUIN_S_TALK_NORMAL_W",
        "SE_SV_PENGUIN_S_TALK_GREET",
        "SE_SV_PENGUIN_S_TALK_WIN",
        "SE_SV_PENGUIN_S_TALK_LOSE",
        "SE_SV_PENGUIN_S_TALK_OUCH",
        "SE_SV_PENGUIN_ACE_TALK_NORMAL",
        "SE_SV_PENGUIN_ACE_TALK_GREET",
        "SE_SV_PENGUIN_ACE_TALK_WIN",
        "SE_SV_PENGUIN_ACE_TALK_LOSE",
        "SE_SV_PENGUIN_SS_HAPPY",
        "SE_SV_PENGUIN_SS_GREET",
        "SE_SV_PENGUIN_SS_DAMAGE",
        "SE_SV_PENGUIN_SS_DISAPPOINTED",
        "SE_SV_PENGUIN_SS_PLEASED",
        "SE_SV_PENGUIN_SS_ANGRY",
        "SE_SV_HONEYBEE_TALK_NORMAL",
        "SE_SV_HONEYBEE_TALK_CONFUSION",
        "SE_SV_HONEYBEE_TALK_QUESTION",
        "SE_SV_HONEYBEE_TALK_SURPRISE",
        "SE_SV_HONEYBEE_TALK_ORDER",
        "SE_SV_HONEYBEE_TALK_LAUGH",
        "SE_SV_HONEYBEE_TALK_GLAD",
        "SE_SV_HONEYBEE_TALK_SLEEP",
        "SE_SV_TICO_TALK_NORMAL",
        "SE_SV_TICO_TALK_GLAD",
        "SE_SV_TICO_TALK_ANGRY",
        "SE_SV_TICO_TALK_SAD",
        "SE_SV_TICO_TALK_HAPPY",
        "SE_SV_TICO_TICO",
        "SE_SV_TICO_TALK_CONFUSION",
        "SE_SV_TICO_TALK_THANKS",
        "SE_SV_TICO_TALK_DIST_HALF_GLAD",
        "SE_SV_TICO_TALK_DIST_HALF_NORMAL",
        "null (80)",
        "SE_SV_LUIGI_FRIGHTENED",
        "null (82)",
        "null (83)",
        "SE_SV_LUIGI_HEY",
        "SE_DM_KINOPIO_CHIEF",
        "SE_SV_CARETAKER_SHORT",
        "SE_SV_CARETAKER_NORMAL",
        "SE_SV_CARETAKER_LONG",
        "SE_SV_CARETAKER_REPEAT",
        "SE_SV_PEACH_TALK_HELP",
        "SE_SV_ROSETTA_TALK_NORMAL",
        "null (92)",
        "null (93)",
        "null (94)",
        "null (95)",
        "SE_SV_TICOFAT_TALK_NORMAL",
        "SE_SV_TICOFAT_TALK_KITA",
        "SE_SV_TICOFAT_META",
        "SE_SV_KINOPIOCHIEF_TALK_HEY",
        "SE_SV_KINOPIOCHIEF_TALK_LAUGH",
        "SE_SV_KINOPIOCHIEF_TALK_YAHOO",
        "SE_SV_TICOFAT_TALK_GIVE_ME",
        "SE_SV_TICOFAT_TALK_WAKU",
        "SE_SV_BUTLER_TALK_SURPRISE",
        "SE_SV_BUTLER_TALK_AGREE",
        "SE_SV_BUTLER_TALK_WORRIED",
        "SE_SV_BUTLER_TALK_NORMAL",
        "SE_SV_PENGUIN_OLD_GREET",
        "SE_SV_PENGUIN_OLD_GRAD",
        "SE_SV_PENGUIN_OLD_SAD",
        "SE_SV_PENGUIN_OLD_NORMAL",
        "SE_SV_LUIGI_TALK_TIRE",
        "SE_SV_LUIGI_TALK_YAH",
        "null (114)",
        "SE_SV_LUIGI_TALK_OH_YEAH",
        "SE_SV_BUTLER_TALK_QUESTION",
        "null (117)",
        "null (118)",
        "SE_SV_PENGUIN_OLD_SCARED",
        "SE_SV_TICOCOMET_TALK_PURURIN",
        "SE_SV_TICOCOMET_TALK_DON",
        "SE_SV_TICOSHOP_TALK_PIKARIN",
        "SE_SV_TICOSHOP_TALK_KITA",
        "SE_BV_KOOPAJR_TLK_PROVOKE",
        "SE_BV_KOOPA_TLK_LAUGH",
        "SE_BV_KOOPA_TLK_NORMAL",
        "SE_BV_KOOPA_TLK_REGRET",
        "SE_BV_KOOPA_TLK_CALM",
        "SE_BV_KOOPA_TLK_EXCITED",
        "SE_SV_TICOFAT_TALK_YEAH",
        "null (131)",
        "SE_SV_CARE_TAKER_TRAMPLE",
        "SE_SV_KINOPIOCHIEF_TALK_EVASIVE",
        "null (134)",
        "null (135)",
        "SE_SV_SIGNBOARD_HEY",
        "null (137)",
        "null (138)",
        "null (139)",
        "null (140)",
        "null (141)",
        "null (142)",
        "SE_SV_CARETAKER_ANGRY_FAST",
        "SE_SV_HONEYQUEEN_TALK_SURPRISE",
        "SE_SV_HONEYQUEEN_TALK_THANKS",
        "SE_SV_HONEYQUEEN_TALK_WORRY",
        "SE_SV_HONEYQUEEN_TALK_AA",
        "SE_SV_HONEYQUEEN_TALK_AN",
        "SE_SV_HONEYQUEEN_TALK_UFUFU",
        "SE_SV_TICOBIG_TALK_NORMAL",
        "SE_SV_TICOBIG_TALK_GLAD",
        "SE_SV_TICOBIG_TRAMPLED",
        "SE_SV_PICHAN_TALK_NORMAL",
        "SE_SV_PICHAN_TALK_GLAD",
        "SE_SV_PICHAN_TALK_ANGRY",
        "SE_SV_PICHAN_TALK_SAD",
        "SE_SV_PICHAN_TALK_HAPPY",
        "SE_SV_PICHAN_TALK_DIFFICULT",
        "SE_SV_BOMBHEI_RED_TALK_NORMAL",
        "SE_SV_BOMBHEI_RED_TALK_SHORT",
        "SE_SV_MONTE_TALK_NORMAL",
        "SE_SV_MONTE_TALK_ANGRY",
        "SE_SV_MONTE_TALK_SURPRISE",
        "SE_SV_MONTE_TALK_PROUD",
        "SE_SV_MONTE_TALK_WELCOME",
        "SE_SV_MONTE_TALK_QUESTION",
        "SE_SV_MEISTER_TALK_NORMAL",
        "SE_SV_MEISTER_TALK_QUESTION",
        "SE_SV_MEISTER_TALK_NOT_SEEN",
        "SE_SV_MEISTER_TALK_BAD",
        "SE_SV_MEISTER_TALK_STRONG",
        "SE_SV_MEISTER_TALK_ALL_RIGHT",
        "SE_SV_MEISTER_TALK_BOAST",
        "SE_SV_MEISTER_TALK_UN",
        "SE_SV_MEISTER_TALK_HAHAN",
        "SE_SV_MEISTER_TALK_EAT1",
        "SE_SV_MEISTER_TALK_EAT2",
        "SE_SV_SASURAI_TALK_NORMAL",
        "SE_SV_SASURAI_TALK_QUESTION",
        "SE_SV_SASURAI_TALK_ALL_RIGHT",
        "SE_SV_SASURAI_TALK_DO_BEST",
        "SE_SV_SASURAI_TALK_EXCELLENT",
        "SE_SV_SASURAI_TALK_REGRET",
        "SE_BV_BATTANKING_TALK_EIO",
        "SE_BV_BATTANKING_TALK_OI",
        "SE_SV_HELPERWITCH_TALK_SMILE",
        "SE_SV_HELPERWITCH_TALK_SMILE_2",
        "SE_SV_HELPERWITCH_TALK_LOOK",
        "SE_SV_HELPERWITCH_TALK_AHA",
        "SE_SV_HINT_TV_TALK_SUGGEST",
        "SE_SV_HINT_TV_TALK_OK",
        "SE_SV_PEACH_NPC_THANK_YOU"
    ]
