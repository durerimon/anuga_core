"""Class pmesh2domain - Converting .tsh files to doamains


   Copyright 2004
   Ole Nielsen, Stephen Roberts, Duncan Gray, Christopher Zoppou
   Geoscience Australia
"""

import sys



def pmesh_instance_to_domain_instance(mesh,
                                      DomainClass):
    """
    Convert a pmesh instance/object into a domain instance.

    Use pmesh_to_domain_instance to convert a mesh file to a domain instance.
    """

    vertex_coordinates, vertices, tag_dict, vertex_quantity_dict \
                        ,tagged_elements_dict, geo_reference = \
                        pmesh_to_domain(mesh_instance=mesh)

    # NOTE(Ole): This import cannot be at the module level due to mutual
    # dependency with domain.py
    from anuga.abstract_2d_finite_volumes.domain import Domain

  


    msg = 'The class %s is not a subclass of the generic domain class %s'\
          %(DomainClass, Domain)
    assert issubclass(DomainClass, Domain), msg


    domain = DomainClass(coordinates = vertex_coordinates,
                         vertices = vertices,
                         boundary = tag_dict,
                         tagged_elements = tagged_elements_dict,
                         geo_reference = geo_reference )

    # set the water stage to be the elevation
    if vertex_quantity_dict.has_key('elevation') and not vertex_quantity_dict.has_key('stage'):
        vertex_quantity_dict['stage'] = vertex_quantity_dict['elevation']

    domain.set_quantity_vertices_dict(vertex_quantity_dict)
    #print "vertex_quantity_dict",vertex_quantity_dict
    return domain



def pmesh_to_domain_instance(file_name, DomainClass, use_cache = False, verbose = False):
    """
    Converts a mesh file(.tsh or .msh), to a Domain instance.

    file_name is the name of the mesh file to convert, including the extension

    DomainClass is the Class that will be returned.
    It must be a subclass of Domain, with the same interface as domain.

    use_cache: True means that caching is attempted for the computed domain.    
    """

    if use_cache is True:
        from caching import cache
        result = cache(_pmesh_to_domain_instance, (file_name, DomainClass),
                       dependencies = [file_name],                     
                       verbose = verbose)

    else:
        result = apply(_pmesh_to_domain_instance, (file_name, DomainClass))        
        
    return result




def _pmesh_to_domain_instance(file_name, DomainClass):
    """
    Converts a mesh file(.tsh or .msh), to a Domain instance.

    Internal function. See public interface pmesh_to_domain_instance for details
    """
    
    vertex_coordinates, vertices, tag_dict, vertex_quantity_dict, \
                        tagged_elements_dict, geo_reference = \
                        pmesh_to_domain(file_name=file_name)


    # NOTE(Ole): This import cannot be at the module level due to mutual
    # dependency with domain.py
    from anuga.abstract_2d_finite_volumes.domain import Domain


    msg = 'The class %s is not a subclass of the generic domain class %s'\
          %(DomainClass, Domain)
    assert issubclass(DomainClass, Domain), msg



    domain = DomainClass(coordinates = vertex_coordinates,
                         vertices = vertices,
                         boundary = tag_dict,
                         tagged_elements = tagged_elements_dict,
                         geo_reference = geo_reference )



    #FIXME (Ole): Is this really the right place to apply the a default
    #value specific to the shallow water wave equation?
    #The 'assert' above indicates that any subclass of Domain is acceptable.
    #Suggestion - module shallow_water.py will eventually take care of this
    #(when I get around to it) so it should be removed from here.

    # This doesn't work on the domain instance.
    # This is still needed so -ve elevations don't cuase 'lakes'
    # The fixme we discussed was to only create a quantity when its values
    #are set.
    # I think that's the way to go still

    # set the water stage to be the elevation
    if vertex_quantity_dict.has_key('elevation') and not vertex_quantity_dict.has_key('stage'):
        vertex_quantity_dict['stage'] = vertex_quantity_dict['elevation']

    domain.set_quantity_vertices_dict(vertex_quantity_dict)
    #print "vertex_quantity_dict",vertex_quantity_dict
    return domain


def pmesh_to_domain(file_name=None,
                    mesh_instance=None,
                    use_cache=False,
                    verbose=False):
    """
    Convert a pmesh file or a pmesh mesh instance to a bunch of lists
    that can be used to instanciate a domain object.

    use_cache: True means that caching is attempted for the computed domain.    
    """
 
    if use_cache is True:
        from caching import cache
        result = cache(_pmesh_to_domain, (file_name, mesh_instance),
                       dependencies = [file_name],                     
                       verbose = verbose)

    else:
        result = apply(_pmesh_to_domain, (file_name, mesh_instance))        
        
    return result


def _pmesh_to_domain(file_name=None,
                     mesh_instance=None,
                     use_cache=False,
                     verbose=False):
    """
    Convert a pmesh file or a pmesh mesh instance to a bunch of lists
    that can be used to instanciate a domain object.
    """

    from Numeric import transpose
    from load_mesh.loadASCII import import_mesh_file

    if file_name is None:
        mesh_dict = mesh_instance.Mesh2IODict()
    else:
        mesh_dict = import_mesh_file(file_name)
    #print "mesh_dict",mesh_dict
    vertex_coordinates = mesh_dict['vertices']
    volumes = mesh_dict['triangles']
    vertex_quantity_dict = {}
    point_atts = transpose(mesh_dict['vertex_attributes'])
    point_titles  = mesh_dict['vertex_attribute_titles']
    geo_reference  = mesh_dict['geo_reference']
    if point_atts != None:
        for quantity, value_vector in map (None, point_titles, point_atts):
            vertex_quantity_dict[quantity] = value_vector
    tag_dict = pmesh_dict_to_tag_dict(mesh_dict)
    tagged_elements_dict = build_tagged_elements_dictionary(mesh_dict)
    return vertex_coordinates, volumes, tag_dict, vertex_quantity_dict, tagged_elements_dict, geo_reference



def build_tagged_elements_dictionary(mesh_dict):
    """Build the dictionary of element tags.
    tagged_elements is a dictionary of element arrays,
    keyed by tag:
    { (tag): [e1, e2, e3..] }
    """
    tri_atts = mesh_dict['triangle_tags']
    tagged_elements = {}
    if tri_atts is None:
       tagged_elements[''] = range(len(mesh_dict['triangles']))
    else:
        for tri_att_index in range(len(tri_atts)):
            tagged_elements.setdefault(tri_atts[tri_att_index],
                                       []).append(tri_att_index)
    return tagged_elements

def pmesh_dict_to_tag_dict(mesh_dict):
    """ Convert the pmesh dictionary (mesh_dict) description of boundary tags
    to a dictionary of tags, indexed with volume id and face number.
    """
    triangles = mesh_dict['triangles']
    sides = calc_sides(triangles)
    tag_dict = {}
    for seg, tag in map(None, mesh_dict['segments'],
                        mesh_dict['segment_tags']):
        v1 = int(seg[0])
        v2 = int(seg[1])
        for key in [(v1,v2),(v2,v1)]:
            if sides.has_key(key) and tag <> "":
                #"" represents null.  Don't put these into the dictionary
                #this creates a dict of lists of faces, indexed by tag
                #tagged_edges.setdefault(tag,[]).append(sides[key])
                tag_dict[sides[key]] = tag

    return tag_dict


def calc_sides(triangles):
    #Build dictionary mapping from sides (2-tuple of points)
    #to left hand side neighbouring triangle
    sides = {}
    for id, triangle in enumerate(triangles):
        a = int(triangle[0])
        b = int(triangle[1])
        c = int(triangle[2])
        sides[a,b] = (id, 2) #(id, face)
        sides[b,c] = (id, 0) #(id, face)
        sides[c,a] = (id, 1) #(id, face)
    return sides