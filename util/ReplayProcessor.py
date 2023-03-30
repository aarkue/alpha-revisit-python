from collections import Counter
from typing import Dict, List, Set, Tuple

from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils.petri_utils import remove_place
from util import Utils


def getTopVariants(
    allVariantsWithCaseNumbers: Dict[str, int],
    totalNumberOfCases: int,
    goalMinCasePercentage: float,
):
    variantArray = sorted(
        allVariantsWithCaseNumbers.keys(),
        key=lambda k: allVariantsWithCaseNumbers.get(k, 0),
        reverse=True,
    )
    numberOfCoveredCases = 0
    lastVariantIndex = -1
    while (
        (numberOfCoveredCases * 100.0 / totalNumberOfCases) < goalMinCasePercentage
    ) and ((lastVariantIndex + 1) < len(variantArray)):
        lastVariantIndex += 1
        numberOfCoveredCases += allVariantsWithCaseNumbers.get(
            variantArray[lastVariantIndex], 0
        )
    return variantArray[0 : lastVariantIndex + 1]


def replayAndRemovePlaces(
    net: Tuple[PetriNet, Marking, Marking],
    frequentVariants: List[str],
    doNotRemoveStartEndPlaces: bool,
):
    transitionMap: Dict[str, PetriNet.Transition] = dict()
    for t in net[0].transitions:
        t: PetriNet.Transition
        transitionMap[t.name.replace(",", "_")] = t

    placesToRemove = set()
    for variant in frequentVariants:
        tokenCount = Counter()
        trace = variant.split(",")
        for p in net[0].places:
            p: PetriNet.Place
            if p in net[1]:  # check if place is part of initial marking
                tokenCount[p] = 1
            else:
                tokenCount[p] = 0

        for activity in trace:
            # Check if incoming places have sufficient token
            # Get every place with an arc to the corresponding (fired) transition
            transition = Utils.getTransitionByName(net[0], activity)
            for p in Utils.getIncomingPlaces(net[0], transition):
                # Decrease the token count in that place by 1
                count = tokenCount.get(p)
                assert type(count) == int
                if count > 0:
                    count -= 1
                    tokenCount[p] = count
                else:
                    # Else, if there is no token in the place, it should be removed (later)
                    placesToRemove.add(p)
            # Place tokens in outgoing places
            for p in Utils.getOutgoingPlaces(net[0], transition):
                # Increase the token count in that place by 1
                count = tokenCount.get(p)
                assert type(count) == int
                count += 1
                tokenCount[p] = count
        # in PM4PY there is only one final marking, thus it is sufficient to use this as the "final marking with least violations"
        for p in net[0].places:
            p: PetriNet.Place
            count = tokenCount.get(p)
            assert type(count) == int
            if p in net[2]:
                if count != 1:
                    placesToRemove.add(p)
            else:
                if count != 0:
                    placesToRemove.add(p)
    #  Actually remove places that had missing/remaining tokens
    for p in placesToRemove:
        if not (doNotRemoveStartEndPlaces and (p in net[1] or p in net[2])):
            remove_place(net[0], p)
            # net[0].places.remove(p)

            # arcs_to_remove : Set[PetriNet.Arc]= set()
            # for arc in net[0].arcs:
            #   if arc.source == p or arc.target == p:
            #     arcs_to_remove.add(arc);
            # for arc in arcs_to_remove:
            #   net[0].arcs.remove(arc)

            if p in net[1]:
                net[1].pop(p)
            if p in net[2]:
                net[2].pop(p)


def replayWithAllTraces(
    net: Tuple[PetriNet, Marking, Marking], allTracesWithFrequency: Dict[str, int]
):
    transitionMap: Dict[str, PetriNet.Transition] = dict()
    for t in net[0].transitions:
        t: PetriNet.Transition
        transitionMap[t.name.replace(",", "_")] = t

    # placesToRemove = set()
    numberOfFittingTracesPerPlace: Dict[PetriNet.Place, int] = dict()
    numberOfRelevantTracesPerPlace: Dict[PetriNet.Place, int] = dict()
    for variant in allTracesWithFrequency:
        violatingPlaces: Set[PetriNet.Place] = set()
        relevantPlaces: Set[PetriNet.Place] = set()
        tokenCount = Counter()
        trace = variant.split(",")
        for p in net[0].places:
            p: PetriNet.Place
            if p in net[1]:  # check if place is part of initial marking
                tokenCount[p] = 1
            else:
                tokenCount[p] = 0

        for activity in trace:
            # Check if incoming places have sufficient token
            # Get every place with an arc to the corresponding (fired) transition
            transition = Utils.getTransitionByName(net[0], activity)
            for p in Utils.getIncomingPlaces(net[0], transition):
                relevantPlaces.add(p)
                # Decrease the token count in that place by 1
                count = tokenCount.get(p)
                assert type(count) == int
                if count > 0:
                    count -= 1
                    tokenCount[p] = count
                else:
                    # Else, if there is no token in the place, it should be removed (later)
                    # placesToRemove.add(p)
                    violatingPlaces.add(p)
            # Place tokens in outgoing places
            for p in Utils.getOutgoingPlaces(net[0], transition):
                relevantPlaces.add(p)
                # Increase the token count in that place by 1
                count = tokenCount.get(p)
                assert type(count) == int
                count += 1
                tokenCount[p] = count
        # in PM4PY there is only one final marking, thus it is sufficient to use this as the "final marking with least violations"
        for p in net[0].places:
            p: PetriNet.Place
            count = tokenCount.get(p)
            assert type(count) == int
            if p in net[2]:
                if count != 1:
                    # placesToRemove.add(p)
                    violatingPlaces.add(p)
            else:
                if count != 0:
                    # placesToRemove.add(p)
                    violatingPlaces.add(p)
        for p in relevantPlaces:
            numberOfRelevantTracesPerPlace[p] = (
                numberOfRelevantTracesPerPlace.get(p, 0)
                + allTracesWithFrequency[variant]
            )
            # First add all relevant traces as fitting, remove the violating ones later
            numberOfFittingTracesPerPlace[p] = (
                numberOfFittingTracesPerPlace.get(p, 0)
                + allTracesWithFrequency[variant]
            )
        for p in violatingPlaces:
            numberOfFittingTracesPerPlace[p] = (
                numberOfFittingTracesPerPlace.get(p, 0)
                - allTracesWithFrequency[variant]
            )
    return {
        p: numberOfFittingTracesPerPlace.get(p, 0)
        / numberOfRelevantTracesPerPlace.get(p, 0)
        if numberOfRelevantTracesPerPlace.get(p, 0) > 0
        else 0
        for p in net[0].places
    }
