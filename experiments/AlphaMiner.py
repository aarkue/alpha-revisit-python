from ExperimentAlgorithm import ExperimentAlgorithm
from typing import Tuple, Union, Literal
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.log.obj import EventLog
from util import LogProcessor
from pm4py.discovery import discover_petri_net_alpha
from pm4py.filtering import (
    filter_variants_top_k,
)


# Careful! No DataFrame support for "filter_log_variants_percentage" yet!
from pm4py.algo.filtering.log.variants.variants_filter import (
    filter_log_variants_percentage,
)
from pm4py.objects.conversion.log import converter as log_converter


def filter_variant_percentage_dataframe(log: EventLog, percentage: float):
    l = filter_log_variants_percentage(log, percentage)
    return log_converter.apply(l, variant=log_converter.TO_DATA_FRAME)


class AlphaMiner(ExperimentAlgorithm):
    def __init__(
        self,
        filter_variant: Union[
            Literal["10%Coverage"],
            Literal["50%Coverage"],
            Literal["70%Coverage"],
            Literal["80%Coverage"],
            Literal["90%Coverage"],
            Literal["Top10Variants"],
            Literal["Top5Variants"],
            Literal["Top1Variants"],
        ],
    ) -> None:
        ExperimentAlgorithm.__init__(self, "Alpha Miner Algorithm", [], {})
        self.filter_variant = filter_variant

    def filter_and_discover(self, log: EventLog) -> Tuple[PetriNet, Marking, Marking]:
        filtered_log: EventLog = None
        if self.filter_variant == "10%Coverage":
            filtered_log = filter_variant_percentage_dataframe(log, 0.1)
        elif self.filter_variant == "50%Coverage":
            filtered_log = filter_variant_percentage_dataframe(log, 0.5)
        elif self.filter_variant == "70%Coverage":
            filtered_log = filter_variant_percentage_dataframe(log, 0.7)
        elif self.filter_variant == "80%Coverage":
            filtered_log = filter_variant_percentage_dataframe(log, 0.8)
        elif self.filter_variant == "90%Coverage":
            filtered_log = filter_variant_percentage_dataframe(log, 0.9)
        elif self.filter_variant == "Top10Variants":
            filtered_log = filter_variants_top_k(log, 10)
        elif self.filter_variant == "Top5Variants":
            filtered_log = filter_variants_top_k(log, 5)
        elif self.filter_variant == "Top1Variants":
            filtered_log = filter_variants_top_k(log, 1)
        net, initial_marking, final_marking = discover_petri_net_alpha(filtered_log)
        return (net, initial_marking, final_marking)

    def execute_steps(self, log_processor: LogProcessor):
        return self.filter_and_discover(log_processor.getLog())

    def execute(self, log: EventLog) -> Tuple[PetriNet, Marking, Marking]:
        return self.filter_and_discover(log)
