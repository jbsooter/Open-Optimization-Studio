# Time Blocking
$I$ is the number of tasks to complete

$K$ = number of periods on the planning horizon

$a_k$ = 1 if period $k$ is available, and 0 otherwise

$p_k$ = 1 if period $k$ is not preferred but is available, 2 if period $k$ is preferred and available, 0 o.w. 

$r_i$ = the required number of 15-minute periods to complete task $i$

$d_i$ = the period that task $i$ is due

$x_{ik} \in {0,1}$ : 1 if task $i$ is worked on during period $k$, 0 otherwise
$y_{ik} \in {0,1}$ : 1 if task $i$ is worked on during a cohesive block starting with period $k$, 0 otherwise

$$\text{Maximize: } \sum_{i=1}^I \sum_{k=1}^K p_k y_{ik} $$

$$\forall i \in {1,2,\dots,I}, \forall k \in {1,2,\dots,K}:$$ (togetherness constraint)

$$\sum_{r=0}^{r_i-1} x_{i,k+r} \geq r_i y_{ik}$$

$$\forall i \in {1,2,\dots,I}, \forall k \in {1,2,\dots,K}: a_k \geq x_{ik} $$ (Time period available constraint)

$$\forall i \in {1,2,\dots,I}: \sum_{k=1}^K x_{ik} = r_i $$ (Task single completion constraint)

$$\forall k \in {1,2,\dots,K}: \sum_{i=1}^I x_{ik} \leq 1 $$ (One task per period constraint)

$$\forall i \in {1,2,\dots,I}, \forall k \in {1,2,\dots,K}:$$ (Task must be completed before due date)

$$\text{if } k \geq d_i, \text{then } x_{ik} = 0 $$