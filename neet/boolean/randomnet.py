"""
Functions that generate random networks from a given network.
"""
# Copyright 2017 ELIFE. All rights reserved.
# Use of this source code is governed by a MIT
# license that can be found in the LICENSE file.

import random
import numpy as np
from .logicnetwork import LogicNetwork
from neet.sensitivity import canalizing_nodes

def random_logic(logic_net, p=0.5, connections='fixed-structure', fix_external=False,
                 make_irreducible=False, fix_canalizing=False):
    """
    Return a `LogicNetwork` from an input `LogicNetwork` with a random logic table.

    `connections` decides how a node in the random network is connected from
    other nodes. With the `'fixed-structure'` option, the random network has the same
    connections as the input network. With the `'fixed-in-degree'` option, the number
    of connections to a node is the same as the input network, but the connections
    are randomly selected. With the 'fixed-mean-degree' option, the total number of
    edges is conserved, but edges are placed randomly between nodes.  With the 
    `'free'` option, only the number of nodes is conserved, with the number of 
    connections to a node chosen uniformly between 1 and the total number of nodes.

    `p` is the probability of a state of the connected nodes being present in
    the activation table. It is also equavolent to the probability of any node
    being activated. If `p` is a single number, it applies to all nodes. Otherwise
    `p` must be a sequence of numbers that match in size with the input network.

    :param logic_net: a :class:LogicNetwork
    :param p: probability that a state is present in the activation table
    :type p: number or sequence
    :param connections: 'fixed-structure', 'fixed-in-degree', 'fixed-mean-degree', or 'free'
    :type connections: str
    :returns: a random :class:LogicNetwork
    """
    if not isinstance(logic_net, LogicNetwork):
        raise ValueError('object must be a LogicNetwork')

    if isinstance(p, (int, float)):
        ps = [p] * logic_net.size
    elif len(p) != logic_net.size:
        raise ValueError("p's length must match with network size")
    else:
        ps = p

    random_styles = {'fixed-structure': _random_logic_fixed_connections,
                     'fixed-in-degree': _random_logic_shuffled_connections,
                     'fixed-mean-degree': _random_logic_fixed_num_edges,
                     'free': _random_logic_free_connections}

    try:
        return random_styles[connections](logic_net, ps, fix_external,
                                          make_irreducible, fix_canalizing)
    except KeyError:
        raise ValueError(
            "connections must be 'fixed', 'fixed-in-degree', 'fixed-mean-degree', or 'free'")


def random_binary_states(k, p):
    """
    Return a set of binary states. Each state has length `k` and the number of
    states is `k * p` (or chosen to produce `k * p` on average if `n * p` is not
    an integer).
    """
    integer, decimal = divmod(2**k * p, 1)
    num_states = int(integer + np.random.choice(2, p=[1 - decimal, decimal]))
    state_idxs = np.random.choice(2 ** k, num_states, replace=False)

    return set('{0:0{1}b}'.format(idx, k) for idx in state_idxs)

def random_canalizing_binary_states(k, p):
    """
    Return a set of binary states that, when considered as a set of 
    activating conditions, represents a canalizing function.
    
    Designed to sample each possible canalized function with equal
    probability.  (Note that this depends on `_prob_canalized_value`,
    a calculation that still needs to be checked for accuracy
    as of 3.27.2018.)
    
    Each state has length `k` and the number of states is set in the
    same way as `random_binary_states`.
    """
    integer, decimal = divmod(2**k * p, 1)
    num_states = int(integer + np.random.choice(2, p=[1 - decimal, decimal]))
    
    # calculate values specifying which input is canalizing and how
    canalizing_input = np.random.choice(k)
    canalizing_value = np.random.choice(2)
    pc = _prob_canalized_value(k,p)
    canalized_value = np.random.choice(2, p=[1. - pc, pc])
    
    print "canalizing_input =",canalizing_input
    print "canalizing_value =",canalizing_value
    print "canalized_value  =",canalized_value

    fixed_states = _all_states_with_one_node_fixed(k,canalizing_input,canalizing_value)
    other_states = np.lib.arraysetops.setxor1d(np.arange(2 ** k),
                                               fixed_states,
                                               assume_unique=True)
    if canalized_value == 1:
        # include all fixed_states as activating conditions
        state_idxs = np.random.choice(other_states,
                                      num_states - len(fixed_states),
                                      replace=False)
        state_idxs = np.concatenate((state_idxs,np.array(fixed_states)))
    elif canalized_value == 0:
        # include none of fixed_states as activating conditions
        state_idxs = np.random.choice(other_states,num_states,replace=False)

    return set('{0:0{1}b}'.format(idx, k) for idx in state_idxs)


def _prob_canalized_value(k, p):
    """
    Return the probability that a boolean function's canalized value
    is 1, given that it is canalizing.
    
    3.27.2018 NEEDS TO BE CHECKED
    """
    if p == 0.:
        return 0.
    else:
        return 1. / ( 1. + ((1.-p)/p)**(2.**(k-1)) )

def _all_states_with_one_node_fixed(k,fixed_index,fixed_value,max_k=20):
    """
    (Should have length 2**(k-1).)
    """
    if k > max_k:
        raise Exception("k > max_k")
    # there may be a more efficient way to do this...
    return [ idx for idx in range(2**k) \
             if '{0:0{1}b}'.format(idx, k)[fixed_index] == str(fixed_value) ]

def _external_nodes(logic_net):
    externals = set()
    for idx, row in enumerate(logic_net.table):
        if row[0] == (idx, ) and row[1] == {'1'}:
            externals.add(idx)
    return externals

# stolen from grn-survey.generate_variants


def _fake_connections(net):
    fakes = []
    for idx in range(net.size):
        for neighbor_in in net.neighbors_in(idx):
            if not net.is_dependent(idx, neighbor_in):
                fakes.append((idx, neighbor_in))
    return fakes


def _logic_table_row_is_irreducible(row, i, size):
    table = [((), set()) for j in range(size)]
    table[i] = row
    net = LogicNetwork(table)
    return len(_fake_connections(net)) == 0

def _logic_table_row_is_canalizing(row, i, size):
    table = [((), set()) for j in range(size)]
    table[i] = row
    net = LogicNetwork(table)
    return i in canalizing_nodes(net)

def _random_logic_fixed_connections(logic_net, ps, fix_external=False,
                                    make_irreducible=False,fix_canalizing=False,
                                    give_up_number=1000):
    """
    Return a `LogicNetwork` from an input `LogicNetwork` with a random logic table.

    Connections in the returned network are the same as those of the input.

    :param logic_net: a :class:LogicNetwork
    :param ps: probability that a state is present in the activation table
    :returns: a random :class:LogicNetwork
    """
    if not isinstance(logic_net, LogicNetwork):
        raise ValueError('object must be a LogicNetwork')

    externals = _external_nodes(logic_net)

    new_table = []
    for i, row in enumerate(logic_net.table):
        indices = row[0]
        if i in externals:
            conditions = row[1]
        else:
            if fix_canalizing:
                original_canalizing = _logic_table_row_is_canalizing(row,i,logic_net.size)
            keep_trying = True
            number_tried = 0
            while keep_trying and (number_tried < give_up_number):
                conditions = random_binary_states(len(indices), ps[i])

                number_tried += 1
                keep_trying = False
                if make_irreducible:
                    node_irreducible = _logic_table_row_is_irreducible(
                        (indices, conditions), i, logic_net.size)
                    keep_trying = not node_irreducible
                if (not keep_trying) and fix_canalizing:
                    node_canalizing = _logic_table_row_is_canalizing(
                        (indices, conditions), i, logic_net.size)
                    keep_trying = not (node_canalizing == original_canalizing)
            if number_tried >= give_up_number:
                raise Exception("No function out of "+str(give_up_number)+" tried satisfied constraints")

        new_table.append((indices, conditions))

    return LogicNetwork(new_table, logic_net.names)


def _random_logic_shuffled_connections(logic_net, ps, fix_external=False,
                                       make_irreducible=False,
                                       fix_canalizing=False,
                                       give_up_number=1000):
    """
    Return a `LogicNetwork` from an input `LogicNetwork` with a random logic table.

    The number of connections to a node is the same as the input network, but
    the connections are randomly selected.

    :param logic_net: a :class:LogicNetwork
    :param p: probability that a state is present in the activation table
    :returns: a random :class:LogicNetwork
    """
    if not isinstance(logic_net, LogicNetwork):
        raise ValueError('object must be a LogicNetwork')

    externals = _external_nodes(logic_net) if fix_external else set()

    new_table = []
    for i, row in enumerate(logic_net.table):
        if i in externals:
            indices, conditions = row
        else:
            if fix_canalizing:
                original_canalizing = _logic_table_row_is_canalizing(row,i,logic_net.size)
            keep_trying = True
            number_tried = 0
            while keep_trying and (number_tried < give_up_number):
                n_indices = len(row[0])
                indices = tuple(sorted(random.sample(range(logic_net.size), k=n_indices)))

                conditions = random_binary_states(n_indices, ps[i])

                number_tried += 1
                keep_trying = False
                if make_irreducible:
                    node_irreducible = _logic_table_row_is_irreducible(
                        (indices, conditions), i, logic_net.size)
                    keep_trying = not node_irreducible
                if (not keep_trying) and fix_canalizing:
                    node_canalizing = _logic_table_row_is_canalizing(
                        (indices, conditions), i, logic_net.size)
                    keep_trying = not (node_canalizing == original_canalizing)
            if number_tried >= give_up_number:
                raise Exception("No function out of "+str(give_up_number)+" tried satisfied constraints")

        new_table.append((indices, conditions))

    return LogicNetwork(new_table, logic_net.names)


def _random_logic_free_connections(logic_net, ps):
    """
    Return a `LogicNetwork` from an input `LogicNetwork` with a random logic table.

    All possible connections within the network are considered in the random process.

    :param logic_net: a :class:LogicNetwork
    :param p: probability that a state is present in the activation table
    :returns: a random :class:LogicNetwork
    """
    if not isinstance(logic_net, LogicNetwork):
        raise ValueError('object must be a LogicNetwork')

    new_table = []
    for i in range(logic_net.size):
        n_indices = random.randint(1, logic_net.size)
        indices = tuple(sorted(random.sample(range(logic_net.size), k=n_indices)))

        conditions = random_binary_states(n_indices, ps[i])

        new_table.append((indices, conditions))

    return LogicNetwork(new_table, logic_net.names)


def _random_logic_fixed_num_edges(logic_net, ps, fix_external=False,
                                  make_irreducible=False,
                                  fix_canalizing=False,
                                  give_up_number=1000):
    """
    Returns new network that corresponds to adding a fixed number of
    edges between random nodes, with random corresponding boolean rules.
    """
    if fix_canalizing:
        raise NotImplementedError("fix_canalizing=True not yet implemented")

    num_edges = sum(len(logic_net.neighbors_in(i)) for i in range(logic_net.size))

    externals = _external_nodes(logic_net) if fix_external else set()

    num_edges -= len(externals)

    internals = [idx for idx in range(logic_net.size) if idx not in externals]
    num_internal_connections = np.zeros(len(internals))

    sample = np.random.choice([i // logic_net.size for i in range(len(internals) * logic_net.size)],
                              num_edges - len(internals), replace=False)
    idxs, counts = np.unique(sample, return_counts=True)

    num_internal_connections[idxs] = counts
    num_internal_connections += 1

    new_table = [()] * logic_net.size
    for internal, num in zip(internals, num_internal_connections):
        keep_trying = True
        number_tried = 0
        while keep_trying and (number_tried < give_up_number):
            in_indices = tuple(np.random.choice(logic_net.size, int(num), replace=False))
            conditions = random_binary_states(len(in_indices), ps[internal])
            new_table[internal] = (in_indices, conditions)

            number_tried += 1
            if make_irreducible:
                node_irreducible = _logic_table_row_is_irreducible(
                    (in_indices, conditions), internal, logic_net.size)
                keep_trying = not node_irreducible
            else:
                keep_trying = False
        if number_tried >= give_up_number:
                raise Exception("No function out of "+str(give_up_number)+" tried satisfied constraints")

    for external in externals:
        new_table[external] = logic_net.table[external]

    return LogicNetwork(new_table, logic_net.names)


# def _degrees(net):
#     """
#     Return the list of node in-degrees for the network.
#     """
#     return [len(t[0]) for t in net.table]


# def _random_partition(n, s, m=np.inf):
#     """
#     Choose n random integers that sum to s, with the maximum value
#     of any element of the list limited to m.
#     """
#     if s > n * m:
#         raise ValueError("Can't have s > n*m")

#     # see, e.g., https://stackoverflow.com/questions/5622608/choosing-n-numbers-with-fixed-sum
#     partition = [0] + list(np.random.randint(0, s + 1, n - 1)) + [s]
#     partition = np.sort(partition)
#     integers = partition[1:] - partition[:-1]

#     # redistribute any values above the max
#     # (there's probably a better way to do this!)
#     while max(integers) > m:
#         maxedIndices = (integers >= m)
#         nonMaxedIndices = (integers < m)
#         numToRedistribute = np.sum(integers[maxedIndices] - m)
#         redistributed = _random_partition(
#             sum(nonMaxedIndices), numToRedistribute)
#         integers[maxedIndices] = m
#         integers[nonMaxedIndices] += redistributed

#     return integers
