from configparser import ConfigParser, NoSectionError
from pathlib import Path
from typing import Any,  Dict, Generator,  Optional, Union

from .functions import get_safe_path


class Settings:
    """
    Settings are thin interface with the configparser within python. Conceptually it's a
    dictionary of dictionaries. The first dictionary key are called sections, and the sub-
    section are attributes. To save a list of related settings we add a space within the
    section name. E.g. `operation 0001` or `operation 0002` etc. The first element can be
    divided up with various layers of `/` to make derivable sub-directories of settings.

    Reading/writing and deleting are performed on the config_dict which stores a set of values
    these are loaded during the `read_configuration` step and are committed to disk when
    `write_configuration` is called.
    """
    def __init__(self, directory, filename):
        self._config_file = Path(get_safe_path(directory, create=True)).joinpath(
            filename
        )
        self._config_dict = {}
        self.read_configuration()

    def __contains__(self, item):
        return item in self._config_dict

    def read_configuration(self):
        """
        Read configuration reads the self._config_file to get the parsed config file data.

        Circa 0.8.0 this uses ConfigParser() in python rather than FileConfig in wxPython

        @return:
        """
        try:
            parser = ConfigParser()
            parser.read(self._config_file, encoding="utf-8")
            for section in parser.sections():
                for option in parser.options(section):
                    try:
                        config_section = self._config_dict[section]
                    except KeyError:
                        config_section = dict()
                        self._config_dict[section] = config_section
                    config_section[option] = parser.get(section, option)
        except PermissionError:
            return

    def write_configuration(self):
        """
        Write configuration writes the config file to disk. This is typically done during the shutdown process.

        This uses the python ConfigParser to save data from the _config_dict.
        @return:
        """
        try:
            parser = ConfigParser()
            for section_key in self._config_dict:
                section = self._config_dict[section_key]
                for key in section:
                    value = section[key]
                    try:
                        parser.set(section_key, key, value)
                    except NoSectionError:
                        parser.add_section(section_key)
                        parser.set(section_key, key, value)
            with open(self._config_file, "w", encoding="utf-8") as fp:
                parser.write(fp)
        except PermissionError:
            return

    def read_persistent(
        self,
        t: type,
        section: str,
        key: str,
        default: Union[str, int, float, bool] = None,
    ) -> Any:
        """
        Directly read from persistent storage the value of an item.

        @param t: datatype.
        @param section: section in which to store the key
        @param key: key used to reference item.
        @param default: default value if item does not exist.
        @return: value
        """
        try:
            value = self._config_dict[section][key]
            if t == bool:
                return value == "True"

            return t(value)
        except (KeyError, ValueError):
            return default

    def read_persistent_attributes(self, section: str, obj: Any):
        """
        Reads persistent settings for any value found set on the object so long as the object type is int, float, str
        or bool.

        @param section:
        @param obj:
        @return:
        """
        props = [k for k, v in vars(obj.__class__).items() if isinstance(v, property)]
        for attr in dir(obj):
            if attr.startswith("_"):
                continue
            if attr in props:
                continue
            obj_value = getattr(obj, attr)
            t = type(obj_value) if obj_value is not None else str
            load_value = self.read_persistent(t, section, attr)
            if load_value is None:
                continue
            try:
                setattr(obj, attr, load_value)
            except AttributeError:
                pass

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
                k = "{section}/{key}".format(section=section, key=k)
            dictionary[k] = item
        return dictionary

    load_persistent_string_dict = read_persistent_string_dict

    def write_persistent(
        self, section: str, key: str, value: Union[str, int, float, bool]
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

    def write_persistent_dict(self, section, write_dict):
        """
        Write all valid attribute values of this object to the section provided.

        @param section: section to write to
        @param obj: object whose attributes should be written
        @return:
        """
        for key in write_dict:
            value = write_dict[key]
            if value is None:
                continue
            if isinstance(value, (int, bool, str, float)):
                self.write_persistent(section, key, value)

    def write_persistent_attributes(self, section, obj):
        """
        Write all valid attribute values of this object to the section provided.

        @param section: section to write to
        @param obj: object whose attributes should be written
        @return:
        """
        props = [k for k, v in vars(obj.__class__).items() if isinstance(v, property)]
        for attr in dir(obj):
            if attr.startswith("_"):
                continue
            if attr in props:
                continue
            value = getattr(obj, attr)
            if value is None:
                continue
            if isinstance(value, (int, bool, str, float)):
                self.write_persistent(section, attr, value)

    def clear_persistent(self, section: str):
        """
        Clears a section of the persistent settings, all subsections are also cleared.

        @param section:
        @return:
        """
        try:
            for section_name in list(self._config_dict):
                if section_name.startswith(section):
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
            self._config_dict[section][key]
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
        yield from set([s.split(" ")[0] for s in self._config_dict])
