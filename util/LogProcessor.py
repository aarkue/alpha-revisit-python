from typing import Dict, List, Tuple, Set
from pandas import DataFrame
from pm4py.objects.log.obj import EventLog
import re

START_ACTIVITY = "__START"
END_ACTIVITY = "__END"
STARTEND_ACTIVITIES = {START_ACTIVITY, END_ACTIVITY}

class LogProcessor:
    def __init__(self, log: EventLog) -> None:
        self.activities: Set[str] = set()
        self.variants = dict()
        self.dfg = dict()
        self.activities_first_in_case = set()
        self.activities_last_in_case = set()
        self.activityOccurrences: Dict[str, int] = dict()
        if 'lifecycle:transition' in log:
            if len(log['lifecycle:transition'].unique()) > 1:
                print("Warning! Multiple different lifecycle:transition values detected. Please filter the event log appropriately before use.")
        self.log = log
        case_groups = log.groupby(["case:concept:name"])
        self.case_ids = set(case_groups.groups.keys())
        for name, group in case_groups:
            trace = group["concept:name"].tolist()
            trace: List[str]
            previousActivity = None
            currentTrace: List[str] = [None for i in range(len(trace) + 2)]
            currentTrace[0] = START_ACTIVITY
            currentTrace[len(trace) + 1] = END_ACTIVITY
            self.increaseActivityOccurenceByOne(START_ACTIVITY)
            self.increaseActivityOccurenceByOne(END_ACTIVITY)
            for i, event in enumerate(trace):
                event: str
                activity: str = re.sub(r",", "_", event)
                self.activities.add(activity)
                self.increaseActivityOccurenceByOne(activity)
                currentTrace[i + 1] = activity
                if i == 0:
                    edge = (START_ACTIVITY, activity)
                    self.activities_first_in_case.add(activity)
                else:
                    edge = (previousActivity, activity)
                    if i == len(trace) - 1:
                        currTraceFrequency: int = self.variants.get(
                            ",".join(currentTrace), 0
                        )
                        self.variants[",".join(currentTrace)] = currTraceFrequency + 1
                        self.activities_last_in_case.add(activity)
                currentValue: int = self.dfg.get(edge, 0)
                self.dfg[edge] = currentValue + 1
                previousActivity = activity
            edge: Tuple[str, str] = (previousActivity, END_ACTIVITY)
            currentValue: int = self.dfg.get(edge, 0)
            self.dfg[edge] = currentValue + 1

    def getDfg(self) -> Dict[Tuple[str, str], int]:
        return self.dfg

    def setDfg(self, newDFG: Dict[Tuple[str, str], int]) -> None:
        self.dfg = newDFG

    def getVariants(self) -> Dict[str, int]:
        return self.variants

    def setVariants(self, newVariants: Dict[str, int]):
        self.variants = newVariants

    def getActivities(self) -> Set[str]:
        return self.activities

    def getFirstInCaseActivities(self) -> Set[str]:
        return self.activities_first_in_case

    def getLastInCaseActivities(self) -> Set[str]:
        return self.activities_last_in_case

    def getActivityOccurrence(self, activity: str) -> int:
        return self.activityOccurrences.get(activity, 0)

    def getActivityOccurrences(self) -> Dict[str, int]:
        return self.activityOccurrences

    def setActivityOccurrences(self, newOccurrences: Dict[str, int]) -> None:
        self.activityOccurrences = newOccurrences

    def getLog(self) -> DataFrame:
        return self.log

    def getNumberOfCases(self) -> int:
        return len(self.case_ids)

    def increaseActivityOccurenceByOne(self, activity: str):
        currentCount = self.activityOccurrences.get(activity, 0)
        self.activityOccurrences[activity] = currentCount + 1

    def setEventLogName(self, name: str):
        self.event_log_name = name
