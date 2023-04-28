## Linear Programming

Linear Programming is **"a method to achieve the best outcome (such as maximum profit or lowest cost) in a mathematical model whose requirements are represented by linear relationships."** 
([Wikipedia](https://en.wikipedia.org/wiki/Linear_programming)). The Simplex algorithm ([Wikipedia](https://en.wikipedia.org/wiki/Simplex_algorithm)) and its extensions ([Branch and Bound](https://en.wikipedia.org/wiki/Integer_programming)) can be used to solve optimization problems composed of continous, integer, and binary variables with linear objective functions and constraining inequalities. 

This module allows the user to: 

- Define a linear or integer program in standard form and solve it. 
- Perform sensitivity analysis on linear programs with exclusively continuous variables. 
- Visualize the solution to a two-variable linear program. 

### Formulating a Model

Two methods are supplied for formulating a model. The first, [Tableau](#tableau) is implemented with streamlit's editable dataframe functionality, and is built around the traditional simplex tableau in mind. The second, [LP](#lp), follows a modeling language created by MIT that closely follows mathematical notation for linear functions. 

### Tableau
Consider the following linear program: 

max: $3x + 2y$

$2x + y \leq 100$ (1)

$x + y \leq 80$ (2)

$1x  \leq 40$ (3)

$x \geq 0$ (4)

$y \geq 0$ (5)

$x$ and $y$ are continuous. 

In this model, x and y are positive, continuous variables. The LP would be represented in the Open Optimization Studio tableau as follows: 

| obj |var1 | var2 |
| --- | --- | --- |
| max | 3 | 2 |

| var1 |var2 | inequality | RHS |
| --- | --- | --- | --- |
| c | c |  | 
| 2.0 | 1.0 | <= | 100.0 | 
| 1.0 | 1.0 | <= | 80.0 | 
| 1.0 | 0.0 | <=| 40.0 | 

Each column represents a variable. For example, **var1** is continous, as denoted by 'c'. Constraints 4 and 5 are not included in the tableau because all variables are assumed to be non-negative in standard form. 

After running the solver, you will see the following output. 

An optimal solution was found in 0.001 s.

| obj |var1 | var2 |
| --- | --- | --- |
| 180 | 20 | 60 |

<!--- The sensitivity of the constraint set is as follows:
Need to double check math on this. 
| Name |Shadow Price | Slack |
| --- | --- | --- |
| c1 | 1 | 0 |
| c2 | 1 | 0 |
| c3 | 0 | 20 |
-->
![2 Variable Graphical Representation](images/graphical-representation.png)

If I wanted to model var1 as a binary variable, I would simply change the type declaration in the first row of the Tableau: 

| var1 |var2 | inequality | RHS |
| --- | --- | --- | --- |
| b | c |  | 
| 2.0 | 1.0 | <= | 100.0 | 
| 1.0 | 1.0 | <= | 80.0 | 
| 1.0 | 0.0 | <=| 40.0 | 

After re-running the solver, you will obtain a new solution. 

An optimal solution was found in 0.042 s.

| obj |var1 | var2 |
| --- | --- | --- |
| 161 | 1 | 79 |

Notice, no graphical representation appears because it is only available for two variable, continuous examples. 

Additional constraints may be created with the **+** UI element at the bottom of the editable tableau. Additional variable columns can be created with the **Add Variable** button. 

### LP

Alternatively, a model can be formulated in the LP language, which was created as a syntax for linear optimization by MIT. The LP syntax has the characteristics: 

- Every line is followed by a semicolon;
- Inequalities are represented with the following symbols [<=, >=, <,>,=]
- The objective function direction is represented with keywords **max** and **min** followed by a colon. 
- constraints can be named by specifying a name followed by a colon ahead of the constraint expression. 
- variables default to being continuous, but can be declared **int** (integer) or **bin** (binary). 
- one line comments can be added with **//** and block comments are supported with **/\* \*/**

The original model could be created as follows in the LP syntax: 

```
max: 3x + 2y;

        c1: 2x + y <= 100;

        c2: x + y <= 80;

        c3: x  <= 40;

        x >= 0;

        y >= 0;
```

Unsurprisingly, the same optimal solution is found. 

| obj |var1 | var2 |
| --- | --- | --- |
| 180 | 20 | 60 |

To constrain x to binary values and y to integer values, the following variable declarations can be added:

```
max: 3x + 2y;

        c1: 2x + y <= 100;

        c2: x + y <= 80;

        c3: x  <= 40;

        x >= 0;

        y >= 0;
        
        bin x;
        
        int y;

```

In the LP syntax, first the objective is declared, then the constraints, then variables are declared. If no declaration is made for a used variable, it is considered continuous. 

For complete documentation of the LP syntax, see this [page](https://web.mit.edu/lpsolve/doc/lp-format.htm). 

