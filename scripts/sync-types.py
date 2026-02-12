#!/usr/bin/env python3
"""
Type Synchronization Script
Automatically generates TypeScript interfaces from Pydantic models.
"""
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


class TypeMapper:
    """Maps Python types to TypeScript types."""

    BASIC_TYPES = {
        'str': 'string',
        'int': 'number',
        'float': 'number',
        'bool': 'boolean',
        'datetime': 'string',
        'Any': 'unknown',
    }

    @classmethod
    def map_type(cls, type_annotation: str) -> str:
        """Convert Python type annotation to TypeScript type."""
        if not type_annotation:
            return 'unknown'

        # Handle Optional[T] -> T | null
        if type_annotation.startswith('Optional['):
            inner = type_annotation[9:-1]
            return f"{cls.map_type(inner)} | null"

        # Handle list[T] -> T[]
        if type_annotation.startswith('list['):
            inner = type_annotation[5:-1]
            return f"{cls.map_type(inner)}[]"

        # Handle dict -> Record<string, unknown>
        if type_annotation in ('dict', 'Dict'):
            return 'Record<string, unknown>'

        # Handle Literal["a", "b"] -> "a" | "b"
        if type_annotation.startswith('Literal['):
            inner = type_annotation[8:-1]
            values = [v.strip().strip('"').strip("'") for v in inner.split(',')]
            return ' | '.join(f'"{v}"' for v in values)

        # Basic type mapping
        return cls.BASIC_TYPES.get(type_annotation, type_annotation)


class PydanticModelParser:
    """Parses Pydantic models from Python source files."""

    def __init__(self, source_code: str):
        self.tree = ast.parse(source_code)
        # Store field metadata: model_name -> [(field_name, type_str, has_default)]
        self.models: Dict[str, List[Tuple[str, str, bool]]] = {}
        self.inheritance: Dict[str, str] = {}  # child -> parent mapping
        self.type_aliases: Dict[str, str] = {}

    def parse(self):
        """Parse all Pydantic models and type aliases from the AST."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                if self._is_pydantic_model(node):
                    self._parse_model(node)
            elif isinstance(node, ast.Assign):
                self._parse_type_alias(node)

    def _is_pydantic_model(self, node: ast.ClassDef) -> bool:
        """Check if a class is a Pydantic BaseModel or inherits from one."""
        for base in node.bases:
            if isinstance(base, ast.Name):
                if 'BaseModel' in base.id:
                    return True
                # Also consider classes that inherit from other models
                if base.id in self.models or base.id.endswith('Base'):
                    return True
        return False

    def _parse_model(self, node: ast.ClassDef):
        """Parse a Pydantic model class."""
        fields = []
        parent_class = None

        # Track inheritance
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id != 'BaseModel':
                parent_class = base.id
                self.inheritance[node.name] = parent_class

        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                type_str = self._get_type_string(item.annotation)
                has_default = self._has_default_value(item)
                fields.append((field_name, type_str, has_default))

        # Always store the model, even if it has no fields (it might inherit)
        self.models[node.name] = fields

    def _parse_type_alias(self, node: ast.Assign):
        """Parse type aliases like TargetType = Literal[...]."""
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if isinstance(node.value, ast.Subscript):
                type_str = self._get_type_string(node.value)
                self.type_aliases[name] = type_str

    def _get_type_string(self, annotation) -> str:
        """Extract type string from AST annotation node."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Subscript):
            value = self._get_type_string(annotation.value)
            slice_val = self._get_type_string(annotation.slice)
            return f"{value}[{slice_val}]"
        elif isinstance(annotation, ast.Constant):
            return repr(annotation.value)
        elif isinstance(annotation, ast.Tuple):
            elements = [self._get_type_string(e) for e in annotation.elts]
            return ', '.join(elements)
        return 'unknown'

    def _has_default_value(self, node: ast.AnnAssign) -> bool:
        """Check if a field has a default value."""
        if node.value is None:
            return False

        # Field(...) with ellipsis means no default (required)
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name) and node.value.func.id == 'Field':
                if node.value.args and isinstance(node.value.args[0], ast.Constant):
                    if node.value.args[0].value is ...:
                        return False

        return True

    def resolve_inheritance(self) -> Dict[str, List[Tuple[str, str, bool]]]:
        """Resolve inheritance to create complete field lists for each model."""
        resolved = {}

        def get_all_fields(model_name: str, visited: Set[str] = None) -> List[Tuple[str, str, bool]]:
            """Recursively get all fields including inherited ones."""
            if visited is None:
                visited = set()

            if model_name in visited:
                return []

            visited.add(model_name)

            # Get fields from this model
            fields = list(self.models.get(model_name, []))

            # Get fields from parent
            if model_name in self.inheritance:
                parent_name = self.inheritance[model_name]
                parent_fields = get_all_fields(parent_name, visited)
                # Parent fields come first, then child fields override
                field_dict = {name: (name, type_str, optional) for name, type_str, optional in parent_fields}
                for name, type_str, optional in fields:
                    field_dict[name] = (name, type_str, optional)
                fields = list(field_dict.values())

            return fields

        # Resolve all models
        for model_name in self.models:
            resolved[model_name] = get_all_fields(model_name)

        return resolved


class TypeScriptGenerator:
    """Generates TypeScript interface definitions."""

    def __init__(self):
        self.output: List[str] = []

    def add_header(self):
        """Add file header with generation notice."""
        self.output.append("// AUTO-GENERATED FILE - DO NOT EDIT")
        self.output.append("// Generated by scripts/sync-types.py")
        self.output.append("// Source: backend/models/")
        self.output.append("")

    def add_type_alias(self, name: str, type_def: str):
        """Add a TypeScript type alias."""
        ts_type = TypeMapper.map_type(type_def)
        self.output.append(f"export type {name} = {ts_type};")
        self.output.append("")

    def add_interface(self, name: str, fields: List[Tuple[str, str, bool]]):
        """Add a TypeScript interface."""
        # Check if this is a request model (Create, Update, Request)
        is_request_model = any(name.endswith(suffix) for suffix in ['Create', 'Update', 'Request'])

        self.output.append(f"export interface {name} {{")

        for field_name, type_str, has_default in fields:
            ts_type = TypeMapper.map_type(type_str)

            # Determine if field should be optional in TypeScript
            # For request models: fields with defaults are optional
            # For response models: fields are never optional (always present)
            is_optional = is_request_model and has_default

            optional_marker = '?' if is_optional else ''
            self.output.append(f"  {field_name}{optional_marker}: {ts_type};")

        self.output.append("}")
        self.output.append("")

    def get_output(self) -> str:
        """Get the complete TypeScript output."""
        return '\n'.join(self.output)


def sync_types():
    """Main function to sync types from backend to frontend."""
    # Paths
    backend_models_dir = Path(__file__).parent.parent / 'backend' / 'models'
    frontend_types_file = Path(__file__).parent.parent / 'frontend' / 'src' / 'lib' / 'types.ts'

    # Collect all parsers to resolve inheritance across files
    parsers: List[PydanticModelParser] = []
    all_type_aliases: Dict[str, str] = {}

    # Parse all model files
    for py_file in sorted(backend_models_dir.glob('*.py')):
        if py_file.name.startswith('_'):
            continue

        source = py_file.read_text()
        parser = PydanticModelParser(source)
        parser.parse()
        parsers.append(parser)
        all_type_aliases.update(parser.type_aliases)

    # Merge all models and inheritance info
    all_models: Dict[str, List[Tuple[str, str, bool]]] = {}
    all_inheritance: Dict[str, str] = {}

    for parser in parsers:
        all_models.update(parser.models)
        all_inheritance.update(parser.inheritance)

    # Create a combined parser to resolve inheritance
    combined_parser = PydanticModelParser("")
    combined_parser.models = all_models
    combined_parser.inheritance = all_inheritance
    resolved_models = combined_parser.resolve_inheritance()

    # Generate TypeScript
    generator = TypeScriptGenerator()
    generator.add_header()

    # Add type aliases first
    for name, type_def in sorted(all_type_aliases.items()):
        generator.add_type_alias(name, type_def)

    # Add interfaces (only non-empty ones)
    for name, fields in sorted(resolved_models.items()):
        if fields:  # Only generate interfaces with fields
            generator.add_interface(name, fields)

    # Write output
    output = generator.get_output()
    frontend_types_file.write_text(output)

    print(f"✓ Generated {len([f for f in resolved_models.values() if f])} interfaces and {len(all_type_aliases)} type aliases")
    print(f"✓ Written to {frontend_types_file}")


if __name__ == '__main__':
    sync_types()
