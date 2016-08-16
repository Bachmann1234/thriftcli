import json
import sys

from .thrift_cli_error import ThriftCLIError
from .thrift_parser import ThriftParser


class ThriftArgumentConverter(object):
    """ Converts a json request body into the corresponding Python object generated by thrift. """

    def __init__(self, thrift_path, thrift_dir_paths=None):
        thrift_parser = ThriftParser(thrift_path, thrift_dir_paths)
        self._parse_result = thrift_parser.parse()

    def convert_args(self, service_reference, method_name, data):
        """ Converts json request body into keyword arguments for a service's method.

        :param service_reference: the name of the service that provides the given method.
        :type service_reference: str
        :param method_name: the name of the method whose type signature is the basis for the conversion.
        :type method_name: str
        :param data: a nested dictionary of parameters, mapping argument names to their values
        :type data: dict
        :returns: a python dict representing the request body
        :rtype: dict

        """
        fields = self._parse_result.get_fields_for_endpoint(service_reference, method_name)
        return self._convert_dict_to_args_given_fields(fields, data)

    def _convert_dict_to_args_given_fields(self, fields, data):
        """ Converts a request body into a Python object, given the fields each key value pair should convert into.

        :param fields: a flat dictionary of field names to ThriftStruct.Fields
        :type fields: dict of str to ThriftStruct.Field
        :param data: a JSON object that represents the desired Python primitive or object
        :type data: JSON
        :returns: a flat dictionary of field names to their values
        :rtype: dict

        """
        if len(fields) == 1:
            field = fields.values()[0]
            if field.name not in data:
                data = {field.name: data}
        args = {field_name: self._convert_dict_entry_to_arg(fields[field_name].field_type, value)
                for field_name, value in data.items()}
        return args

    def _convert_dict_entry_to_arg(self, field_type, value):
        """ Converts a request body item into an argument for the Python object.

        :param field_type: the type of the field being converted
        :type field_type: str
        :param value: a JSON object that represents the desired Python primitive or object
        :type value: JSON
        :returns: the Python primitive or object represented by value given the field type

        """
        field_type = self._parse_result.unalias_type(field_type)
        if self._parse_result.get_struct(field_type) is not None:
            fields = self._parse_result.get_fields_for_struct_name(field_type)
            value = self._convert_dict_to_args_given_fields(fields, value)
        arg = self._construct_arg(field_type, value)
        return arg

    def _construct_arg(self, field_type, value):
        """ Converts a simple request body item into an argument for the Python object.

        A request body item is simple when it is not a struct that has another struct as a field.

        :param field_type: the type of the field being converted
        :type field_type: str
        :param value: a flat dictionary that represents the desired Python primitive or object
        :type value: dict
        :returns: the Python primitive or object represented by value given the field type

        """
        if self._parse_result.get_struct(field_type) is not None:
            return self._construct_struct_arg(field_type, value)
        elif self._parse_result.has_enum(field_type):
            return self._construct_enum_arg(field_type, value)
        elif field_type.startswith('list<'):
            return self._construct_list_arg(field_type, value)
        elif field_type.startswith('set<'):
            return self._construct_set_arg(field_type, value)
        elif field_type.startswith('map<'):
            return self._construct_map_arg(field_type, value)
        elif field_type == 'string':
            return str(value)
        elif field_type == 'double':
            return float(value)
        elif field_type == 'bool':
            return bool(value)
        try:
            return long(value)
        except ValueError:
            return value

    @staticmethod
    def _get_type_class(package, type_name):
        """ Gets the generated Python class corresponding to a type definition.

        :param package: the name of the package containing the class
        :type package: str
        :param type_name: the name of the class to retrieve
        :type type_name: str
        :returns: the class defining the desired type name in the given package

        """
        return getattr(sys.modules['%s.ttypes' % package], type_name)

    @staticmethod
    def _construct_struct_arg(field_type, value):
        """ Returns the Python object corresponding to a struct.

        :param field_type: the type of the struct being constructed
        :type field_type: str
        :param value: a flat dictionary that represents the desired Python struct
        :type value: dict
        :returns: the Python struct represented by value given the field type

        """
        package, struct = ThriftArgumentConverter._split_field_type(field_type)
        constructor = ThriftArgumentConverter._get_type_class(package, struct)
        return constructor(**value)

    @staticmethod
    def _construct_enum_arg(field_type, value):
        """ Returns the value corresponding to an enum.

        :param field_type: the type of the enum being constructed
        :type field_type: str
        :param value: a string or integer mapping to an enum value
        :type value: str or int
        :returns: the integer representing the desired enum value
        :rtype: int

        """
        package, enum = ThriftArgumentConverter._split_field_type(field_type)
        enum_class = ThriftArgumentConverter._get_type_class(package, enum)
        if isinstance(value, (int, long)):
            return value
        elif isinstance(value, basestring):
            return enum_class._NAMES_TO_VALUES[value]
        raise ThriftCLIError('Invalid value provided for enum %s: %s' % (field_type.str(value)))

    def _construct_list_arg(self, field_type, value):
        """ Returns the Python list corresponding to a JSON array in the request body.

        :param field_type: the type of the list being constructed
        :type field_type: str
        :param value: a JSON array representing the desired Python list
        :type value: JSON array
        :returns: the desired Python list
        :rtype: list

        """
        elem_type = field_type[field_type.index('<') + 1: field_type.rindex('>')]
        return tuple([self._convert_dict_entry_to_arg(elem_type, elem) for elem in value])

    def _construct_set_arg(self, field_type, value):
        """ Returns the Python set corresponding to a JSON array in the request body.

        :param field_type: the type of the set being constructed
        :type field_type: str
        :param value: a JSON array representing the desired Python set
        :type value: JSON array
        :returns: the desired Python set
        :rtype: set

        """
        elem_type = field_type[field_type.index('<') + 1: field_type.rindex('>')]
        return frozenset([self._convert_dict_entry_to_arg(elem_type, elem) for elem in value])

    def _construct_map_arg(self, field_type, value):
        """ Returns the Python dict corresponding to a JSON object in the request body.

        :param field_type: the type of the map being constructed
        :type field_type: str
        :param value: a JSON object representing the desired Python dict
        :type value: JSON
        :returns: the desired Python dict
        :rtype: dict

        """
        types_string = field_type[field_type.index('<') + 1: field_type.rindex('>')]
        split_index = ThriftParser.calc_map_types_split_index(types_string)
        if split_index == -1:
            raise ThriftCLIError('Invalid type formatting for map - \'%s\'' % types_string)
        key_type = types_string[:split_index].strip()
        elem_type = types_string[split_index + 1:].strip()
        prep = lambda x: x if self._parse_result.get_struct(key_type) is None else json.loads(x)
        return {self._convert_dict_entry_to_arg(key_type, prep(key)): self._convert_dict_entry_to_arg(elem_type, elem)
                for key, elem in value.items()}

    @staticmethod
    def _split_field_type(field_type):
        """ Extracts the namespace and type name from a field type.

        For example: "Namespace.type" -> ("Namespace", "type")

        :param field_type: the type being split
        :type field_type: str
        :returns: a tuple of the namespace and the type name
        :rtype: tuple of (str, str)
        :raises: ThriftCLIError

        """
        split = field_type.split('.')
        if not split or len(split) != 2:
            raise ThriftCLIError('Field type should be in format \'Namespace.type\', given \'%s\'' % field_type)
        return split
