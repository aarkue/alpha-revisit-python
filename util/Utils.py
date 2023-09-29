from typing import Iterable, Set, Tuple

from util.LogProcessor import END_ACTIVITY, START_ACTIVITY, STARTEND_ACTIVITIES


def isNoDFRelationBetweenSymmetric(dfRelation: Set[Tuple[str,str]], aEls: Iterable[str], bEls : Iterable[str]):
    for a in aEls:
        for b in bEls:
            if (a,b) in dfRelation or (b,a) in dfRelation:
                return False
    return True


def isNoDFRelationBetweenAsymmetric(dfRelation: Set[Tuple[str,str]], aEls: Iterable[str], bEls : Iterable[str]):
    for a in aEls:
        for b in bEls:
            if (a,b) in dfRelation:
                return False
    return True


def areAllRelationsDFBetweenStrict(dfRelation: Set[Tuple[str,str]], aEls: Iterable[str], bEls : Iterable[str]):
    for a in aEls:
        for b in bEls:
            if (a,b) not in dfRelation or (b,a) in dfRelation:
                return False
    return True

def areAllRelationsDFBetweenNonStrict(dfRelation: Set[Tuple[str,str]], aEls: Iterable[str], bEls : Iterable[str]):
    for a in aEls:
        for b in bEls:
            if (a,b) not in dfRelation and a != START_ACTIVITY and b != END_ACTIVITY:
                return False
    return True

def areNotAllRelationsDF_SWITCHED(dfRelation: Set[Tuple[str,str]], aEls: Iterable[str], bEls : Iterable[str]):
    for a in aEls:
        for b in bEls:
            if (b,a) not in dfRelation:
                return True
    return False

def isFeasibleForA30(dfRelation: Set[Tuple[str,str]], aEls: Iterable[str], bEls : Iterable[str]):
    if not areAllRelationsDFBetweenNonStrict(dfRelation,aEls,bEls):
        return False;

    aElsWithoutBs = aEls - bEls
    bElsWithoutAs = bEls - aEls
    newAs = set(aEls)
    newBs = set(bEls)

    for a1 in aEls:
        for a2 in aElsWithoutBs:
            if (a1,a2) in dfRelation:
                newBs.add(a2)
    
    for a1 in bElsWithoutAs:
        for a2 in bEls:
            if (a1,a2) in dfRelation:
                newAs.add(a1)
    return areAllRelationsDFBetweenNonStrict(dfRelation,newAs,newBs)

def stringifyCandidates(cndSet:  Set[Tuple[Set[str],Set[str]]]) -> str:
    return "\n".join(sorted([stringigyCandidate(cnd) for cnd in cndSet]))

def stringigyCandidate(cnd: Tuple[Set[str],Set[str]]):
    return "(" + sortedStringifySet(cnd[0])  + ", \t" + sortedStringifySet(cnd[1]) + ")"

def sortedStringifySet(set: Set[str]):
    return "{" + (', '.join([e for e in sorted(set)])) + "}"



def getIncomingPlaces(net,transition):
    places = set()
    for arc in net.arcs:
        if arc.target == transition:
            places.update([arc.source]);
    return places;

def getOutgoingPlaces(net, transition):
    places = set()
    for arc in net.arcs:
        if arc.source == transition:
            places.update([arc.target]);
    return places;

def getTransitionByName(net,name):
        for t in net.transitions:
            if t.name == name:
                return t;
        return None