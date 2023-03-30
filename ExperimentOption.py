
class ExperimentOption:
    def __init__(self,type,id,name,startValue,minValue = None,maxValue = None) -> None:
        self.__type = type;
        self.__id = id;
        self.__name = name;
        self.__startValue = startValue;
        self.__currentValue = startValue;
        if minValue and maxValue:
            self.__minValue = minValue;
            self.__maxValue = maxValue;

    def getID(self):
        return self.__id;
    def getName(self):
        return self.__name;
    def getStartValue(self):
        return self.__startValue;
    def getValue(self):
        return self.__currentValue;
    def setValue(self, newVal):
        self.__currentValue = newVal;
    def getMinValue(self):
        return self.__minValue;
    def getMaxValue(self):
        return self.__maxValue;
    def getType(self):
        return self.__type;