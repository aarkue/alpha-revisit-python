import datetime
import math
import pickle
import time
from typing import Dict

# Alpha Revisit
from experiments import AlphaPPP, AlphaMiner, InductiveMinerInfrequent
from util import LogProcessor
from ExperimentAlgorithm import ExperimentAlgorithm

# Plots
import matplotlib.pyplot as plt
import seaborn as sns

# NumPy
from numpy import NaN

# Concurrency
from pebble import concurrent, ProcessFuture
from concurrent.futures import TimeoutError

# PM4Py
import pm4py
from pm4py.algo.evaluation.simplicity import algorithm as simplicity_evaluator
from pm4py.algo.evaluation.generalization import algorithm as generalization_evaluator
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay

# Timeout in seconds before aborting computation of alignments etc. (only used in concurrent evaluation)
SECONDS_TIMEOUT = 1.5 * 60 * 60

# Path where the results (pickle, txt, svg plots and process models) should be saved 
SAVE_PATH = "./figures/"
# Path where event logs (see list below) are saved
EVENT_LOGS_PATH = "./event_logs/"

# Use Multiprocessing for alignment computation (only used for linear/non-concurrent evaluation)
LINEAR_USE_MULTIPROCESSING = True

def runExperiments(
    logsWithPath: Dict[str, str], algorithms: Dict[str, ExperimentAlgorithm]
):
    for log_name in logsWithPath:
        print("Evaluating on " + log_name)
        log = pm4py.read_xes(logsWithPath[log_name])
        algo_results_futures: Dict[str, ProcessFuture] = dict()
        algo_results: Dict[str, Dict[str, float]] = dict()
        for algo_name in algorithms:
            print("Using " + algo_name)
            algo_results_futures[algo_name] = getAlgoResultConcurrent(
                log_name, log, algo_name, algorithms[algo_name]
            )
        for key in algo_results_futures:
            try:
                v = algo_results_futures[key].result()
                algo_results[key] = v
            except Exception as e:
                print(f"Could not compute value {key}: {str(e)}")
        saveResAsPickle(log_name, algo_results)
        visualizeRes(log_name, algo_results)



def runLinear(
    logsWithPath: Dict[str, str], algorithms: Dict[str, ExperimentAlgorithm]
):
    for log_name in logsWithPath:
        print("Linear Evaluating on " + log_name)
        log = pm4py.read_xes(logsWithPath[log_name])
        algo_results: Dict[str, Dict[str, float]] = dict()
        for algo_name in algorithms:
            algo_res = getAlgoResultLinear(log_name, log, algo_name, algorithms[algo_name])
            print(algo_res)
            algo_results[algo_name] = algo_res
        saveResAsPickle(log_name, algo_results)
        visualizeRes(log_name, algo_results)
        print("Finished Linear Evaluation on " + log_name)

def getAlgoResultLinear(
    log_name: str,
    log: pm4py.objects.log.obj.EventLog,
    algo_name: str,
    algo: ExperimentAlgorithm,
):
    values = {
        "number_places": 0,
        "number_transitions": 0,
        "number_arcs": 0,
        "discover_duration": 0,
        "token_fitness": 0,
        "token_precision": 0,
        "alignment_precision": 0,
        "alignment_fitness": 0,
        "simplicity": 0,
        "generalization": 0,
    }
    log_processor = LogProcessor(log)
    start_time = time.time()
    try:
        print(f"Discovering model...")
        net, initial_marking, final_marking = discover(algo, log_processor)
        values["discover_duration"] = time.time() - start_time
        print(
            f"Discovered model for {log_name} with {algo_name} in {values['discover_duration']}s"
        )
        timestamp = datetime.datetime.now().isoformat()
        pm4py.write_pnml(net,initial_marking,final_marking,f"{SAVE_PATH}{log_name}_model_{algo_name}_{timestamp}.pnml")
        pm4py.save_vis_petri_net(net,initial_marking,final_marking,f"{SAVE_PATH}{log_name}_model_{algo_name}_{timestamp}.svg")
        start_time = time.time()
        
        try:
            values['alignment_fitness'] = pm4py.fitness_alignments(log, net, initial_marking, final_marking, LINEAR_USE_MULTIPROCESSING)["average_trace_fitness"]
        except Exception as e:
            print(f"Could not compute alignment fitness: {str(e)}")
            values["alignment_fitness"] = NaN
        
        try:
            values['alignment_precision'] = pm4py.precision_alignments(log, net, initial_marking, final_marking, LINEAR_USE_MULTIPROCESSING)
        except Exception as e:
            print(f"Could not compute alignment precision: {str(e)}")
            values["alignment_precision"] = NaN

        values["number_places"] = len(net.places)
        values["number_transitions"] = len(net.transitions)
        values["number_arcs"] = len(net.arcs)
    except Exception as e:
        print(e)
        pass

    return {
    "number of places": values["number_places"],
    "number of transitions": values["number_transitions"],
    "number of arcs": values["number_arcs"],
    "duration (s)": values["discover_duration"],
    "fitness (alignment) %": (values["alignment_fitness"] * 100),
    "precision (alignment) %": (values["alignment_precision"] * 100),
    "fitness (token) %": (values["token_fitness"] * 100),
    "precision (token) %": (values["token_precision"] * 100),
    "simplicity %": values["simplicity"] * 100,
    "generalization %": values["generalization"] * 100,
    }

def saveResAsPickle(log_name, log_results: Dict[str, Dict[str, float]]):
    time_stamp = datetime.datetime.now().isoformat()
    with open(f"{SAVE_PATH}algo_res{time_stamp}_{log_name}.pickle", "wb") as f:
        pickle.dump(log_results, f)


def visualizeRes(log_name: str, log_results: Dict[str, Dict[str, float]]):
    metrics: Dict[
        str, Dict[str, float]
    ] = (
        {}
    )  # Metric (e.g. fitness) -> {alpha miner -> 0.7, inductive miner-> 1.0, ...}, ...
    for (algo_name, algo_results) in log_results.items():
        for (metric_name, metric_value) in algo_results.items():
            metric_entry = metrics.get(metric_name, {})
            metric_entry[algo_name] = metric_value
            metrics[metric_name] = metric_entry
    print(metrics)
    columns = 2
    rows = math.ceil(len(metrics) / float(columns))
    fig, axs = plt.subplots(
        rows, columns, figsize=(columns * 3, 10 * len(log_results) * rows), sharey=False
    )
    fig.set_figwidth(5 * 4 * len(metrics))
    fig.set_figheight(3 * 7 * len(metrics))
    index = 0
    time_stamp = datetime.datetime.now().isoformat()
    with open(f"{SAVE_PATH}{time_stamp}_{log_name}.txt", "w") as f:
        f.write(str(metrics))
    for (metric_name, metric_values) in metrics.items():
        names = list(metric_values.keys())
        values = list(metric_values.values())
        a = axs[math.floor(index / float(columns))][index % columns]
        sns.barplot(x=names, y=values, palette="muted", ax=a)
        a.set_title(metric_name)
        if "%" in metric_name:
            a.set_ylim(0, 100)
        index += 1
    fig.suptitle(log_name + " (Timeout: " + str(SECONDS_TIMEOUT) + "s)")
    fig.savefig(f"{SAVE_PATH}res_{time_stamp}_{log_name}.svg")
    fig.clear()
    plt.close("all")


@concurrent.process(daemon=False)
def getAlgoResultConcurrent(
    log_name: str,
    log: pm4py.objects.log.obj.EventLog,
    algo_name: str,
    algo: ExperimentAlgorithm,
):
    algo_res = dict()
    values = {
        "number_places": 0,
        "number_transitions": 0,
        "number_arcs": 0,
        "discover_duration": 0,
        "token_fitness": 0,
        "token_precision": 0,
        "alignment_precision": 0,
        "alignment_fitness": 0,
        "simplicity": 0,
        "generalization": 0,
    }
    log_processor = LogProcessor(log)
    start_time = time.time()
    try:
        print(f"Discovering model...")
        net, initial_marking, final_marking = discover(algo, log_processor)
        values["discover_duration"] = time.time() - start_time
        print(
            f"Discovered model for {log_name} with {algo_name} in {values['discover_duration']}s"
        )
        timestamp = datetime.datetime.now().isoformat()
        pm4py.write_pnml(net,initial_marking,final_marking,f"{SAVE_PATH}{log_name}_model_{algo_name}_{timestamp}.pnml")
        pm4py.save_vis_petri_net(net,initial_marking,final_marking,f"{SAVE_PATH}{log_name}_model_{algo_name}_{timestamp}.svg")
        start_time = time.time()
        print("evaluating now...")
        future_list = dict()
        
        try:
            future_list['token_fitness'] = token_fitness_with_timeout(log,net,initial_marking,final_marking)
        except Exception as e:
            print(f"Could not compute token fitness value {str(e)}")
            values['token_fitness'] = NaN
        try:
            values['token_fitness'] = future_list["token_fitness"].result()
        except Exception as e:
            print(f"Could not compute token fitness {str(e)}")
            
        try:
            future_list["alignment_fitness"] = alignment_fitness_with_timeout(
                log, net, initial_marking, final_marking
            )
        except Exception as e:
            print(f"Could not compute alignment fitness value {str(e)}")
            values["alignment_fitness"] = NaN
        try:
            values['alignment_fitness'] = future_list["alignment_fitness"].result()
        except Exception as e:
            print(f"Could not compute alignment fitness {str(e)}")

        try:
            future_list["token_precision"] = token_precision_with_timeout(
                log, net, initial_marking, final_marking
            )
        except Exception as e:
            print(f"Could not compute token precision value {str(e)}")
            values["token_precision"] = NaN
        try:
            values['token_precision'] = future_list["token_precision"].result()
        except Exception as e:
            print(f"Could not compute token precision {str(e)}")

        try:
            future_list["alignment_precision"] = alignment_precision_with_timeout(
                log, net, initial_marking, final_marking
            )
        except Exception as e:
            print(f"Could not compute alignment precision value {str(e)}")
            values["alignment_precision"] = NaN
        try:
            values['alignment_precision'] = future_list["alignment_precision"].result()
        except Exception as e:
            print(f"Could not compute alignment precision {str(e)}")


        try:
            future_list["simplicity"] = simplicity_with_timeout(
                log, net, initial_marking, final_marking
            )
        except Exception as e:
            print(f"Could not compute simplicity value {str(e)}")
            values["simplicity"] = NaN
        try:
            future_list['generalization'] = generalization_with_timeout(log,net,initial_marking,final_marking)
        except Exception as e:
            print(f"Could not compute alignment generalization value {str(e)}")
            values['generalization'] = NaN

        try:
            values['simplicity'] = future_list["simplicity"].result()
            values['generalization'] = future_list["generalization"].result()
        except Exception as e:
            print(f"Could not compute simplicity or generalization {str(e)}")

        for key in future_list:
            try:
                value = future_list[key].result()
                values[key] = value
            except Exception as e:
                print(f"Could not compute value {key}: {str(e)}")
                if type(e) == TimeoutError:
                    values[key] = 0
                else:
                    values[key] = -0
        evaluate_duration = time.time() - start_time
        print(
            f"Computed fitness and precision for model for {log_name} with {algo_name} in {evaluate_duration}s"
        )

        values["number_places"] = len(net.places)
        values["number_transitions"] = len(net.transitions)
        values["number_arcs"] = len(net.arcs)
    except Exception as e:
        print(e)
        print(f"FAILED to discover model for {log_name} with {algo_name} ({e})")
    algo_res[algo_name] = {
        "number of places": values["number_places"],
        "number of transitions": values["number_transitions"],
        "number of arcs": values["number_arcs"],
        "duration (s)": values["discover_duration"],
        "fitness (alignment) %": (values["alignment_fitness"] * 100),
        "precision (alignment) %": (values["alignment_precision"] * 100),
        "fitness (token) %": (values["token_fitness"] * 100),
        "precision (token) %": (values["token_precision"] * 100),
        "simplicity %": values["simplicity"] * 100,
        "generalization %": values["generalization"] * 100,
    }
    del log_processor
    return {
        "number of places": values["number_places"],
        "number of transitions": values["number_transitions"],
        "number of arcs": values["number_arcs"],
        "duration (s)": values["discover_duration"],
        "fitness (alignment) %": (values["alignment_fitness"] * 100),
        "precision (alignment) %": (values["alignment_precision"] * 100),
        "fitness (token) %": (values["token_fitness"] * 100),
        "precision (token) %": (values["token_precision"] * 100),
        "simplicity %": values["simplicity"] * 100,
        "generalization %": values["generalization"] * 100,
    }


def discover(algo, log_processor):
    return algo.execute_steps(log_processor)


@concurrent.thread(timeout=SECONDS_TIMEOUT)
def alignment_fitness_with_timeout(log, net, im, fm):
    return pm4py.fitness_alignments(log, net, im, fm, True)["average_trace_fitness"]


@concurrent.thread(timeout=SECONDS_TIMEOUT)
def alignment_precision_with_timeout(log, net, im, fm):
    return pm4py.precision_alignments(log, net, im, fm, True)


@concurrent.process(timeout=SECONDS_TIMEOUT)
def token_fitness_with_timeout(log, net, im, fm):
    return pm4py.fitness_token_based_replay(log, net, im, fm)["average_trace_fitness"]


@concurrent.process(timeout=SECONDS_TIMEOUT)
def token_precision_with_timeout(log, net, im, fm):
    return pm4py.precision_token_based_replay(log, net, im, fm)


@concurrent.process(timeout=SECONDS_TIMEOUT)
def simplicity_with_timeout(log, net, im, fm):
    return simplicity_evaluator.apply(net)


@concurrent.process(timeout=SECONDS_TIMEOUT)
def generalization_with_timeout(log, net, im, fm):
    return generalization_evaluator.apply(log, net, im, fm)


@concurrent.process(timeout=SECONDS_TIMEOUT)
def compute_token_replay_with_timeout(log, net, im, fm):
    replay_result = token_replay.apply(log, net, im, fm)
    return replay_result


if __name__ == "__main__":
    font = {
        "size": 62
    }
    plt.rc("font", **font)
    runLinear(
        {
            "BPI_Challenge_2020_DomesticDeclarations": f"{EVENT_LOGS_PATH}DomesticDeclarations.xes.gz",
            "BPI_Challenge_2020": f"{EVENT_LOGS_PATH}BPI_Challenge_2020_request_for_payments.xes",
            "BPI_Challenge_2019_sampled_3000cases": f"{EVENT_LOGS_PATH}BPI_Challenge_2019_sampled3000.xes",
            "Sepsis": f"{EVENT_LOGS_PATH}Sepsis Cases - Event Log.xes.gz",
            "RTFM": f"{EVENT_LOGS_PATH}Road_Traffic_Fine_Management_Process.xes.gz",
        },
        {
        # Standard Alpha Configurations
            "α Top10": AlphaMiner("Top10Variants"),
            "α 10%Cov": AlphaMiner("10%Coverage"),
            "α 50%Cov": AlphaMiner("50%Coverage"),
            "α 80%Cov": AlphaMiner("80%Coverage"),

        # Inductive Miner Infrequent Configurations
            "IMf 0.1": InductiveMinerInfrequent(0.1),
            "IMf 0.2": InductiveMinerInfrequent(0.2),
            "IMf 0.3": InductiveMinerInfrequent(0.3),
            "IMf 0.4": InductiveMinerInfrequent(0.4),
        

        # Alpha+++ Configuration
            "α+++|4.0|b0.5|t0.5|r0.5": AlphaPPP("TAB|4.0|b0.5|t0.5|r0.5"),
            "α+++|4.0|b0.3|t0.7|r0.6": AlphaPPP("TAB|4.0|b0.3|t0.7|r0.6"),
            "α+++|4.0|b0.2|t0.8|r0.7": AlphaPPP("TAB|4.0|b0.2|t0.8|r0.7"),
            "α+++|4.0|b0.2|t0.8|r0.8": AlphaPPP("TAB|4.0|b0.2|t0.8|r0.8"),
            "α+++|4.0|b0.1|t0.9|r0.9": AlphaPPP("TAB|4.0|b0.1|t0.9|r0.9"),

            "α+++|2.0|b0.5|t0.5|r0.5": AlphaPPP("TAB|2.0|b0.5|t0.5|r0.5"),
            "α+++|2.0|b0.3|t0.7|r0.6": AlphaPPP("TAB|2.0|b0.3|t0.7|r0.6"),
            "α+++|2.0|b0.2|t0.8|r0.7": AlphaPPP("TAB|2.0|b0.2|t0.8|r0.7"),
            "α+++|2.0|b0.2|t0.8|r0.8": AlphaPPP("TAB|2.0|b0.2|t0.8|r0.8"),
            "α+++|2.0|b0.1|t0.9|r0.9": AlphaPPP("TAB|2.0|b0.1|t0.9|r0.9"),
        },
    )
