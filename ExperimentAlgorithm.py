from abc import ABC, abstractmethod
from typing import Tuple
from pm4py.objects.petri_net.obj import PetriNet
from pm4py.objects.petri_net.obj import Marking
from pm4py.objects.log.obj import EventLog
from util import LogProcessor
class ExperimentAlgorithm(ABC):
    def __init__(self,name,options,optionValue : dict = {}) -> None:
        self.__name = name;
        self.__options = options;
        for key in optionValue.keys():
            value = optionValue.get(key)
            self.setOptionValueByID(key,value)


    def getName(self):
        return self.__name;

    def getOptions(self):
        return self.__options;

    def getOptionByID(self,id):
        options = [o for o in self.__options if o.getID() == id];
        if len(options) > 0:
            return options[0];
        return None;

    def getOptionValueByID(self,id):
        option = self.getOptionByID(id)
        if option != None:
            return option.getValue()
        else:
            return None;
    def setOptionValueByID(self,id,value):
        option = self.getOptionByID(id);
        if option != None:
            option.setValue(value);


    @abstractmethod
    def execute(self,log : EventLog) -> Tuple[PetriNet,Marking,Marking]:
        pass

    @abstractmethod
    def execute_steps(self, log_processor: LogProcessor):
        pass
