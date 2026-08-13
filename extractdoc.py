from collections import namedtuple
from lxml import etree
from lxml.builder import E
import sys

from domagi.domagi import main
import click

Command = namedtuple("Command", "name options short_help")

namespaces = {"dbk": "http://docbook.org/ns/docbook"}

def printtree(tree, file):
    print(etree.tostring(tree).decode(), file=file)

def clickfunc2commands(func):
    with click.Context(func) as ctx:
        info = ctx.to_info_dict()
    return [Command(name,
                    (frozenset({tuple(parameter["opts"])
                                for parameter in properties["params"]})
                     # We add the -h variant of the help option to all
                     # subcommands through the context settings. This does not
                     # reflect properly in the info dict. Hence this hack to add
                     # it back.
                     | frozenset({("-h", "--help")}))
                    - frozenset({("--help",)}),
                    properties["short_help"])
            for name, properties in info["command"]["commands"].items()]

def refentry2options(refentry):
    name, = refentry.xpath("dbk:refnamediv/dbk:refname/text()",
                           namespaces=namespaces)
    return (name.removeprefix("domagi-"),
            frozenset({tuple(option.rstrip("= ")
                             for option in varlistentry.xpath("dbk:term/dbk:option/text()",
                                                              namespaces=namespaces))
                       for varlistentry
                       in refentry.xpath("dbk:refsection/dbk:variablelist[dbk:title='Options']//dbk:varlistentry",
                                         namespaces=namespaces)}))

subcommands = clickfunc2commands(main)

# Extract information about subcommands from the source to add to the
# documentation.
for subcommand in subcommands:
    with open(f"doc/gen-refentry-{subcommand.name}.xml", "w") as file:
        printtree(E.refnamediv(E.refname(f"domagi-{subcommand.name}"),
                               E.refpurpose(subcommand.short_help),
                               xmlns="http://docbook.org/ns/docbook"),
                  file)

# Validate documented subcommands. TODO: Also check if the metasyntactic
# variables for the arguments match.
with open("doc/domagi.dbk") as f:
    tree = etree.parse(f)
    tree.xinclude()
documented = dict([refentry2options(refentry)
                   for refentry in tree.xpath("//dbk:refentry", namespaces=namespaces)])
for subcommand in subcommands:
    if subcommand.name not in documented:
        sys.exit(f"Undocumented subcommand: {subcommand.name}")
    undocumented_options = subcommand.options - documented[subcommand.name]
    unknown_options = documented[subcommand.name] - subcommand.options
    if undocumented_options or unknown_options:
        if undocumented_options:
            print(f"Undocumented fields {list(undocumented_options)} in {subcommand.name} documentation")
        if unknown_options:
            print(f"Unknown option {list(unknown_options)} in {subcommand.name} documentation")
        sys.exit(1)
