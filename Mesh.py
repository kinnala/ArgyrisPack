#! /usr/bin/env python
import numpy as np
import pdb

class Mesh(object):
    """
    Representation of a finite element mesh. Essentially a struct.

    Required Arguements and Properties
    ----------------------------------

    * elements : integer numpy array of the global node numbers of each
      element.

    * nodes    : double precision numpy array of global node coordinates.

    * node_collections : a dictionary correlating names with node numbers.
    """
    def __init__(self, elements, nodes, node_collections):
        self.elements = elements
        self.nodes = nodes
        self.node_collections = node_collections

class ArgyrisMesh(object):
    """
    Class to build an Argyris mesh from a quadratic mesh. Can handle a mesh
    with multiple boundary conditions.

    The algorithm is as follows:

    1. Treat the current midpoint nodes as the normal derivative basis
    functions.
    2. For each corner of each element, see if nodes have been stacked on
    previously. If not, use the class-scope variable _new_index to add five
    new nodes at the current corner. Update the appropriate node container.

    Required Arguements
    -------------------
    * node_collections : list of the ArgyrisNodeCollection objects formed
      from the quadratic mesh.

    * original_elements : integer numpy array of the global node numbers of
      each element in the quadratic mesh.

    * original_nodes : 2xN numpy array of node coordinates on the quadratic
      mesh.

    Properties
    ----------
    * elements : a numpy array listing the node numbers of every element.

    * node_collections : a list of ArgyrisNodeCollection objects.

    * nodes : a numpy array of node coordinates.

    Methods
    -------
    * save_QGE_files : save the mesh in a format compatible to the existing QGE
    code.
    """
    def __init__(self, node_collections, original_elements, original_nodes):
        self.node_collections = node_collections
        self.elements = np.zeros((original_elements.shape[0], 21), dtype=np.int)
        self.elements[:,0:6] = original_elements

        # solve a lot of orientation problems later by ensuring that the corner
        # nodes are in sorted order.
        for element in self.elements:
            self._fix_element_order(element[0:6])

        # also convert the normal derivative basis functions to be in the
        # correct order (albeit at this point they are still in the wrong
        # column position in the array)
        temp = self.elements[:,4].copy()
        self.elements[:,4] = self.elements[:,5]
        self.elements[:,5] = temp

        # stack new nodes.
        n = original_elements.max() + 1

        self.stacked_nodes = \
            {node_number : np.array(range(n + 5*count, n + 5*count + 5))
             for count, node_number in enumerate(np.unique(self.elements[:,0:3]))}

        for element in self.elements:
                element[6:11]  = self.stacked_nodes[element[0]]
                element[11:16] = self.stacked_nodes[element[1]]
                element[16:21] = self.stacked_nodes[element[2]]

        self.edges_by_midpoint = \
            {midpoint : (element_number + 1, k) for k in range(1,4) for
             element_number, midpoint in enumerate(self.elements[:,2+k])}

        # add new nodal coordinates.
        self.nodes = np.zeros((self.elements.max(), 2))
        self.nodes[0:len(original_nodes),:] = original_nodes
        for stacked_node, new_nodes in self.stacked_nodes.iteritems():
            self.nodes[new_nodes - 1] = original_nodes[stacked_node - 1]

        # update the collections based on this information.
        for collection in self.node_collections:
            collection.update(self)
    def _fix_element_order(self, element):
        """
        Ensure that the corners of the input quadratic element are in increasing
        order. For example, convert
        1 3 2 4 6 5
        to
        1 2 3 5 6 4
        """
        if element[0] > element[1]:
            element[0], element[1] = element[1], element[0]
            element[4], element[5] = element[5], element[4]
        if element[1] > element[2]:
            element[2], element[1] = element[1], element[2]
            element[3], element[5] = element[5], element[3]
        if element[0] > element[2]:
            element[2], element[0] = element[0], element[2]
            element[3], element[4] = element[4], element[3]
        if element[0] > element[1]:
            element[0], element[1] = element[1], element[0]
            element[4], element[5] = element[5], element[4]

    def save_QGE_files(self):
        """
        Save the following data for compatibility with the QGE code:

            nodes.txt    : all nodal coordinates
            elements.txt : the element array for Argyris
            unodes.txt   : nodes corresponding to function values

        and for each border in edge_collections with key NAME, as well as the
        interior nodes:

            NAME_dx.txt       : nodes approximating x-derivatives
            NAME_dy.txt       : nodes approximating y-derivatives
            NAME_normal.txt   : nodes approximating normal derivatives
            NAME_function.txt : nodes approximating function values
            NAME_all.txt      : all nodes in the collection.
        """
        # save node indicies containing function values.
        u_nodes = np.unique(self.elements[:,0:3])

        # fix the numbering on the argyris.elements to match QGE code.
        elements = self.elements.copy()
        normal_derivatives1 = elements[:,3].copy()
        normal_derivatives2 = elements[:,4].copy()
        normal_derivatives3 = elements[:,5].copy()

        first_nodes  = elements[:,6:11].copy()
        second_nodes = elements[:,11:16].copy()
        third_nodes  = elements[:,16:21].copy()

        elements[:,18]    = normal_derivatives1
        elements[:,19]    = normal_derivatives2
        elements[:,20]    = normal_derivatives3

        elements[:,3:5]   = first_nodes[:,0:2]
        elements[:,9:12]  = first_nodes[:,2:5]

        elements[:,5:7]   = second_nodes[:,0:2]
        elements[:,12:15] = second_nodes[:,2:5]

        elements[:,7:9]   = third_nodes[:,0:2]
        elements[:,15:18] = third_nodes[:,2:5]

        np.savetxt('nodes.txt', self.nodes)
        np.savetxt('elements.txt', elements, fmt="%d")
        np.savetxt('unodes.txt', u_nodes, fmt="%d")

        # save the information stored in the node collections as well.
        for collection in self.node_collections:
            collection.write_to_files()

class ArgyrisNodeCollection(object):
    """
    Contains information about a group of nodes in an Argyris Mesh and any
    relevant edge data.

    Required Arguements
    -------------------
    * function_values : set of basis function numbers that approximate function
      values on the Argyris mesh.
    * normal_derivatives : set of the node numbers corresponding to normal
      derivative basis functions.
    * edges : set of tuples corresponding to (endpoint, endpoint, midpoint)

    Optional Arguements
    -------------------
    * name : prefix on the output files. Defaults to 'inner'.
    """
    def __init__(self, function_values, normal_derivatives,
                 edges, name = 'inner'):
        self.function_values = function_values
        self.normal_derivatives = normal_derivatives
        self._edges = edges

        self.name = name

        self.stacked_nodes = dict()
        self._edge_elements = list()

    def update(self, mesh):
        """
        """
        self.stacked_nodes = {node : mesh.stacked_nodes[node] for node in
                              self.function_values}
        self._edge_elements = [mesh.edges_by_midpoint[edge[-1]] + edge
                               for edge in self._edges]

    def write_to_files(self):
        """
        Save the data to text files; place all node numbers in the collection
        in one file and all information on edge elements in another.
        """
        if self._edge_elements: # don't save if there are no edge elements.
            np.savetxt(self.name + '_edge_elements.txt',
                       np.asarray(self._edge_elements, dtype=np.int), "%d")

        np.savetxt(self.name + '_all.txt',
                   np.unique(np.hstack(self.stacked_nodes.values() +
                                       self.stacked_nodes.keys() +
                                       list(self.normal_derivatives))), "%d")

    def __str__(self):
        return ("Node collection name: " + self.name + "\n" +
        "function values:\n" + str(self.function_values) + "\n" +
        "normal derivatives:\n" + str(self.normal_derivatives) + "\n" +
        "edge elements:\n" + str(self._edge_elements))