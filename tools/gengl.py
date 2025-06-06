"""Generate gl.py and gl_compat.py
See : tools/requirements.txt.

We are using the opengl-registry project to extract this information from
https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/master/xml/gl.xml

A local version gl.xml can also be used.

Usage:

# Fetch gl.xml from Khronos Github repo
python gengl.py
python gengl.py --source url

# Use local gl.xml
python gengl.py --source local
"""  # noqa: D205
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import TextIO, Iterable

from opengl_registry import Registry, RegistryReader

REPO_ROOT = Path(__file__).parent.parent.resolve()
DEST_PATH = REPO_ROOT / "pyglet" / "gl"


def main() -> None:  # noqa: D103
    values = parse_args(sys.argv[1:])
    if values.source == "url":
        # Fetch gl.xml from Khronos Github repo
        reader = RegistryReader.from_url()
    else:
        # Use the local gl.xml file
        reader = RegistryReader.from_file(Path(REPO_ROOT / "tools" / "gl.xml"))

    registry = reader.read()

    # OpenGL extensions we want to include
    extensions = [
        "GL_ARB_multisample",
        "EXT_texture_compression_s3tc",  # For pyglet.image.codecs.dds
        "GL_EXT_framebuffer_object",  # Needed for GL_FRAMEBUFFER_INCOMPLETE_DIMENSIONS
        "GL_ARB_bindless_texture",
        "GL_ARB_gpu_shader_int64",
        "GL_NV_mesh_shader",
    ]

    core_profile = registry.get_profile(
        api="gl",
        profile="core",
        version="4.6",
        extensions=extensions,
    )
    compat_profile = registry.get_profile(
        api="gl",
        profile="compat",
        version="4.6",
        extensions=extensions,
    )
    # es_profile = registry.get_profile(
    #     api="gles2",
    #     profile="core",
    #     version="3.2",
    #     extensions=extensions,
    # )

    core_writer = PygletGLWriter(registry=core_profile, out_module=DEST_PATH / "gl")
    core_writer.run()
    compat_writer = PygletGLWriter(registry=compat_profile, out_module=DEST_PATH / "gl_compat")
    compat_writer.run()
    # es_writer = PygletGLWriter(registry=es_profile, out_file=DEST_PATH / "gl_es")
    # es_writer.run()


def parse_args(args: str) -> Namespace:  # noqa: D103
    parser = ArgumentParser()
    parser.add_argument("--source", choices=["local", "url"], default="url")
    return parser.parse_args(args)


class PygletGLWriter:
    """Writes gl.py, gl_compat.py, and gl_es.py."""

    # All gl types manually matched to ctypes.
    # Inspect registry.types
    types = {  # noqa: RUF012
        "GLenum": "c_uint",
        "GLboolean": "c_ubyte",
        "GLbitfield": "c_uint",
        "GLvoid": "None",
        "GLbyte": "c_byte",
        "GLubyte": "c_ubyte",
        "GLshort": "c_short",
        "GLushort": "c_ushort",
        "GLint": "c_int",
        "GLuint": "c_uint",
        "GLclampx": "c_uint",
        "GLsizei": "c_int",
        "GLfloat": "c_float",
        "GLclampf": "c_float",
        "GLdouble": "c_double",
        "GLclampd": "c_double",
        "GLchar": "c_char",
        "GLintptr": "c_ptrdiff_t",
        "GLsizeiptr": "c_ptrdiff_t",
        "GLint64": "c_int64",
        "GLuint64": "c_uint64",
        "GLuint64EXT": "c_uint64",
        "GLsync": "POINTER(struct___GLsync)",
        "GLDEBUGPROC": "CFUNCTYPE(None, GLenum, GLenum, GLuint, GLenum, GLsizei, POINTER(GLchar), POINTER(GLvoid))",
    }
    # All gl types matched to python types
    pythontypes = {
        "GLenum": "int",
        "GLboolean": "int",
        "GLbitfield": "int",
        "GLvoid": "None",
        "GLbyte": "bytes",
        "GLubyte": "int",
        "GLshort": "int",
        "GLushort": "int",
        "GLint": "int",
        "GLuint": "int",
        "GLclampx": "int",
        "GLsizei": "int",
        "GLfloat": "float",
        "GLclampf": "float",
        "GLdouble": "float",
        "GLclampd": "float",
        "GLchar": "bytes",
        # "GLintptr": "c_ptrdiff_t",
        # "GLsizeiptr": "c_ptrdiff_t",
        "GLint64": "int",
        "GLuint64": "int",
        "GLuint64EXT": "int",
    }
    exclude_commands = set()

    def __init__(self, *, registry: Registry, out_module: Path):
        self._registry = registry
        self._out_module = out_module
        self._out = None
        self._stub = None
        self._all = []  # Entries for __all__
        self._commands = []

    def run(self):
        """Write the file and close"""
        with open(self._out_module.with_suffix(".py"), mode='w') as out:
            self.write_template(out, REPO_ROOT / "tools" / "gl.template")
            self.write_types(out)
            self.write_enums(out)
            self.write_commands(out)
            self.write_footer(out)

        with open(self._out_module.with_suffix(".pyi"), mode='w') as stub:
            self.write_template(stub, REPO_ROOT / "tools" / "gl_stub.template")
            self.write_types(stub)
            self.write_enum_stubs(stub)
            self.write_command_stubs(stub)

    def write_lines(self, fp: TextIO, lines: Iterable[str]) -> None:
        """Write one or several lines to the out file."""
        for line in lines:
            fp.write(line)
            fp.write("\n")

    def write_template(self, fp: TextIO, template: Path) -> None:
        """Write the header."""
        with open(template) as fd:
            fp.write(fd.read())

    def write_types(self, fp: TextIO) -> None:
        """Write all types."""
        self.write_lines(fp, ["# GL type definitions"])
        self.write_lines(fp, [f"{k} = {v}" for k, v in self.types.items()])
        self.write_lines(fp, [""])
        self._all.extend(self.types.keys())

    def write_enums(self, fp: TextIO) -> None:
        """Write all enums."""
        self.write_lines(fp, ["# GL enumerant (token) definitions"])
        self.write_lines(fp, [
            f"{e.name} = {e.value_int}"
            for e in sorted(self._registry.enums.values())
        ])
        self.write_lines(fp, [""])
        self._all.extend(self._registry.enums.keys())

    def write_enum_stubs(self, fp: TextIO) -> None:
        """Write type annotations for all enums."""
        self.write_lines(fp, ["# GL enumerant (token) definitions"])
        self.write_lines(fp, [
            f"{e.name}: int"  # assume all enums values are integers
            for e in sorted(self._registry.enums.values())
        ])
        self.write_lines(fp, [""])

    def write_commands(self, fp: TextIO) -> None:
        """Write all commands."""
        self.write_lines(fp, ["# GL command definitions"])

        # _link_function params : name, restype, argtypes, requires=None, suggestions=None
        for cmd in sorted(self._registry.commands.values()):
            if cmd.name in self.exclude_commands:
                continue

            # Return type: If the function returns a pointer type ...
            if "*" in cmd.proto:
                restype = f"POINTER({cmd.ptype})"
            else:
                restype = cmd.ptype or "None"

            # Arguments can be pointer and pointer-pointer
            arguments = []
            for param in cmd.params:
                # print(cmd.name, param.name, param.ptype, "|", param.value)

                # Detect void pointers. They don't have a ptype set
                if "void" in param.value:
                    arguments.append("POINTER(GLvoid)")
                else:
                    # Ensure we actually know what the type is
                    if not self.types.get(param.ptype):
                        raise ValueError(f"ptype {param.ptype} not a known type")
                    # Handle pointer-pointer and pointers: *, **, *const*
                    if param.value.count("*") == 2:
                        arguments.append(f"POINTER(POINTER({param.ptype}))")
                    elif param.value.count("*") == 1:
                        arguments.append(f"POINTER({param.ptype})")
                    else:
                        arguments.append(param.ptype)

            argtypes = ", ".join(arguments)
            requires = f"OpenGL {cmd.requires}" if cmd.requires else "None"
            # NOTE: PROCs are optional
            # proc_name = f"PFN{cmd.name.upper()}PROC"

            self.write_lines(fp, [
                f"{cmd.name} = _link_function('{cmd.name}', {restype}, [{argtypes}], requires='{requires}')",
                # f"{proc_name} = CFUNCTYPE({restype}, {argtypes})",
            ])
            self._all.append(cmd.name)

        self.write_lines(fp, [""])

    def write_footer(self, fp: TextIO) -> None:
        """Write __all__ section."""
        self.write_lines(fp, [
            "",
            "__all__ = [",
            *[f"    '{name}'," for name in self._all],
            "]",
        ])

    def write_command_stubs(self, fp: TextIO) -> None:
        """Write type annotations for all commands."""
        self.write_lines(fp, ["# GL command definitions"])

        # _link_function params : name, restype, argtypes, requires=None, suggestions=None
        for cmd in sorted(self._registry.commands.values()):
            if cmd.name in self.exclude_commands:
                continue

            # Return type: If the function returns a pointer type ...
            if "*" in cmd.proto:
                restype = f"_Pointer[{cmd.ptype}]"
            else:
                restype = cmd.ptype or "None"

            # Arguments can be pointer and pointer-pointer
            arguments = []
            names = []
            for param in cmd.params:
                # print(cmd.name, param.name, param.ptype, "|", param.value)
                names.append(param.name)

                # Detect void pointers. They don't have a ptype set
                if "void" in param.value:
                    # The exact types which are valid is hard to determine since
                    # ctypes automatically converts arguments to the required type, so allow Any
                    arguments.append("_Pointer[GLvoid] | Any")
                else:
                    # Ensure we actually know what the type is
                    if not self.types.get(param.ptype):
                        raise ValueError(f"ptype {param.ptype} not a known type")
                    # Handle pointer-pointer and pointers: *, **, *const*
                    if param.value.count("*") == 2:
                        arguments.append(f"_Pointer[_Pointer[{param.ptype}]] | Any")
                    elif param.value.count("*") == 1:
                        arguments.append(f"_Pointer[{param.ptype}] | Any")
                    else:
                        arguments.append(param.ptype)

            # Arguments can be pointer and pointer-pointer
            argannotations = ", ".join(
                f"{name}: {f'{arg} | {self.pythontypes[arg]}' if arg in self.pythontypes else arg}" for name, arg in
                zip(names, arguments))

            self.write_lines(fp, [
                f"def {cmd.name}({argannotations}) -> {self.pythontypes.get(restype, restype)}: ..."
            ])


if __name__ == "__main__":
    main()
