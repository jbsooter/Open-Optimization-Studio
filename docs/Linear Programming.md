## Linear Programming

Linear Programming is **"a method to achieve the best outcome (such as maximum profit or lowest cost) in a mathematical model whose requirements are represented by linear relationships."** 
([Wikipedia](https://en.wikipedia.org/wiki/Linear_programming)). The Simplex algorithm ([Wikipedia](https://en.wikipedia.org/wiki/Simplex_algorithm)) and its extensions ([Branch and Bound](https://en.wikipedia.org/wiki/Integer_programming)) can be used to solve optimization problems composed of continous, integer, and binary variables with linear objective functions and constraining inequalities. 

This module allows the user to: 

- Define a linear or integer program in standard form and solve it. 
- Perform basic sensitivity analysis on linear programs with exclusively continuous variables. 
- Visualize the solution to a two-variable linear program. 
- Import/Export models and solutions as Excel files. 

### Formulating a Model

Consider the following linear program: 

max: $3x + 5y$

$2x + y \leq 10$ (1)

$x + 3y \leq 12$ (2)

$1x + 1y \geq 5$ (3)

$x \geq 0$ (4)

$y \geq 0$ (5)

$x$ and $y$ are continuous. 

In this model, x and y are positive, continuous variables. The LP would be represented in the Open Optimization Studio tableau as follows: 

| obj |var1 | var2 |
| --- | --- | --- |
| max | 3 | 5 |

| var1 |var2 | inequality | RHS |
| --- | --- | --- | --- |
| c | c |  | 
| 2.0 | 1.0 | <= | 10.0 | 
| 1.0 | 1.0 | <= | 12.0 | 
| 1.0 | 0.0 | >=| 5.0 | 

Each column represents a variable. For example, **var1** is continous, as denoted by 'c'. Constraints 4 and 5 are not included in the tableau because all variables are assumed to be non-negative in standard form. 

//TODO: show output and basic explanation of graphical representation and sensitivity

//TODO: show example with binary and integer vars, changing names, negative coefficient

//TODO: show input, output, settings

//TODO: activity
