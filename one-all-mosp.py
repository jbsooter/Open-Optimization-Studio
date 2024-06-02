import heapq
import networkx as nx
import numpy as np

infinity = np.Infinity

class Label:
    def __init__(self, node, costs,predecessor):
        self.node = node
        self.costs = costs
        self.predecessor = predecessor
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
            return  str(self.node) +   "," + str(self.costs) + " <- " + str(self.predecessor)

def nextCandidateLabel(v,lastProcessedLabel,sigma, L, G):
    l_v = Label(v, [infinity, infinity],None)

    for u in sigma:
        for k in range(lastProcessedLabel[(u,v)],len(L[u])):
                l_u = L[u][k]
                l_new = Label(v, [l_u.costs[0] + G.edges[(u,v)]["elevation"],l_u.costs[1]+ G.edges[(u,v)]["length"]], l_u)

                lastProcessedLabel[(u,v)] = k

                if L[v][-1].dominance_check(l_new) is False:
                    if l_new.__lt__(l_v):
                        l_v = l_new
                        L[v].append(l_v)
                        break

    if l_v.costs[0] is not infinity:
        return None
    return l_v

def propogate(l_v, w, H,L, G):
    l_new = Label(w,[l_v.costs[0] +  G.edges[(l_v.node,w)]["elevation"], l_v.costs[1] + G.edges[(l_v.node,w)]["length"]], l_v)
    #fix to n obj calc
    dom_check = True

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
    while len(H) > 0:
        l_v_star = heapq.heappop(H)
        L[l_v_star.node].append(l_v_star)

        u = []
        for uu, v in G.in_edges(l_v_star.node):
            u.append(uu)

        l_v_new = nextCandidateLabel(l_v_star.node,last_processed_label,u,L, G)
        if l_v_new is not None:
            heapq.heappush(H,l_v_new)


        sigma_plus = []
        for u, v in G.out_edges(l_v_star.node):
            sigma_plus.append(v)

        for w in sigma_plus:
            H = propogate(l_v_star,w,H,L,G)
            heapq.heapify(H)

    return L

def main():
    G = nx.DiGraph()

    print("Source 1. Case where 1-2-3 is still preferred even though distance is large, because elevation is an order of maginude larger. ")
    G.add_edge(1,2,length=1,elevation=1)
    G.add_edge(2,1,length=1,elevation=1)
    G.add_edge(1,3,length=1,elevation=1000000)
    G.add_edge(3,1,length=1,elevation=1)
    G.add_edge(2,3,length=100000,elevation=100000)
    G.add_edge(3,2,length=1,elevation=1)

    #run multipl objective with source node 1
    result = one_to_all(G,1)


    for x in result.values():
        #print(x[-1])
        for xx in x:
            print(xx)





if __name__ == "__main__":
    main()