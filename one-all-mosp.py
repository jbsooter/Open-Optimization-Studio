import heapq
import queue

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
        for i in range(0, len(c)):
            if c[i] <= cc[i]:
                return True
            elif c[i] == cc[i]:
                continue
            else:
                return False
        return False
    def dominance_check(self, other):
        cc = self.costs
        c = other.costs

        counter = 0

        for i in range(0,len(c)):
            if c[i] <= cc[i]:
                if c[i] < cc[i]:
                    counter += 1
            else:
                return False

        if counter >= 1:
            return True
        else:
            return False
        #still need to check non equivalence?
    def __str__(self):
            return str(self.node) + "    pred: " + str(self.predecessor) + "    costs:  " + str(self.costs)


def nextCandidateLabel(v,lastProcessedLabel,sigma, L, G):
    l_v = Label(v, [infinity, infinity],None)

    for u in sigma:
        for k in range(lastProcessedLabel[(u,v)],len(L[u])):
                print(len(L[u]))
                l_u = L[u][k]
                l_new = Label(v, np.sum([l_u.costs , [G.edges[(u,v)]["elevation"], G.edges[(u,v)]["length"]]], axis=0), l_u.node)
                lastProcessedLabel[(u,v)] = k
                #start back at line 9
                if l_v.dominance_check(l_new):
                    print(l_new.__lt__(l_v))
                    if l_new.__lt__(l_v):
                        l_v = l_new
                        break
    if l_v.costs[0] != infinity:
        return None

    return l_v

def propogate(l_v, w, H,L, G):
    l_new = Label(w,np.sum([l_v.costs, [G.edges[(l_v.node,w)]["elevation"], G.edges[(l_v.node,w)]["length"]]], axis=0), l_v)
    #fix to n obj calc
    dom_check = True
    for l_w_local in L[w]:
        if l_w_local.dominance_check(l_new) is False:
            dom_check = False

    if dom_check:
        if (w in H) is False:
                heapq.heappush(H,l_new)

        elif l_new.__lt__(H[w]):
            H = [label for label in H if label.node != l_new.node]
            heapq.heapify(H)
            heapq.heappush(H,l_new)


def one_to_all(G,source):
    H = []
    heapq.heapify(H)

    L = {}

    for v,data in G.nodes.data():

        L[v] = [Label(v,[infinity, infinity],-1)]

    last_processed_label = {}
    for a in G.edges:
        last_processed_label[a] = 0

    heapq.heappush(H, Label(source,[0,0],None))

    #line 7
    while len(H) > 0:
        l_v_star = heapq.heappop(H)
        print(l_v_star)
        L[l_v_star.node].append(l_v_star)
        #heapq.heappush(H,l_v_star)

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
            propogate(l_v_star,w,H,L,G)

    return L




def main():

    G = nx.DiGraph()
    #pos = {1: (0, 0), 2: (-1, 0.3), 3: (2, 0.17), 4: (4, 0.255), 5: (5, 0.03)}
    G.add_edge(1,2,length=1,elevation=10000000)
    G.add_edge(2,1,length=1,elevation=1)
    G.add_edge(3,2,length=1,elevation=1)
    G.add_edge(2,3,length=1,elevation=1)
    G.add_edge(1,3,length=1,elevation=1)
    G.add_edge(3,1,length=1,elevation=1)
    result = one_to_all(G,2)

    for i in result.values():
       for ii in i:
           if ii.predecessor!= -1:
                print(ii)



if __name__ == "__main__":
    main()