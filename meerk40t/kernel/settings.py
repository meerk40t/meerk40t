import ast
from configparser import ConfigParser, MissingSectionHeaderError, NoSectionError
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Union

from .functions import get_safe_path


class Settings:
    """
    Settings are thin interface with the configparser within python. Conceptually it's a
    dictionary of dictionaries. The first dictionary key are called sections, and the sub-
    section are attributes. To save a list of related settings we add a space within the
    section name. E.g. `operation 0001` or `operation 0002` etc. The first element can be
    divided up with various layers of `/` to make derivable subdirectories of settings.

    Reading/writing and deleting are performed on the config_dict which stores a set of values
    these are loaded during the `read_configuration` step and are committed to disk when
    `write_configuration` is called.
    """

    def __init__(self, directory, filename, ignore_settings=False):
        self._config_file = Path(get_safe_path(directory, create=True)).joinpath(
            filename
        )
        self._config_dict = {}
        if not ignore_settings:
            self.read_configuration()

    def __contains__(self, item):
        return item in self._config_dict

    def read_configuration(self, targetfile=None):
        """
        Read configuration reads the self._config_file to get the parsed config file data.

        Circa 0.8.0 this uses ConfigParser() in python rather than FileConfig in wxPython

        @return:
        """
        if targetfile is None:
            targetfile = self._config_file
        try:
            parser = ConfigParser()
            parser.read(targetfile, encoding="utf-8")
            for section in parser.sections():
                for option in parser.options(section):
                    try:
                        config_section = self._config_dict[section]
                    except KeyError:
                        config_section = dict()
                        self._config_dict[section] = config_section
                    config_section[option] = parser.get(section, option)
        except (
            PermissionError,
            NoSectionError,
            MissingSectionHeaderError,
            FileNotFoundError,
        ):
            return

    def write_configuration(self, targetfile=None):
        """
        Write configuration writes the config file to disk. This is typically done during the shutdown process.

        This uses the python ConfigParser to save data from the _config_dict.
        @return:
        """
        if targetfile is None:
            targetfile = self._config_file
        try:
            parser = ConfigParser()
            for section_key in self._config_dict:
                section = self._config_dict[section_key]
                for key in section:
                    value = section[key]
                    try:
                        if "%" in value:
                            value = value.replace("%", "%%")
                        parser.set(section_key, key, value)
                    except NoSectionError:
                        parser.add_section(section_key)
                        parser.set(section_key, key, value)
            with open(targetfile, "w", encoding="utf-8") as fp:
                parser.write(fp)
        except (PermissionError, FileNotFoundError):
            return

    def literal_dict(self):
        literal_dict = dict()
        for section in self._config_dict:
            section_dict = self._config_dict[section]
            literal_section_dict = dict()
            literal_dict[section] = literal_section_dict
            for key in section_dict:
                value = section_dict[key]
                try:
                    value = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    pass
                literal_section_dict[key] = value
        return literal_dict

    def set_dict(self, literal_dict):
        self._config_dict.clear()
        for section in literal_dict:
            section_dict = dict()
            self._config_dict[section] = section_dict
            for key in literal_dict[section]:
                section_dict[key] = str(literal_dict[section][key])

    def read_persistent(
        self,
        t: type,
        section: str,
        key: str,
        default: Union[str, int, float, bool, list, tuple] = None,
    ) -> Any:
        """
        Directly read from persistent storage the value of an item.

        @param t: datatype.
        @param section: storing section
        @param key: reference item
        @param default: default value if item does not exist.
        @return: value
        """

        try:
            value = self._config_dict[section][key]
            if t == bool:
                return value == "True"
            elif t in (list, tuple):
                if ";" in value:
                    # This is backwards compatibility code. And may be removed at a later date.
                    value = value.replace(";", ", ").replace("'", "")
                try:
                    return ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    return default

            return t(value)
        except (KeyError, ValueError):
            return default
        except AttributeError as e:
            raise AttributeError(
                "Something is attempting to load a persistent setting after kernel is terminated."
            ) from e

    def read_persistent_attributes(self, section: str, obj: Any):
        """
        Reads persistent settings for any value found set on the object so long as the object type is int, float, str
        or bool.

        @param section:
        @param obj:
        @return:
        """
        for key, value in obj.__dict__.items():
            if key.startswith("_"):
                continue
            t = type(value) if value is not None else str
            read_value = self.read_persistent(t, section, key)
            if read_value is None:
                continue
            try:
                setattr(obj, key, read_value)
            except AttributeError:
                pass

    def read_persistent_object(self, section: str, obj: object) -> None:
        """
        Updates the objects instance dictionary with literal read values.

        @param section: section to load into string dict
        @param obj: object to apply read values.
        @return: object
        """
        for k in list(self.keylist(section)):
            item = self._config_dict[section][k]
            try:
                item = ast.literal_eval(item)
            except (ValueError, SyntaxError):
                pass
            obj.__dict__[k] = item

    def read_persistent_string_dict(
        self, section: str, dictionary: Optional[Dict] = None, suffix: bool = False
    ) -> Dict:
        """
        Updates the given dictionary with the key values at the given section.

        Reads string values and provides no typing information to convert the setting values.

        @param section: section to load into string dict
        @param dictionary: optional dictionary to update values
        @param suffix: provide only the keys or section/key combination.
        @return:
        """
        if dictionary is None:
            dictionary = dict()
        for k in list(self.keylist(section)):
            item = self._config_dict[section][k]
            if not suffix:
                k = f"{section}/{k}"
            dictionary[k] = item
        return dictionary

    load_persistent_string_dict = read_persistent_string_dict

    def write_persistent(
        self, section: str, key: str, value: Union[str, int, float, bool, list, tuple]
    ):
        """
        Directly write the value to persistent storage.

        @param section: section to write key value
        @param key: The item key being written
        @param value: the value of the item.
        """
        try:
            config_section = self._config_dict[section]
        except KeyError:
            config_section = dict()
            self._config_dict[section] = config_section

        if isinstance(value, (str, int, float, bool)):
            config_section[str(key)] = str(value)
        elif isinstance(value, (list, tuple)):
            s = str(value)
            config_section[str(key)] = s

    def write_persistent_dict(self, section, write_dict):
        """
        Write all valid attribute values of this object to the section provided.

        @param section: section to write to
        @param write_dict: dict whose attributes should be written
        @return:
        """
        for key, value in write_dict.items():
            if key.startswith("_"):
                continue
            if isinstance(value, (str, int, float, bool, list, tuple)):
                self.write_persistent(section, key, value)

    def write_persistent_attributes(self, section, obj):
        """
        Write all valid attribute values of this object to the section provided.

        @param section: section to write to
        @param obj: object whose attributes should be written
        @return:
        """
        self.write_persistent_dict(section, obj.__dict__)

    def clear_persistent(self, section: str):
        """
        Clears a section of the persistent settings, all subsections are also cleared.

        @param section:
        @return:
        """
        try:
            for section_name in list(self._config_dict):
                if section_name == section:
                    del self._config_dict[section_name]
        except KeyError:
            pass

    def delete_persistent(self, section: str, key: str):
        """
        Deletes a key within a section of the persistent settings.

        @param section: section to delete key from
        @param key: key to delete
        @return:
        """
        try:
            del self._config_dict[section][key]
        except KeyError:
            pass

    def delete_all_persistent(self):
        """
        Deletes all persistent settings.
        @return:
        """
        self._config_dict.clear()

    def keylist(self, section: str) -> Generator[str, None, None]:
        """
        Get all keys located at the given path location. The keys are listed in absolute path locations.

        @param section: Path to check for keys.
        @return:
        """
        try:
            yield from self._config_dict[section]
        except KeyError:
            return

    def derivable(self, section: str) -> Generator[str, None, None]:
        """
        Finds all derivable paths within the config from the set path location.
        @param section:
        @return:
        """
        for section_name in self._config_dict:
            section_name.split("/")

            if section_name.startswith(section):
                yield section_name

    def section_set(self) -> Generator[str, None, None]:
        """
        Finds all derivable paths within the config from the set path location.
        @return:
        """
        yield from {s.split(" ")[0] for s in self._config_dict}
