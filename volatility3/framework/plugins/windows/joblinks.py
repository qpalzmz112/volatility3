# This file is Copyright 2022 Volatility Foundation and licensed under the Volatility Software License 1.0
# which is available at https://www.volatilityfoundation.org/license/vsl-v1.0
#

import logging

from typing import Iterable, Iterator, List, Tuple

from volatility3.framework import exceptions, interfaces, renderers
from volatility3.framework.configuration import requirements
from volatility3.framework.constants import LOGLEVEL_VVVV
from volatility3.framework.objects import utility
from volatility3.framework.renderers import format_hints
from volatility3.plugins.windows import pslist

vollog = logging.getLogger(__name__)

class JobLinks(interfaces.plugins.PluginInterface):
    """Print process job link information"""

    _required_framework_version = (2, 0, 0)
    _version = (1, 0, 0)

    @classmethod
    def get_requirements(cls)-> List[interfaces.configuration.RequirementInterface]:
        return [
            requirements.ModuleRequirement(name = 'kernel', description = 'Windows kernel',
                                           architectures = ["Intel32", "Intel64"]),
            requirements.BooleanRequirement(name = 'physical',
                                            description = "Display physical offset instead of virtual",
                                            default = False,
                                            optional = True),
            requirements.VersionRequirement(name = 'pslist', component = pslist.PsList, version = (2, 0, 0))        
        ]

    def _generator(self) -> Iterator[Tuple]:
        kernel = self.context.modules[self.config['kernel']]
        memory = self.context.layers[kernel.layer_name]

        for proc in pslist.PsList.list_processes(self.context, kernel.layer_name,
                                                 kernel.symbol_table_name):
            try:
                if not self.config['physical']:
                    offset = proc.vol.offset
                else:
                    (_, _, offset, _, _) = list(memory.mapping(offset = proc.vol.offset, length = 0))[0]
                
                job = proc.Job.dereference()
                
                yield (0, (
                    format_hints.Hex(offset), utility.array_to_string(proc.ImageFileName), proc.UniqueProcessId,
                    proc.InheritedFromUniqueProcessId, proc.get_session_id(), job.SessionId, proc.get_is_wow64(),
                    job.TotalProcesses, job.ActiveProcesses, job.TotalTerminatedProcesses,
                    renderers.NotApplicableValue(),
                    "(Original Process)"
                ))

                vollog.log(LOGLEVEL_VVVV, proc.JobLinks)
                vollog.log(LOGLEVEL_VVVV, job.JobLinks)
                vollog.log(LOGLEVEL_VVVV, job.ProcessListHead)

            except (exceptions.InvalidAddressException):
                continue

    def run(self)-> renderers.TreeGrid:
        offsettype = "(V)" if not self.config.get('physical', pslist.PsList.PHYSICAL_DEFAULT) else "(P)"

        return renderers.TreeGrid([
            (f"Offset{offsettype}", format_hints.Hex), ("Name", str), ("PID", int),
            ("PPID", int), ("Sess", int), ("JobSess", int), ("Wow64", bool),
            ("Total", int), ("Active", int), ("Term", int), ("JobLink", str), ("Process", str)
        ], self._generator())