# Algorithm
Our solution employs a mix of beam-search and brute force algorithm

    1. Create a graph, initialize total solution, total score and best total score
    2. Loop maxL times: 
        1. get a list of disconnected subgraphs
        2. For each subgraph:
            1. Initialize mapEntity, solution and total score in the subgraph
            2. If subgraph size <= maxB, do brute force searches for the best solution within the subgraph
            3. Else, do beam searches with width maxK for the best solution within the subgraph
            4. add subgraph solution into total solution and update the total score 

We have also made several design choices:
- To speed up the score calculation within a subgraph
   - we run the scoring function (earning, footfall, co2 saving) within a subgraph, avoiding the need to scan through the whole map
   - we have a total_score dictionary to keep track of the score metrics earned in other subgraphs
- We scan through the map multiple times
   - In the first loop, we have no information on the refill station placement of the subgraphs that are not processed yet, thus the effect of footfall and earnings may not be accurate.
   - In the subsequent loop, we already have the station placement in all other stations, allowing the algorithm to calculate the score more accurately.
- We decide which algorithm to run depending on the subgraph size
   - If the size is small, brute force would be used to get a higher score while maintaining a reasonable runtime
   - If the size is large, beam search would be used to speed up the processing time while getting a reasonably high score



# Introduction

This is the submitted code of team Cobra in Considition 2023 using Python.

algorithm.py contains the main code of the refill station placement algorithm.

- graph_mixed_score(): The main function of our solution, a mix of beam-search and brute force algorithm
- algo(): inteface for eval.py
- create_graph(): Create networkx graph from mapEntity
- get_mapEntity_subgraph(): Get a subset of mapEntity where all the locations are in subgraph C
- get_solution_subgreaph(): Get a subset of the solution where all the locations are in subgraph C
- refine_footfall(): Fix rounding error in footfall using scoredSolution calculated from the scoring function
- update_total_score(): Update the game score dictionary total_score using scoredSolution calculated from the scoring function
- try_placing_refill(): Simulate the effect of placing a refill station in a single location in a subgraph
- initize_solution_subgraph(): Reset solutions in a subgraph C

eval.py is the main script for submission:

- Fetching required data
- Submitting a solution to Considition 2023
- Scoring a solution locally and saving the "game"
  - There will be a request limit for the Considition apis so if you wish to train an AI/ML or try some brute force solution you'll have to use the scoring function that comes in this repo.
  - Saved games can be visualized using the notebook in this repo

visualization.ipynb is a notebook for visualizing games.

exploration.ipynb is a notebook for exploratory data analysis of map data.

graph.ipynb is a notebook for exploratory data analysis of graphs.

scoring.py contains the logic for how we score a solution.

api.py contains methods for using the Considition apis.


# Getting Started

We recommended using visual studio code (https://code.visualstudio.com/Download) with the "Jupyter" extension for running the note book in this repo.

----Running eval.py-----

1. Install python 3.11. https://www.python.org/downloads/
2. Navigate to the root folder of the project and create a virtual environment with required dependencies:

```console
   python -m venv .venv
```

3. Activate the virtual environment and run

```console
   pip install -r requirements.txt
```

3. Create a .env file with you api token (see .example.env).

4. Run the program with

```console
   python .\eval.py
```

----Running visualization.ipynb in vs code----

1. Complete above steps
2. Install the jupyter extension in vs code: https://marketplace.visualstudio.com/items?itemName=ms-toolsai.jupyter&ssr=false#review-details
3. Select the .venv created above steps as kernel for the notebook
4. Run the notebook
   - enter a game id
   - Choose to fetch game from the Considtion APP or locally from the "my_games" folder.
