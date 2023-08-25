# Alpha+++ Process Discovery Algorithm
This repository contains the Python source code of the Alpha+++ process discovery algorithm.
The evaluation setup is also available, as well as a Jupyter Notebook to visualize, analyze and process evaluation results.

Detailed information on the algorithm and evaluation results on real-life event logs are available separately.

The corresponding paper "__Revisiting the Alpha Algorithm To Enable Real-Life Process Discovery Applications__" was published at the Algorithms & Theories for the Analysis of Event Data (ATAED) 2023 workshop in Caparica, Portugal.

- Paper: [https://ceur-ws.org/Vol-3424/paper4.pdf](https://ceur-ws.org/Vol-3424/paper4.pdf)
- Extended Report: [https://arxiv.org/abs/2305.17767](https://arxiv.org/abs/2305.17767)
- Presentation: [Slides PDF](https://aar.pm/alphapppslides)


## Parts
- Alpha+++ Source: `experiments/AlphaPPP.py`
- Evaluation Script: `ExperimentRunner.py`
- Visualization/Analyzation Notebook: `vis.ipynb`
- Activity/Transition Removal Experiments: `remove-disconnected-acts.ipynb` 


## Requirements
```
pm4py==2.6.1
Pebble==5.0.3
pandas==1.3.5
numpy==1.21.6
matplotlib==3.5.3
seaborn==0.12.2
```

## License
This source code is available under the MIT license.
For more information, read the LICENSE file in this repository.
