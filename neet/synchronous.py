# Copyright 2017 ELIFE. All rights reserved.
# Use of this source code is governed by a MIT
# license that can be found in the LICENSE file.
import copy
import networkx as nx
import numpy as np
import pyinform as pi
from .statespace import StateSpace
from .interfaces import is_network, is_fixed_sized

def trajectory(net, state, timesteps=1, encode=False):
    """
    Generate the trajectory of length ``timesteps+1`` through the state-space,
    as determined by the network rule, beginning at ``state``.

    .. rubric:: Example:

    ::

        >>> from neet.automata import ECA
        >>> from neet.boolean.examples import s_pombe
        >>> gen = trajectory(ECA(30), [0, 1, 0], timesteps=3)
        >>> gen
        <generator object trajectory at 0x000002B692ED8BF8>
        >>> list(gen)
        [[0, 1, 0], [1, 1, 1], [0, 0, 0], [0, 0, 0]]
        >>> list(trajectory(ECA(30), [0, 1, 0], timesteps=3, encode=True))
        [2, 7, 0, 0]
        >>> gen = trajectory(s_pombe, [0, 0, 0, 0, 1, 0, 0, 0, 0], timesteps=3,
        ... encode=True)
        >>> list(gen)
        [16, 256, 78, 128]

    :param net: the network
    :param state: the network state
    :param timesteps: the number of steps in the trajectory
    :param encode: encode the states as integers
    :yields: the next state in the trajectory
    :raises TypeError: if net is not a network
    :raises ValueError: if ``timesteps < 1``
    """
    if not is_network(net):
        raise TypeError("net is not a network")
    if timesteps < 1:
        raise ValueError("number of steps must be positive, non-zero")

    state = copy.copy(state)
    if encode:
        if is_fixed_sized(net):
            state_space = net.state_space()
        else:
            state_space = net.state_space(len(state))

        yield state_space._unsafe_encode(state)

        net.update(state)
        yield state_space._unsafe_encode(state)

        for _ in range(1,timesteps):
            net._unsafe_update(state)
            yield state_space._unsafe_encode(state)
    else:
        yield copy.copy(state)

        net.update(state)
        yield copy.copy(state)

        for _ in range(1, timesteps):
            net._unsafe_update(state)
            yield copy.copy(state)

def transitions(net, size=None, encode=False):
    """
    Generate the one-step state transitions for a network over its state space.

    .. rubric:: Example:

    ::

        >>> from neet.automata import ECA
        >>> from neet.boolean.examples import s_pombe
        >>> gen = transitions(ECA(30), size=3)
        >>> gen
        <generator object transitions at 0x000002B691328BA0>
        >>> list(gen)
        [[0, 0, 0], [1, 1, 1], [1, 1, 1], [1, 0, 0], [1, 1, 1], [0, 0, 1],
        [0, 1, 0], [0, 0, 0]]
        >>> list(transitions(ECA(30), size=3, encode=True))
        [0, 7, 7, 1, 7, 4, 2, 0]
        >>> gen = transitions(s_pombe, encode=True)
        >>> len(list(gen))
        512

    :param net: the network
    :param size: the size of the network (``None`` if fixed sized)
    :param encode: encode the states as integers
    :yields: the one-state transitions
    :raises TypeError: if ``net`` is not a network
    :raises ValueError: if ``net`` is fixed sized and ``size`` is not ``None``
    :raises ValueError: if ``net`` is not fixed sized and ``size`` is ``None``
    """
    if not is_network(net):
        raise TypeError("net is not a network")

    if is_fixed_sized(net):
        if size is not None:
            raise ValueError("size must be None for fixed sized networks")
        state_space = net.state_space()
    else:
        if size is None:
            raise ValueError("size must not be None for variable sized networks")
        state_space = net.state_space(size)

    for state in state_space:
        net._unsafe_update(state)
        if encode:
            yield state_space._unsafe_encode(state)
        else:
            yield state

def transition_graph(net, size=None):
    """
    Construct the state transition graph for the network.

    .. rubric:: Example:

    ::

        >>> from neet.automata import ECA
        >>> from neet.boolean.examples import s_pombe
        >>> g = transition_graph(s_pombe)
        >>> g.number_of_nodes(), g.number_of_edges()
        (512, 512)
        >>> g = transition_graph(ECA(30), size=6)
        >>> g.number_of_nodes(), g.number_of_edges()
        (64, 64)

    :param net: the network (if already a networkx.DiGraph, does nothing and returns it)
    :param size: the size of the network (``None`` if fixed sized)
    :param encode: encode the states as integers
    :returns: a ``networkx.DiGraph`` of the network's transition graph
    :raises TypeError: if ``net`` is not a network
    :raises ValueError: if ``net`` is fixed sized and ``size`` is not ``None``
    :raises ValueError: if ``net`` is not fixed sized and ``size`` is ``None``
    """
    if is_network(net):
        edge_list = enumerate(transitions(net, size=size, encode=True))
        return nx.DiGraph(list(edge_list))
    elif isinstance(net, nx.DiGraph):
        if size is not None:
            raise ValueError("size must be None for transition graphs")
        return net
    else:
        raise TypeError("net must be a network or a networkx DiGraph")

def attractors(net, size=None):
    """
    Find the attractor states of a network. A generator of the attractors is
    returned with each attractor represented as a ``list`` of "encoded" states.

    .. rubric:: Example:

    ::

        >>> from neet.automata import ECA
        >>> from neet.boolean.examples import s_pombe
        >>> list(attractors(s_pombe))
        [[76], [4], [8], [12], [144, 110, 384], [68], [72], [132], [136],
        [140], [196], [200], [204]]
        >>> list(attractors(ECA(30), size=5))
        [[0], [14, 25, 7, 28, 19]]

    :param net: the network or the transition graph
    :param size: the size of the network (``None`` if fixed sized)
    :returns: a generator of attractors
    :raises TypeError: if ``net`` is not a network or a ``networkx.DiGraph``
    :raises ValueError: if ``net`` is fixed sized and ``size`` is not ``None``
    :raises ValueError: if ``net`` is a transition graph and ``size`` is not ``None``
    :raises ValueError: if ``net`` is not fixed sized and ``size`` is ``None``
    """
    if isinstance(net, nx.DiGraph):
        for attr in nx.simple_cycles(net):
            yield attr
    elif not is_network(net):
        raise TypeError("net must be a network or a networkx DiGraph")
    elif is_fixed_sized(net) and size is not None:
        raise ValueError("fixed sized networks require size is None")
    elif not is_fixed_sized(net) and size is None:
        raise ValueError("variable sized networks require a size")
    else:
        # Get the state transitions
        # (array of next state indexed by current state)
        trans = list(transitions(net, size=size, encode=True))
        # Create an array to store whether a given state has visited
        visited = np.zeros(len(trans), dtype=np.bool)
        # Create an array to store which attractor basin each state is in
        basins = np.zeros(len(trans), dtype=np.int)
        # Create a counter to keep track of how many basins have been visited
        basin_number = 1

        # Start at state 0
        initial_state = 0
        # While the initial state is a state of the system
        while initial_state < len(trans):
            # Create a stack to store the state so far visited
            state_stack = []
            # Create a array to store the states in the attractor cycle
            cycle = []
            # Create a flag to signify whether the current state is part of the cycle
            in_cycle = False
            # Set the current state to the initial state
            state = initial_state
            # Store the next state and terminus variables to the next state
            terminus = next_state = trans[state]
            # Set the visited flag of the current state
            visited[state] = True
            # While the next state hasn't been visited
            while not visited[next_state]:
                # Push the current state onto the stack
                state_stack.append(state)
                # Set the current state to the next state
                state = next_state
                # Update the terminus and next_state variables
                terminus = next_state = trans[state]
                # Update the visited flag for the current state
                visited[state] = True

            # If the next state hasn't been assigned a basin yet
            if basins[next_state] == 0:
                # Set the current basin to the basin number
                basin = basin_number
                # Add the current state to the attractor cycle
                cycle.append(state)
                # We're still in the cycle until the current state is equal to the terminus
                in_cycle = (terminus != state)
            else:
                # Set the current basin to the basin of next_state
                basin = basins[next_state]

            # Set the basin of the current state
            basins[state] = basin

            # While we still have states on the stack
            while len(state_stack) != 0:
                # Pop the current state off of the top of the stack
                state = state_stack.pop()
                # Set the basin of the current state
                basins[state] = basin
                # If we're still in the cycle
                if in_cycle:
                    # Add the current state to the attractor cycle
                    cycle.append(state)
                    # We're still in the cycle until the current state is equal to the terminus
                    in_cycle = (terminus != state)

            # Find the next unvisited initial state
            while initial_state < len(visited) and visited[initial_state]:
                initial_state += 1

            # Yield the cycle if we found one
            if len(cycle) != 0:
                yield cycle

def basins(net, size=None):
    """
    Find the attractor basins of a network. A generator of the attractor basins
    is returned with each basin represented as a ``networkx.DiGraph`` whose
    nodes are the "encoded" network states.

    .. rubric:: Example:

    ::

        >>> from neet.automata import ECA
        >>> from neet.boolean.examples import s_pombe
        >>> b = basins(s_pombe)
        >>> [len(basin) for basin in b]
        [378, 2, 2, 2, 104, 6, 6, 2, 2, 2, 2, 2, 2]
        >>> b = basins(ECA(30), size=5)
        >>> [len(basin) for basin in b]
        [2, 30]

    :param net: the network or landscape transition_graph
    :param size: the size of the network (``None`` if fixed sized)
    :returns: generator of basin subgraphs
    :raises TypeError: if ``net`` is not a network or a ``networkx.DiGraph``
    :raises ValueError: if ``net`` is fixed sized and ``size`` is not ``None``
    :raises ValueError: if ``net`` is a transition graph and ``size`` is not ``None``
    :raises ValueError: if ``net`` is not fixed sized and ``size`` is ``None``
    """
    graph = transition_graph(net, size=size)
    return nx.weakly_connected_component_subgraphs(graph)

def basin_entropy(net, size=None, base=2):
    """
    Calculate the basin entropy.

    Reference:
    P. Krawitz and I. Shmulevich, ``Basin Entropy in Boolean Network Ensembles.''
    Phys. Rev. Lett. 98, 158701 (2007).  http://dx.doi.org/10.1103/PhysRevLett.98.158701

    .. rubric:: Example:

    ::

        >>> from neet.automata import ECA
        >>> from neet.boolean.examples import s_pombe
        >>> basin_entropy(s_pombe)
        1.2218888338849747
        >>> basin_entropy(s_pombe, base=10)
        0.367825190366261
        >>> basin_entropy(ECA(30), size=5)
        0.3372900666170139

    :param net: the network or landscape transition_graph
    :param size: the size of the network (``None`` if fixed sized)
    :param base: base of logarithm used to calculate entropy (2 for bits)
    :returns: value of basin entropy
    :raises TypeError: if ``net`` is not a network or a ``networkx.DiGraph``
    :raises ValueError: if ``net`` is fixed sized and ``size`` is not ``None``
    :raises ValueError: if ``net`` is a transition graph and ``size`` is not ``None``
    :raises ValueError: if ``net`` is not fixed sized and ``size`` is ``None``
    """
    sizes = [ len(basin) for basin in basins(net, size=size) ]
    d = pi.Dist(sizes)
    return pi.shannon.entropy(d, b=base)

def timeseries(net, timesteps, size=None):
    """
    Return the timeseries for the network. The result will be a :math:`3D` array
    with shape :math:`N \\times V \\times t` where :math:`N` is the number of
    nodes in the network, :math:`V` is the volume of the state space (total
    number of network states), and :math:`t` is ``timesteps + 1``.

    ::

        >>> net = WTNetwork([[1,-1],[1,0]])
        >>> timeseries(net, 5)
        array([[[ 0.,  0.,  0.,  0.,  0.,  0.],
                [ 1.,  1.,  1.,  1.,  1.,  1.],
                [ 0.,  0.,  0.,  0.,  0.,  0.],
                [ 1.,  1.,  1.,  1.,  1.,  1.]],

            [[ 0.,  0.,  0.,  0.,  0.,  0.],
                [ 0.,  1.,  1.,  1.,  1.,  1.],
                [ 1.,  1.,  1.,  1.,  1.,  1.],
                [ 1.,  1.,  1.,  1.,  1.,  1.]]])

    :param net: the network
    :param timesteps: the number of timesteps in the timeseries
    :param size: the size of the network (``None`` if fixed sized)
    :return: a numpy array
    :raises TypeError: if ``net`` is not a network
    :raises ValueError: if ``net`` is fixed sized and ``size`` is not ``None``
    :raises ValueError: if ``net`` is not fixed sized and ``size`` is ``None``
    :raises ValueError: if ``timesteps < 1``
    """
    if not is_network(net):
        raise TypeError("net must be a NEET network")
    if not is_fixed_sized(net) and size is None:
        raise ValueError("network is not fixed sized; must provide a size")
    elif is_fixed_sized(net) and size is not None:
        raise ValueError("cannot provide a size with a fixed sized network")
    if timesteps < 1:
        raise ValueError("time series must have at least one timestep")

    if size is None:
        state_space = net.state_space()
    else:
        state_space = net.state_space(size)

    shape = (state_space.ndim, state_space.volume, timesteps+1)
    series = np.empty(shape, dtype=np.int)

    trans = list(transitions(net, size=size, encode=False))
    encoded_trans = [state_space._unsafe_encode(state) for state in trans]

    for (index, init) in enumerate(state_space):
        k = index
        series[:, index, 0] = init[:]
        for time in range(1, timesteps + 1):
            series[:, index, time] = trans[k][:]
            k = encoded_trans[k]

    return series

class Landscape(StateSpace):
    """
    The ``Landscape`` class represents the structure and topology of the
    "landscape" of state transitions. That is, it is the state space
    together with information about state transitions and the topology of
    the state transition graph.
    """
    def __init__(self, net, size=None):
        """
        Construct the landscape for a network.

        ::

            >>> Landscape(s_pombe)
            <neet.synchronous.Landscape object at 0x101c74810>
            >>> Landscape(ECA(30), size=5)
            <neet.synchronous.Landscape object at 0x10415b6d0>

        :param net: the network
        :param size: the size of the network (``None`` if fixed sized)
        :raises TypeError: if ``net`` is not a network
        :raises ValueError: if ``net`` is fixed sized and ``size`` is not ``None``
        :raises ValueError: if ``net`` is not fixed sized and ``size`` is ``None``
        """

        if not is_network(net):
            raise TypeError("net is not a network")
        elif is_fixed_sized(net):
            if size is not None:
                raise ValueError("size must be None for fixed sized networks")
            state_space = net.state_space()
        else:
            if size is None:
                raise ValueError("size must not be None for variable sized networks")
            state_space = net.state_space(size)

        if state_space.is_uniform:
            super(Landscape, self).__init__(state_space.ndim, state_space.base)
        else:
            super(Landscape, self).__init__(state_space.bases)

        self.__net = net

        self.__expounded = False

        self.__setup()

    @property
    def network(self):
        """
        Get the landscape's dynamical network.

        :return: the dynamical network
        """
        return self.__net

    @property
    def size(self):
        """
        Get the size of the dynamical network, i.e.. number of nodes.

        :return: the size of the dynamical network
        """
        return self.ndim

    @property
    def transitions(self):
        """
        Get the transitions array of the landscape. That is, return the
        array of state whose indices are initial states and values are
        the subsequent state.

        :return: the state transitions array
        """
        return self.__transitions

    @property
    def attractors(self):
        """
        Get the attractor cycles of the landscape.

        :return: an array of cycles, each an array
        """
        if not self.__expounded:
            self.__expound()
        return self.__attractors

    @property
    def basins(self):
        """
        """
        if not self.__expounded:
            self.__expound()
        return self.__basins

    def __setup(self):
        """
        Compute all of the relavent computable values for the network:
            * transitions
        """
        update = self.__net._unsafe_update
        encode = self._unsafe_encode

        transitions = np.empty(self.volume, dtype=np.int)
        for i, state in enumerate(self):
            transitions[i] = encode(update(state))

        self.__transitions = transitions

    def __expound(self):
        # Get the state transitions
        trans = self.__transitions
        # Create an array to store whether a given state has visited
        visited = np.zeros(self.volume, dtype=np.bool)
        # Create an array to store which attractor basin each state is in
        basins = np.full(self.volume, -1, dtype=np.int)
        # Create a counter to keep track of how many basins have been visited
        basin_number = 0
        # Create a list of attractor cycles
        attractors = []

        # Start at state 0
        initial_state = 0
        # While the initial state is a state of the system
        while initial_state < len(trans):
            # Create a stack to store the state so far visited
            state_stack = []
            # Create a array to store the states in the attractor cycle
            cycle = []
            # Create a flag to signify whether the current state is part of the cycle
            in_cycle = False
            # Set the current state to the initial state
            state = initial_state
            # Store the next state and terminus variables to the next state
            terminus = next_state = trans[state]
            # Set the visited flag of the current state
            visited[state] = True
            # While the next state hasn't been visited
            while not visited[next_state]:
                # Push the current state onto the stack
                state_stack.append(state)
                # Set the current state to the next state
                state = next_state
                # Update the terminus and next_state variables
                terminus = next_state = trans[state]
                # Update the visited flag for the current state
                visited[state] = True

            # If the next state hasn't been assigned a basin yet
            if basins[next_state] == -1:
                # Set the current basin to the basin number
                basin = basin_number
                # Increment the basin number
                basin_number += 1
                # Add the current state to the attractor cycle
                cycle.append(state)
                # We're still in the cycle until the current state is equal to the terminus
                in_cycle = (terminus != state)
            else:
                # Set the current basin to the basin of next_state
                basin = basins[next_state]

            # Set the basin of the current state
            basins[state] = basin

            # While we still have states on the stack
            while len(state_stack) != 0:
                # Pop the current state off of the top of the stack
                state = state_stack.pop()
                # Set the basin of the current state
                basins[state] = basin
                # If we're still in the cycle
                if in_cycle:
                    # Add the current state to the attractor cycle
                    cycle.append(state)
                    # We're still in the cycle until the current state is equal to the terminus
                    in_cycle = (terminus != state)

            # Find the next unvisited initial state
            while initial_state < len(visited) and visited[initial_state]:
                initial_state += 1

            # Yield the cycle if we found one
            if len(cycle) != 0:
                attractors.append(np.asarray(cycle, dtype=np.int))

        self.__basins = basins
        self.__attractors = np.asarray(attractors)
        self.__expounded = True

    def trajectory(self, init, timesteps=None, encode=None):
        decoded = isinstance(init, list) or isinstance(init, np.ndarray)

        if decoded:
            if init == []:
                raise ValueError("initial state cannot be empty")
            elif encode is None:
                encode = False
            init = self.encode(init)
        elif encode is None:
            encode = True

        trans = self.__transitions
        if timesteps is not None:
            if timesteps < 1:
                raise ValueError("number of steps must be positive, non-zero")

            path = [init] * (timesteps + 1)
            for i in range(1, len(path)):
                path[i] = trans[path[i-1]]
        else:
            path = [init]
            state = trans[init]
            while state not in path:
                path.append(state)
                state = trans[state]

        if not encode:
            decode = self.decode
            path = [ decode(state) for state in path ]

        return path
