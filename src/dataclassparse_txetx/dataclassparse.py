import dataclasses
from dataclasses import dataclass, field

import argparse

import types
import typing

from collections import defaultdict
from collections.abc import Sequence

@dataclass
class ConfigGroupDataclass:
    _config_group_title : typing.ClassVar[str | None] = None
    _config_group_description : typing.ClassVar[str | None] = None


@dataclass
class SelfParsingDataclass:
    @classmethod
    def parse_args(cls, args : Sequence[str] | None = None, namespace: None = None):

        root_fields = []
        nested_dataclasses, nested_fields = {}, defaultdict(list)
        parser = argparse.ArgumentParser()
        for f in dataclasses.fields(cls):

            if not f.init:
                continue
            
            if issubclass(f.type,ConfigGroupDataclass):
                nested_parser = parser.add_argument_group(title=f.type._config_group_title,description=f.type._config_group_description)
                nested_dataclasses[f.name] = f.type

                for nf in dataclasses.fields(f.type):
                    if not nf.init:
                        continue

                    SelfParsingDataclass._add_argument(nested_parser,nf)
                    nested_fields[f.name].append(nf.name)

            else:
                SelfParsingDataclass._add_argument(parser,f)
                root_fields.append(f.name)

        args = parser.parse_args(args, namespace)

        root_args = {f : getattr(args,f) for f in root_fields}
        for ndc in nested_dataclasses:
            nested_args = {f : getattr(args,f) for f in nested_fields[ndc]}
            nested_dataclasses[ndc] = nested_dataclasses[ndc](**nested_args)

        return cls(**root_args,**nested_dataclasses)
        

    @staticmethod
    def _add_argument(parser : argparse._ArgumentGroup | argparse.ArgumentParser, field : dataclasses.Field):

        default = None
        if not isinstance(field.default,dataclasses._MISSING_TYPE) :
            default = field.default
        elif not isinstance(field.default_factory ,dataclasses._MISSING_TYPE):
            default = field.default_factory()


        if type(field.type) is type and issubclass(field.type, bool):
            parser.add_argument(
                f"--{field.name}",
                action="store_true" if not default else "store_false",
                **field.metadata
            )
            parser.set_defaults(**{field.name: False if default is None else default})

        else:
            args = dict()
            # Nargs
            if type(typing.get_origin(field)) is type and issubclass(typing.get_origin(field.type), Sequence): args["nargs"] = "*"

            # Default
            args["default"] = default

            # Try to get type
            if typing.get_args(field.type):
                t = typing.get_args(field.type)[0]
                t = t if type(t) is type else type(t)
            else:
                t = field.type
            if not issubclass(t,types.UnionType): args["type"] = t

            # Choices
            if typing.get_origin(field.type) is typing.Literal: args["choices"] = typing.get_args(field.type)

            # Add and override metadata
            args.update(field.metadata)

            # Parse
            parser.add_argument(
                 f"--{field.name}" if field.kw_only else field.name,
                **args
            )