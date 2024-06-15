import heapq
import random

import networkx as nx
import numpy as np

infinity = np.Infinity

class Label:
    def __init__(self, node, costs,predecessor):
        self.node = node
        self.costs = costs
        self.predecessor = predecessor
        self.label_list = []
        if predecessor is not None:
            for x in self.predecessor.label_list:
                self.label_list.append(x)
            self.label_list.append(node)
        else:
            self.label_list.append(node)
    #define priority according to "lexographic min" analogous to java comparator
    def __lt__(self, other):
        c = self.costs
        cc = other.costs

        for i in range(len(c)):
            #if equal, move to next cost
            if c[i] == cc[i]:
                continue
            #if less, then true
            elif c[i] < cc[i]:
                return True
            else:
                return False
        return False

    def dominance_check(self, other):
        c = self.costs
        cc = other.costs

        counter = 0

        for i in range(0,len(c)):
            if c[i] <= cc[i]:
                #count the better objectives
                if c[i] < cc[i]:
                    counter += 1
            #if there is ever a worse, return false
            if c[i] > cc[i]:
                return False

        if counter >= 1:
            return True
        else:
            return False

    def __str__(self):
            return  str(self.node) + " <- " + str(self.predecessor) + str(self.label_list)

def nextCandidateLabel(v,lastProcessedLabel,sigma, L, G):
    l_v = Label(v, [infinity, infinity],None)

    for u in sigma:
        for k in range(lastProcessedLabel[(u,v)],len(L[u])):
                l_u = L[u][k]
                l_new = Label(v, [label_costs + new_costs for label_costs, new_costs in zip(l_u.costs,G.edges[(u,v)]["costs"])], l_u)

                #print(l_new.costs)
                lastProcessedLabel[(u,v)] = k

                if L[v][-1].dominance_check(l_new) is False:
                    if l_new.__lt__(l_v):
                        l_v = l_new
                        break

    if l_v.costs[0] is not infinity:
        return None
    return l_v

def propogate(l_v, w, H,L, G):
    l_new = Label(w,[label_costs + new_costs for label_costs, new_costs in zip(l_v.costs,G.edges[(l_v.node,w)]["costs"])], l_v)

    if L[w][-1].dominance_check(l_new) is False:

        existing_labels = [label for label in H if label.node == w]
        heapq.heapify(H)
        if len(existing_labels) == 0:
            heapq.heappush(H, l_new)
        elif l_new.__lt__(existing_labels[0]):
            H.remove(existing_labels[0])
            heapq.heapify(H)
            heapq.heappush(H, l_new)
    return H

def one_to_all(G,source):
    H = []
    heapq.heapify(H)

    L = {}

    for v,data in G.nodes.data():
        if v == source:
            L[v] = [Label(v,[0,0],None)]
        else:
            L[v] = [Label(v,[infinity,infinity],None)]

    last_processed_label = {}
    for a in G.edges:
        last_processed_label[a] = 0

    heapq.heappush(H, Label(source,[0,0],None))

    #line 7
    count = 0
    while len(H) > 0:
        l_v_star = heapq.heappop(H)
        L[l_v_star.node].append(l_v_star)

        u = []
        for uu, v in G.in_edges(l_v_star.node):
            u.append(uu)

        #running nextCandidate only for source
        #if l_v_star.node is source:
            #l_v_new = nextCandidateLabel(l_v_star.node,last_processed_label,u,L, G)
            #if l_v_new is not None:
            #    heapq.heappush(H,l_v_new)

        #running nextCandidate as described in MOSP paper
        l_v_new = nextCandidateLabel(l_v_star.node,last_processed_label,u,L, G)
        if l_v_new is not None:
            heapq.heappush(H,l_v_new)

        sigma_plus = []
        for u, v in G.out_edges(l_v_star.node):
            sigma_plus.append(v)

        for w in sigma_plus:
            H = propogate(l_v_star,w,H,L,G)
            heapq.heapify(H)


        #print("iteration")
        #print(count)
        #count = count + 1
        #for x in L.values():
            #print(x[-1])
        #    for xx in x:
        #        print(xx)

    return L

def main():
    G = nx.DiGraph()

    print("Source is 1. Small case where 1-2-3 is still preferred even though distance is large, because elevation is an order of maginude larger. ")
    G.add_edge(1,2,costs=[1,1])
    G.add_edge(2,1,costs = [1,1])
    G.add_edge(1,3,costs=[1,1000000000])
    G.add_edge(3,1,costs=[1,1])
    G.add_edge(2,3,costs=[100000,100000])
    G.add_edge(3,2,costs=[1,1])

    #run multiple objective with source node 1
    result = one_to_all(G,1)


    print("MOSP solution")
    for x in result.values():
        print(str(x[-1].label_list) + ", costs: " + str(x[-1].costs))


    print("Source is 1. Generated, complete graph case, single objective")
    # Generate a complete graph w/ 10 nodes and add random edges
    complete_graph = nx.complete_graph(10)
    G = nx.DiGraph()

    G.add_nodes_from(complete_graph.nodes)

    random.seed(0)
    for u, v in complete_graph.edges:
            G.add_edge(u, v, costs=[random.randint(1,10), 0])
            G.add_edge(v, u,costs=[random.randint(1,10), 0])

    #run multipl objective with source node 1
    result = one_to_all(G,1)


    print("MOSP Solution")
    for x in result.values():
        print(str(x[-1].label_list) + ", costs: " + str(x[-1].costs))

    print("NextworkX solution")
    gen = nx.single_source_all_shortest_paths(G,source = 1,weight='length')
    for x in gen:
        print(x)

    print("Source is 1. Generated, half of arcs removed, single objective, alternate optimal")
    for u, v in complete_graph.edges:
        if random.random() > 0.5:
            G.remove_edge(u,v)

            #run multipl objective with source node 1
    result = one_to_all(G,1)


    print("MOSP solution")
    for x in result.values():
        print(str(x[-1].label_list) + ", costs: " + str(x[-1].costs))

if __name__ == "__main__":
    main()