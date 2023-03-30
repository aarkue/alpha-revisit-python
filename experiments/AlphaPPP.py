from typing import Dict, FrozenSet, List, Set, Tuple
from pm4py.objects.petri_net.obj import PetriNet
from pm4py.objects.petri_net.obj import Marking
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to
from util import LogProcessor, START_ACTIVITY, END_ACTIVITY, Utils
import pm4py

from ExperimentAlgorithm import ExperimentAlgorithm
from typing import Dict, List, Set, Tuple
from util import LogProcessor, START_ACTIVITY, END_ACTIVITY, Utils
from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to


from util import ReplayProcessor
# 
# DFG Cleaning
# 
def cleanDFG(dfg: Dict[Tuple[str,str],int], df_thresh = 0.0):
    newDfg : Dict[Tuple[str,str],int] = dict()
    for (a,b) in dfg:
        allOutgoingEdgeValues = [dfg[(x,y)] for (x,y) in dfg if x == a]
        allIncomingEdgeValues = [dfg[(x,y)] for (x,y) in dfg if y == b]
        v = dfg.get((a,b))
        if (v >= 0.01 * sum(allOutgoingEdgeValues)/len(allOutgoingEdgeValues) or v >=  0.01 * sum(allIncomingEdgeValues)/len(allIncomingEdgeValues)) and v > df_thresh:
            newDfg[(a,b)] = v
    return newDfg

# 
# Skip Log Repair
# 
from typing import Dict, List, Set, Tuple
from util import LogProcessor, START_ACTIVITY, END_ACTIVITY, Utils
from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to

def repairLogSkip(logProcessor: LogProcessor, threshold) -> Tuple[LogProcessor,Set[str]]:
    dfg = logProcessor.getDfg()
    df_threshold = threshold
    print("Using df_threshold of " + str(df_threshold)  + " for SkipLogRepair")

    def isSignificantDFBetween(a: str, b: str):
      return dfg.get((a,b),0) >= df_threshold
    newNamedTauActivities : Set[str]= set()
    for a in logProcessor.getActivities():
      if dfg.get((a, a), 0) == 0:
          outgoingFromA = {
              b
              for (x, b) in dfg.keys()
              if x == a and (dfg.get((a, b), 0) >= df_threshold)
          }
          if len(outgoingFromA) > 0:
              canSkip = set()
              for (x, b) in dfg.keys():
                  if x == a and b != a and b in logProcessor.getActivities():
                      if (not isSignificantDFBetween(b, b)) and (
                          not isSignificantDFBetween(b, a)
                      ):
                          outgoingFromB = {
                              c
                              for (x, c) in dfg.keys()
                              if x == b and (dfg.get((b, c), 0) >= df_threshold)
                          }
                          if outgoingFromA.issuperset(outgoingFromB):
                              canSkip.add(b)
              # Update variants and DF
              if len(canSkip) > 0:
                  newNamedTau = "skip_after_" + a
                  assert newNamedTau not in logProcessor.getActivities()
                  variantsBefore = logProcessor.getVariants()
                  variantsAfter: Dict[str, int] = dict()
                  for variant in variantsBefore.keys():
                      variantSplit = variant.split(",")
                      newVariantSplit: List[str] = list()
                      for i in range(len(variantSplit)):
                          newVariantSplit.append(variantSplit[i])
                          if (
                              variantSplit[i] == a
                              and i + 1 < len(variantSplit)
                              and variantSplit[i + 1] not in canSkip
                          ):
                              newVariantSplit.append(newNamedTau)
                      variantsAfter[",".join(newVariantSplit)] = variantsBefore.get(
                          variant, 0
                      )
                  logProcessor.setVariants(variantsAfter)

                  dfCountFromAToOther = 0
                  dfsToDelete = set()
                  for (x, y) in dfg.keys():
                      if x == a and y not in canSkip:
                          dfCountFromAToOther += dfg.get((x, y), 0)
                          dfsToDelete.add((x, y))
                  for (x, y) in dfsToDelete:
                      dfg[(newNamedTau, y)] = dfg.get((x, y))
                      dfg.pop((x, y))
                  dfg[(a, newNamedTau)] = dfCountFromAToOther

                  logProcessor.setDfg(dfg)
                  newNamedTauActivities.add(newNamedTau)
                  logProcessor.getActivityOccurrences()[
                      newNamedTau
                  ] = dfCountFromAToOther
    for newNamedTauAct in newNamedTauActivities:
        print("added new named tau activity: " + newNamedTauAct)
        logProcessor.getActivities().add(newNamedTauAct)
    return logProcessor


# 
# Loop Log Repair
# 
def repairLogLoop(logProcessor: LogProcessor,df_p1: float) -> LogProcessor:

  dfg = logProcessor.getDfg()
  df_threshold = df_p1

  print("Using Loop Log Repair with df_threshold of " + str(df_threshold))

  def isSignificantDFBetween(a: str, b: str):
    return dfg.get((a,b),0) >= df_threshold

  def getSignificantDFActs(a : str):
    return {b for (x,b) in dfg if x == a and dfg.get((x,b),0) > df_threshold}


  def getReachableBF(activity: str):
    reachable : Set[Tuple[str]] = set()
    finishedReachable : Set[Tuple[str]] = set()
    directlyReachable = getSignificantDFActs(activity)
    foundLoops: Set[Tuple[str]] = set()
    for a in directlyReachable:
      if a != activity:
        l = (activity,a)
        reachable.add(l)
    expanded = True
    while expanded:
      expanded = False
      additions: Set[Tuple[str]] = set()
      for visitedActs in reachable:
        lastVisitedAct = visitedActs[len(visitedActs) - 1]
        dfAs : Set[str] = getSignificantDFActs(lastVisitedAct)
        if (lastVisitedAct not in dfAs) or True:
          if len(dfAs) == 0:
            finishedReachable.add(visitedActs)
          else:
            for a in dfAs:
              newPath: Tuple[str] = tuple(visitedActs)
              if a in newPath:
                # Loop found
                finishedReachable.add((*newPath,a))
                foundLoops.add((*newPath,a))
              else:
                additions.add((*newPath,a))
                expanded = True
      reachable = additions
      reachable.difference_update(finishedReachable)
    return foundLoops

  insertNamedTausBetween : Set[Tuple[str,str]]= set()
  bf_approach_reachable: Set[Tuple[str]] = getReachableBF(START_ACTIVITY)
  loop_candidates: Set[Tuple[str]] = {x for x in bf_approach_reachable if x[len(x) - 1] != END_ACTIVITY}
  for path in loop_candidates:
    if len(path) >= 2:
      act = path[len(path) - 1]
      actBefore = path[len(path) - 2]
      insertNamedTausBetween.add((actBefore,act))



  for newNamedTau in insertNamedTausBetween:
    newActName = "skip_loop_" + newNamedTau[0] + "_" + newNamedTau[1]
    assert newActName not in logProcessor.activities
    print("Adding new activity " + newActName)
    variantsBefore: Dict[str,int] = logProcessor.getVariants()
    variantsAfter: Dict[str,int] = dict()
    for variant in variantsBefore:
      newVariant = variant.replace(newNamedTau[0] + "," + newNamedTau[1],newNamedTau[0] + "," + newActName + "," + newNamedTau[1])
      variantsAfter[newVariant] = variantsBefore.get(variant,0)
    logProcessor.setVariants(variantsAfter)

    dfCount = dfg.get(newNamedTau,0)

    logProcessor.getActivities().add(newActName)
    logProcessor.getActivityOccurrences()[newActName] = dfCount

    dfg.pop(newNamedTau)

    dfg[(newNamedTau[0],newActName)] = dfCount
    dfg[(newActName,newNamedTau[1])] = dfCount
  return logProcessor




# 
# Candidate Building
# 
from typing import FrozenSet, Iterable, Set, Tuple
from pm4py.objects.petri_net.obj import PetriNet
from pm4py.objects.petri_net.obj import Marking
from util import LogProcessor, START_ACTIVITY, END_ACTIVITY, Utils
def buildCandidates(logProcessor: LogProcessor) -> Set[Tuple[Set[str],Set[str]]]:
    activities = logProcessor.getActivities()
    activitiesHat = set(activities)
    activitiesHat.add(START_ACTIVITY)
    activitiesHat.add(END_ACTIVITY)

    dfg = logProcessor.getDfg()
    dfRelation = set([key for key,val in dfg.items() if val > 0])

    
    initialCnd : Set[Tuple[FrozenSet[str],FrozenSet[str]]]= set()
    expandCnd : Set[Tuple[FrozenSet[str],FrozenSet[str]]]= set()

    for a in activitiesHat:
      for b in activitiesHat:
        if (a,b) in dfRelation and (b,a) not in dfRelation and (a,a) not in dfRelation and (b,b) not in dfRelation:
          initialCnd.add(( frozenset([a]), frozenset([b]) ))
        else:
          expandCnd.add(( frozenset([a]), frozenset([b]) ))

    cnd = list(initialCnd) + list(expandCnd)
    
    cndSet = set(initialCnd)


    def satisfiesCndCriteria(c):
        a = c[0]
        b = c[1]
        a_without_b = a - b
        b_without_a = b - a
        return  Utils.isNoDFRelationBetweenAsymmetric(dfRelation,a, a_without_b) and Utils.isNoDFRelationBetweenAsymmetric(dfRelation,b_without_a,b) and Utils.areAllRelationsDFBetweenNonStrict(dfRelation,a,b) and Utils.areNotAllRelationsDF_SWITCHED(dfRelation,a_without_b,b_without_a)
    

    i = 0
    while i < len(cnd):
        j = i + 1
        while j < len(cnd):
          if cnd[i] != cnd[j]:
            a1 = cnd[i][0]
            a2 = cnd[i][1]
            b1 = cnd[j][0]
            b2 = cnd[j][1]
            first = frozenset(set(a1).union(b1))
            second = frozenset(set(a2).union(b2))
            if satisfiesCndCriteria((first,second)):
              newCandidate = (first,second)
              if newCandidate not in cndSet:
                cndSet.add(newCandidate)
                cnd.append(newCandidate)
          j += 1
        i += 1
    
    filteredCnd = {cnd for cnd in cndSet if satisfiesCndCriteria(cnd)}
    return filteredCnd



# 
# Fitness Pruning
# 
def getCandidateScore(logProcessor: LogProcessor, candidate:  Tuple[FrozenSet[str],FrozenSet[str]],t: float):
  fittingTraces = 0
  underfedTraces = 0
  overfedTraces = 0
  variants =  logProcessor.getVariants()
  numberOfTracesWithActs = 0;
  fittingWithActs = 0;
  allActsInCandidate = candidate[0].union(candidate[1])
  numOfTracesContainingAct : Dict[str,int] = {a: 0 for a in allActsInCandidate}
  numOfFittingTracesContaingAct: Dict[str,int]  = {a: 0 for a in allActsInCandidate}
  
  for variant in variants.keys():
    weight = variants.get(variant,0)
    tokenCount = 0
    trace = variant.split(",")
    for a in allActsInCandidate:
        if a in trace:
            numOfTracesContainingAct[a] += weight
    if len(set(trace).intersection(candidate[0].union(candidate[1]))) > 0:
      numberOfTracesWithActs += weight;
    for i,act in enumerate(trace):
      if act in candidate[0]:
        tokenCount += 1

      if act in candidate[1]:
        tokenCount -= 1

      if tokenCount < 0:
        underfedTraces += weight
        break
    if tokenCount < 0:
      underfedTraces += weight
    elif tokenCount > 0:
      overfedTraces += weight
    else:
        fittingTraces += weight
        for a in allActsInCandidate:
            if a in trace:
                numOfFittingTracesContaingAct[a] += weight
        if len(set(trace).intersection(candidate[0].union(candidate[1]))) > 0:
            fittingWithActs += weight
  return fittingWithActs/numberOfTracesWithActs >= t and min({numOfFittingTracesContaingAct[a]/numOfTracesContainingAct[a] for a in allActsInCandidate if numOfTracesContainingAct[a] > 0}) >= t if numberOfTracesWithActs > 0 else False

def pruneCandidatesFitness(logProcessor: LogProcessor, candidates:  Set[Tuple[Set[str],Set[str]]], min_fitting_traces: float) -> Set[Tuple[Set[str],Set[str]]]:
  return {c for c in candidates if getCandidateScore(logProcessor,c,min_fitting_traces)}



# 
# Dominated Candidates Pruning
# 
def pruneCandidatesMaximal(logProcessor: LogProcessor, candidates:  Set[Tuple[Set[str],Set[str]]]) -> Set[Tuple[Set[str],Set[str]]]:
  sel : List[Tuple[FrozenSet[str],FrozenSet[str]]] = list()
  def isMaximalPair(pair):
      for c in candidates:
          if c != pair:
              if(c[0].issuperset(pair[0]) and c[1].issuperset(pair[1])):
                  return False
      return True

  sel = list(filter(isMaximalPair,candidates))
  return sel


# 
# Build Petri Net
# 
from util import LogProcessor, START_ACTIVITY, END_ACTIVITY, Utils
from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to, remove_transition
candidatePlaceMap : Dict[Tuple[FrozenSet[str],FrozenSet[str]],PetriNet.Transition]= dict()
def buildPetriNet(logProcessor: LogProcessor, candidates:  Set[Tuple[Set[str],Set[str]]]) -> Tuple[PetriNet,Marking,Marking]:
      candidatePlaceMap = dict();
      places : Dict[Tuple[FrozenSet[str],FrozenSet[str]],PetriNet.Place]= dict()
      initialMarking : Marking = Marking()
      finalMarking : Marking = Marking()
      for e in candidates:
          places[e] = PetriNet.Place(str(e))
          if START_ACTIVITY in e[0]:
              initialMarking[places[e]] = 1
          if END_ACTIVITY in e[1]:
              finalMarking[places[e]] = 1

      for act in logProcessor.activities:
        if act.startswith("skip_"):
            candidatePlaceMap[act] = PetriNet.Transition(name=act,label=None)
        else:
            candidatePlaceMap[act] = PetriNet.Transition(name=act, label=act)

      net = PetriNet('Alpha PN',places=set(places.values()), transitions=set(candidatePlaceMap.values()))

      for e in candidates:
          for a in e[0]:
              if a in logProcessor.activities:
                  fr = candidatePlaceMap[a]
                  to = places[e]
                  add_arc_from_to(fr,to,net)
          for a in e[1]:
              if a in logProcessor.activities:
                  to = candidatePlaceMap[a]
                  fr = places[e]
                  add_arc_from_to(fr,to,net)

      transitionsToRemove : Set = set()
      for t in net.transitions:
          t : PetriNet.Transition
          if len(t.in_arcs) == 0 and len(t.out_arcs) == 0 and t.label is None:
              transitionsToRemove.add(t)
      for t in transitionsToRemove:
          remove_transition(net,t)
      return (net,initialMarking,finalMarking);



def pruneCandidatesBalance(lp, candidates, b: float):
  return set(c for c in candidates if getBalance(lp,c[0],c[1]) <= b)

def getBalance(lp, aEls : Iterable[str], bEls: Iterable[str]):
  countAEls = getNumberOfOccurrences(lp,aEls)
  countBEls = getNumberOfOccurrences(lp,bEls)
  return abs(countAEls - countBEls) / max(countAEls, countBEls)

def getNumberOfOccurrences(lp, aEls: Iterable[str]):
  return sum([lp.getActivityOccurrence(act) for act in aEls])


# 
# Complete Algorithm
# 
class AlphaPPP(ExperimentAlgorithm):
    def __init__(self, variant: str) -> None:
        self.variant = variant

    def execute_steps(self, log_processor: LogProcessor):
      if self.variant.startswith("TAB|"):
          repair_thresh = float(self.variant[4:7])
          if self.variant.endswith("|b0.5|t0.5|r0.5"):
              lp = log_processor
              mean_df_value = sum(lp.dfg.values()) / len(lp.dfg)
              skip_log_repair_df_threshold = repair_thresh * mean_df_value
              loop_log_repair_df_threshold = repair_thresh * mean_df_value
              balance_value = 0.5
              candidate_pruning_local_fitness_required = 0.5
              replay_local_fitness_required = 0.5
              lp = repairLogLoop(lp, df_p1=loop_log_repair_df_threshold)
              lp = repairLogSkip(lp, skip_log_repair_df_threshold)
              # Advising DFG
              dfg = cleanDFG(lp.dfg, 1)
              lp.setDfg(dfg)
          elif self.variant.endswith("|b0.3|t0.7|r0.6"):
              lp = log_processor
              mean_df_value = sum(lp.dfg.values()) / len(lp.dfg)
              skip_log_repair_df_threshold = repair_thresh * mean_df_value
              loop_log_repair_df_threshold = repair_thresh * mean_df_value
              balance_value = 0.3
              candidate_pruning_local_fitness_required = 0.7
              replay_local_fitness_required = 0.6
              lp = repairLogLoop(lp, df_p1=loop_log_repair_df_threshold)
              lp = repairLogSkip(lp, skip_log_repair_df_threshold)
              # Advising DFG
              dfg = cleanDFG(lp.dfg, 1)
              lp.setDfg(dfg)
          elif self.variant.endswith("|b0.2|t0.8|r0.7"):
              lp = log_processor
              mean_df_value = sum(lp.dfg.values()) / len(lp.dfg)
              skip_log_repair_df_threshold = repair_thresh * mean_df_value
              loop_log_repair_df_threshold = repair_thresh * mean_df_value
              balance_value = 0.2
              candidate_pruning_local_fitness_required = 0.8
              replay_local_fitness_required = 0.7
              lp = repairLogLoop(lp, df_p1=loop_log_repair_df_threshold)
              lp = repairLogSkip(lp, skip_log_repair_df_threshold)
              # Advising DFG
              dfg = cleanDFG(lp.dfg, 1)
              lp.setDfg(dfg)
          elif self.variant.endswith("|b0.2|t0.8|r0.8"):
              lp = log_processor
              mean_df_value = sum(lp.dfg.values()) / len(lp.dfg)
              skip_log_repair_df_threshold = repair_thresh * mean_df_value
              loop_log_repair_df_threshold = repair_thresh * mean_df_value
              balance_value = 0.2
              candidate_pruning_local_fitness_required = 0.8
              replay_local_fitness_required = 0.8
              lp = repairLogLoop(lp, df_p1=loop_log_repair_df_threshold)
              lp = repairLogSkip(lp, skip_log_repair_df_threshold)
              # Advising DFG
              dfg = cleanDFG(lp.dfg, 1)
              lp.setDfg(dfg)
          elif self.variant.endswith("|b0.1|t0.9|r0.9"):
              lp = log_processor
              mean_df_value = sum(lp.dfg.values()) / len(lp.dfg)
              skip_log_repair_df_threshold = repair_thresh * mean_df_value
              loop_log_repair_df_threshold = repair_thresh * mean_df_value
              balance_value = 0.1
              candidate_pruning_local_fitness_required = 0.9
              replay_local_fitness_required = 0.9
              lp = repairLogLoop(lp, df_p1=loop_log_repair_df_threshold)
              lp = repairLogSkip(lp, skip_log_repair_df_threshold)
              # Advising DFG
              dfg = cleanDFG(lp.dfg, 1)
              lp.setDfg(dfg)
          else:
             raise ValueError("Unknown Parameter Configuration")

      cnd = buildCandidates(lp)
      cnd = pruneCandidatesBalance(lp,cnd,balance_value)
      cnd = pruneCandidatesFitness(lp, cnd, candidate_pruning_local_fitness_required)
      sel = pruneCandidatesMaximal(lp, cnd)
      net, im, fm = buildPetriNet(lp, sel)

      # Replay
      replay_res = ReplayProcessor.replayWithAllTraces((net,im,fm),lp.getVariants())
      replay_res_problematic_places = {p for p in replay_res if replay_res[p] < replay_local_fitness_required}
      from pm4py.objects.petri_net.utils.petri_utils import remove_place
      for p in replay_res_problematic_places:
          remove_place(net,p)
          if p in im:
            im.pop(p)
          if p in fm:
            fm.pop(p)

      return (net, im, fm)

    def execute(self, log: EventLog) -> Tuple[PetriNet, Marking, Marking]:
        raise NotImplementedError
