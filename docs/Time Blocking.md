# Time Blocking
$I$ = number of tasks to complete

$K$ = number of periods on the planning horizon

$a_k$ = 1 if period $k$ is available, and 0 otherwise

$p_k$ = 1 if period $k$ is not preferred but is available, 2 if period $k$ is preferred and available, 0 o.w. 

$r_i$ = the required number of 15-minute periods to complete task $i$

$d_i$ = the period that task $i$ is due

$x_{ik} \in {0,1}$ : 1 if task $i$ is worked on during period $k$, 0 otherwise
$y_{ik} \in {0,1}$ : 1 if task $i$ is worked on during a cohesive block starting with period $k$, 0 otherwise

$$\text{Maximize: } \sum_{i=1}^I \sum_{k=1}^K p_k y_{ik} \forall i \in {0,1,\dots,I}, \forall k \in {0,1,\dots,K}:$$



$$\sum_{k}^{k + r_i} x_{i,k} \geq r_i y_{ik}$$ (togetherness constraint)

$$a_k \geq x_{ik} \forall i \in {0,1,\dots,I}, \forall k \in {0,1,\dots,K}$$ (Time period available constraint)

$$\sum_{k=0}^K x_{ik} = r_i \forall i \in {0,1,\dots,I}$$ (Task single completion constraint)

$$\sum_{i=0}^I x_{ik} \leq 1 \forall k \in {0,1,\dots,K}$$ (One task per period constraint)

$$k \geq d_i x_{ik} \forall i \in {0,1,\dots,I}, \forall k \in {0,1,\dots,K}:$$ (Task must be completed before due date)

