class BinarySerializer:
    def __init__(self, schema):  # noqa: D107
        self.array = bytearray()
        self.schema = schema

    def read_bytes(self, n):  # noqa: D102
        assert n + self.offset <= len(self.array), f"n: {n} offset: {self.offset}, length: {len(self.array)}"
        ret = self.array[self.offset : self.offset + n]
        self.offset += n
        return ret

    def serialize_num(self, value, n_bytes):  # noqa: D102
        assert value >= 0
        for _ in range(n_bytes):
            self.array.append(value & 255)
            value //= 256
        assert value == 0

    def deserialize_num(self, n_bytes):  # noqa: D102
        value = 0
        bytes_ = self.read_bytes(n_bytes)
        for b in bytes_[::-1]:
            value = value * 256 + b
        return value

    def serialize_field(self, value, field_type):  # noqa: D102
        if type(field_type) == tuple:  # noqa: E721
            if len(field_type) == 0:
                pass
            else:
                assert len(value) == len(field_type)
                for v, t in zip(value, field_type):
                    self.serialize_field(v, t)
        elif type(field_type) == str:  # noqa: E721
            if field_type == "bool":
                assert isinstance(value, bool), str(type(value))
                self.serialize_num(int(value), 1)
            elif field_type[0] == "u":
                self.serialize_num(value, int(field_type[1:]) // 8)
            elif field_type == "string":
                b = value.encode("utf8")
                self.serialize_num(len(b), 4)
                self.array += b
            else:
                raise AssertionError(field_type)
        elif type(field_type) == list:  # noqa: E721
            assert len(field_type) == 1
            if type(field_type[0]) == int:  # noqa: E721
                assert type(value) == bytes  # noqa: E721
                assert len(value) == field_type[0], "len(%s) = %s != %s" % (value, len(value), field_type[0])
                self.array += bytearray(value)
            else:
                self.serialize_num(len(value), 4)
                for el in value:
                    self.serialize_field(el, field_type[0])
        elif type(field_type) == dict:  # noqa: E721
            if "kind" not in field_type:
                raise ValueError(f"Invalid field_type: {field_type}")

            if field_type["kind"] == "option":
                if value is None:
                    self.serialize_num(0, 1)
                else:
                    self.serialize_num(1, 1)
                    self.serialize_field(value, field_type["type"])
            elif field_type["kind"] == "struct":
                assert isinstance(value, dict), f"Expected dict for struct, got {type(value)}"
                for field_name, field_details in field_type["fields"]:
                    self.serialize_field(value[field_name], field_details)
            else:
                raise ValueError(f"Unknown kind: {field_type['kind']}")
        elif type(field_type) == type:  # noqa: E721
            assert type(value) == field_type, "%s != type(%s)" % (field_type, value)  # noqa: E721
            self.serialize_struct(value)
        else:
            raise AssertionError(type(field_type))

    def deserialize_field(self, field_type):  # noqa: D102
        if type(field_type) == tuple:  # noqa: E721
            if len(field_type) == 0:
                return None
            else:
                return tuple(self.deserialize_field(t) for t in field_type)

        elif type(field_type) == str:  # noqa: E721
            if field_type == "bool":
                value = self.deserialize_num(1)
                assert 0 <= value <= 1, f"Fail to deserialize bool: {value}"
                return bool(value)
            elif field_type[0] == "u":
                return self.deserialize_num(int(field_type[1:]) // 8)
            elif field_type == "string":
                len_ = self.deserialize_num(4)
                return self.read_bytes(len_).decode("utf8")
            else:
                raise AssertionError(field_type)
        elif type(field_type) == list:  # noqa: E721
            assert len(field_type) == 1
            if type(field_type[0]) == int:  # noqa: E721
                return bytes(self.read_bytes(field_type[0]))
            else:
                len_ = self.deserialize_num(4)
                return [self.deserialize_field(field_type[0]) for _ in range(len_)]
        elif type(field_type) == dict:  # noqa: E721
            assert field_type["kind"] == "option"
            is_none = self.deserialize_num(1) == 0
            if is_none:
                return None
            else:
                return self.deserialize_field(field_type["type"])
        elif type(field_type) == type:  # noqa: E721
            return self.deserialize_struct(field_type)
        else:
            raise AssertionError(type(field_type))

    def serialize_struct(self, obj):  # noqa: D102
        struct_schema = self.schema[type(obj)]
        if struct_schema["kind"] == "struct":
            for field_name, field_type in struct_schema["fields"]:
                self.serialize_field(getattr(obj, field_name), field_type)
        elif struct_schema["kind"] == "enum":
            name = getattr(obj, struct_schema["field"])
            for idx, (field_name, field_type) in enumerate(struct_schema["values"]):
                if field_name == name:
                    self.serialize_num(idx, 1)
                    self.serialize_field(getattr(obj, field_name), field_type)
                    break
            else:
                raise AssertionError(name)
        else:
            raise AssertionError(struct_schema)

    def deserialize_struct(self, type_):  # noqa: D102
        struct_schema = self.schema[type_]
        if struct_schema["kind"] == "struct":
            ret = type_()
            for field_name, field_type in struct_schema["fields"]:
                setattr(ret, field_name, self.deserialize_field(field_type))
            return ret
        elif struct_schema["kind"] == "enum":
            ret = type_()
            value_ord = self.deserialize_num(1)
            value_schema = struct_schema["values"][value_ord]
            setattr(ret, struct_schema["field"], value_schema[0])
            setattr(ret, value_schema[0], self.deserialize_field(value_schema[1]))

            return ret
        else:
            raise AssertionError(struct_schema)

    def serialize(self, obj):  # noqa: D102
        self.serialize_struct(obj)
        return bytes(self.array)

    def deserialize(self, bytes_, type_):  # noqa: D102
        self.array = bytearray(bytes_)
        self.offset = 0
        ret = self.deserialize_field(type_)
        assert self.offset == len(bytes_), "%s != %s" % (self.offset, len(bytes_))
        return ret
