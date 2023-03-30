from ExperimentAlgorithm import ExperimentAlgorithm
from typing import Tuple
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.log.obj import EventLog
from util import LogProcessor
from pm4py.discovery import discover_petri_net_inductive


class InductiveMinerInfrequent(ExperimentAlgorithm):
    def __init__(self, noise_treshold: float) -> None:
        ExperimentAlgorithm.__init__(
            self, "Inductive Miner Infrequent Algorithm", [], {}
        )
        self.noise_treshold = noise_treshold

    def execute_steps(self, log_processor: LogProcessor):
        net, initial_marking, final_marking = discover_petri_net_inductive(
            log_processor.getLog(), False, self.noise_treshold
        )
        return (net, initial_marking, final_marking)

    def execute(self, log: EventLog) -> Tuple[PetriNet, Marking, Marking]:
        net, initial_marking, final_marking = discover_petri_net_inductive(
            log, False, self.noise_treshold
        )
        return (net, initial_marking, final_marking)
