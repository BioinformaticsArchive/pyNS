#!/usr/bin/env python

## Program:   PyNS
## Module:    ModelAdaptor.py
## Language:  Python
## Date:      $Date: 2011/02/15 12:07:15 $
## Version:   $Revision: 0.1.6 $

##   Copyright (c) Simone Manini, Luca Antiga. All rights reserved.
##   See LICENCE file for details.

##      This software is distributed WITHOUT ANY WARRANTY; without even 
##      the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR 
##      PURPOSE.  See the above copyright notices for more information.

##   Developed with support from the EC FP7/2007-2013: ARCH, Project n. 224390

from csv import *
import csv
try:
    from lxml import etree
except:
    from xml.etree import ElementTree as etree
from datetime import date
import shutil

class ModelAdaptor(object):
    '''
    This Class adapts generic model according to
    specific dataset.
    This Class provides the following methods:
    SetNetworkGraph: a method for setting NetworkGraph input.
    SetSimulationContext : a method for setting simulation context.
    SettingParameters: a method for adapting simulation parameters from specific values.
    AdaptingModel: still under development.
    '''
    
    def __init__(self):
        '''
        Constructor
        '''
        self.NetworkGraph = None
        self.SimulationContext = None
        self.arm = None
        self.ftype = None
        self.Idpat = None
    
    def SetNetworkGraph(self,networkGraph):
        '''
        Setting NetworkGraph
        '''
        self.NetworkGraph = networkGraph
    
    def SetEvaluator(self,evaluator):
        '''
        Setting Evaluator
        '''
        self.Evaluator = evaluator
    
    def SetSimulationContext(self,simulationContext):
        '''
        Setting SimulationContext
        '''
        self.SimulationContext = simulationContext
        
    def ChoosingTemplate(self, csvfilepath):
        '''
        This method sets correct template according
        to parameters in .csv file
        '''
        csv_reader = reader(file(csvfilepath, "rU"))
        for row in csv_reader:
            el = row[0].split(";")
            name = el[0]
            value = el[1]
            if name == 'idpat':
                self.Idpat = str(value)
            if name == 'arm':
                self.arm = int(value)
            if name == 'ftype':
                self.ftype = int(value)
        
    def SettingParameters(self, csvfilepath):
        '''
        This method reads parameters from a .csv file and sets them into
        simulation context.
        '''
        csv_reader = reader(file(csvfilepath, "rU"))
        for row in csv_reader:
            el = row[0].split(";")
            name = el[0]
            value = el[1]
            
            if name == 'dob' or name == 'dos':
                self.SimulationContext.Context[name] = str(value)
            else:
                self.SimulationContext.Context[name] = float(value)
        
        
    def AdaptingParameters(self, genericXml, specificXml):
        '''
        This method evaluates expressions in boundary conditions file and
        re-writes a new boundary conditions xml file with computed values
        '''
        expressionList = []
        for name in self.SimulationContext.Context:
            if type(self.SimulationContext.Context[name]) is str:
                expressionList.append(self.SimulationContext.Context[name])
        while len(expressionList)>2:       
            for x in expressionList:
                try:
                    self.Evaluator.Evaluate(x)
                    expressionList.remove(x)
                except:
                    pass
        self.SimulationContext.UpdateXML(genericXml, specificXml)
    
    def AdaptingModel(self, genericXml, specificXml,csvfilepath=None):
        '''
        This method reads specific data from a csv file
        (measured radii) and evaluates the rest of the network rules.
        Finally, it creates a new vascular network xml file with specific data.
        '''
        shutil.copy(genericXml, specificXml)
        self.NetworkGraph.xmlgraphpath = specificXml
        
        if csvfilepath:
            print "Loading Specific Data"
            csv_reader = reader(file(csvfilepath, "rU"))
            for row in csv_reader:
                el = row[0].split(";")
                name = el[0]
                value1 = el[1]
                value2 = el[2]
                for edgeId, edge in self.NetworkGraph.Edges.iteritems():
                    if name == edge.Name: 
                        edge.Radius = {}
                        if value1 != value2:
                            edge.Radius['array'] = {0.0:(float(value1)*1e-3),1.0:(float(value2)*1e-3)}
                        else:
                            edge.Radius['value'] = (float(value1)*1e-3)
        
        expressionList = []                    
        for edgeId, edge in self.NetworkGraph.Edges.iteritems():
            if 'expression' in edge.Radius:
                expressionList.append(edge.Radius['expression'])  
            if 'expression' in edge.Length:
                expressionList.append(edge.Length['expression'])
            if 'expression' in edge.YoungModulus:
                expressionList.append(edge.YoungModulus['expression'])
            if edge.Compliance is not None:
                if 'expression' in edge.Compliance:
                    expressionList.append(edge.Compliance['expression'])  
            if 'array' in edge.Radius:
                for x in edge.Radius['array'].itervalues():
                    if type(x) is str:
                        expressionList.append(x)
                   
        while len(expressionList)>0:       
            for x in expressionList:
                try: 
                    self.Evaluator.Evaluate(x)
                    expressionList.remove(x)
                except:   
                    pass
                        
        
        root = etree.Element("NetworkGraph", id=self.NetworkGraph.Id, version="3.2")
        xmlgraph = etree.ElementTree(root)
        
        #CASE
        case = etree.SubElement(root, "case")
        patId = etree.SubElement(case, "patient_id")
        patId.text = self.NetworkGraph.PatientId
        visit = etree.SubElement(case, "visit")
        visit.text = self.NetworkGraph.Visit
        
        #NODES
        nodes_list = []
        nodes = etree.SubElement(root, "nodes")
        for node in self.NetworkGraph.Nodes.itervalues():
            nodes_list.append(int(node.Id))
        nodes_list.sort()
        for id in nodes_list:
            name = self.NetworkGraph.Nodes[str(id)].Name
            typee = self.NetworkGraph.Nodes[str(id)].Type
            prop = self.NetworkGraph.Nodes[str(id)].Properties
            if name and typee:
                node = etree.SubElement(nodes, "node", id = str(id), type = typee, name = name)
                if typee == 'downstream network':
                    node_p = etree.SubElement(node, "properties")
                    node_w = etree.SubElement(node_p, "windkessel")
                    node_e = etree.SubElement(node_w, "expression")
                    node_e.text = prop['windkessel']
                if typee == 'anastomosis':
                    node_p = etree.SubElement(node, "properties")
                    node_c = etree.SubElement(node_p, "connections")
                    node_pa = etree.SubElement(node_c, "proximal_artery", edge_id=str(prop['proximal']))
                    try:
                        node_da = etree.SubElement(node_c, "distal_artery", edge_id=str(prop['distal']))
                    except KeyError:
                        pass
                    node_pv = etree.SubElement(node_c, "proximal_vein", edge_id=str(prop['vein']))
                    node_ar = etree.SubElement(node_p, "arterial_resistance")
                    node_ar_e = etree.SubElement(node_ar, "expression")
                    node_ar_e.text = prop['arterial_resistance']
                    node_vr = etree.SubElement(node_p, "venous_resistance")
                    node_vr_e = etree.SubElement(node_vr, "expression")
                    node_vr_e.text = prop['venous_resistance']
                    
            else:
                etree.SubElement(nodes, "node", id = str(id))
                
                
        #SUPEREDGES
        superedges_list = []
        superedges = etree.SubElement(root, "superedges")
        for sedges in self.NetworkGraph.SuperEdges.iterkeys():
            superedges_list.append(int(sedges))
        superedges_list.sort()  
        
        for sedg in superedges_list:
            for s in self.NetworkGraph.SuperEdges.itervalues():
                if s.Id == str(sedg):
                    if s.SuperEdges != {}:
                        superedge = etree.SubElement(superedges, "superedge", id = str(s.Id), name = str(s.Name))
                        superedges2 = etree.SubElement(superedges, "superedges")
                    if s.SuperEdges == {}:
                        superedge2 = etree.SubElement(superedges2,"superedge", id = str(s.Id), name = str(s.Name))
                        edgeIdsel = etree.SubElement(superedge2, "edgesIds")
                        for edgeIds in s.Edges.iterkeys():
                            etree.SubElement(edgeIdsel, "edgeIds", edge_id = str(edgeIds))
                   
        #EDGES
        edges_list = []
        edges = etree.SubElement(root, "edges")
        for edge in self.NetworkGraph.Edges.iterkeys():
            edges_list.append(int(edge))
        edges_list.sort()
        
        for edg in edges_list:
            for e in self.NetworkGraph.Edges.itervalues():
                if e.Id == str(edg):
                    edge = etree.SubElement(edges, "edge", id = str(e.Id), name = str(e.Name), side = str(e.Side), node1_id = str(e.NodeIds[0]), node2_id = str(e.NodeIds[1]))
                    geometry = etree.SubElement(edge, "geometry")
                    length = etree.SubElement(geometry, "length", unit="m", accuracy="10%", source="US")
                    length_v = etree.SubElement(length, "scalar")
                    length_v.text = str(e.Length['value'])
                    properties = etree.SubElement(edge, "properties")
                    if e.xRadius:
                        if 'value' in e.xRadius:
                            xradius = etree.SubElement(properties, "radius_a", unit="m", accuracy="10%", source="US")
                            xradius_v = etree.SubElement(xradius, "scalar")
                            xradius_v.text = str(e.xRadius['value'])
                        if 'array' in e.xRadius:
                            xradius = etree.SubElement(properties, "radius_a_array", unit="m", accuracy="10%", source="US")
                            xradius_s1 = etree.SubElement(xradius, "value", s="0.0")
                            xradius_v1 = etree.SubElement(xradius_s1, "scalar")
                            xradius_v1.text = str(e.xRadius['array'][0.0])
                            xradius_s2 = etree.SubElement(xradius, "value", s="1.0")
                            xradius_v2 = etree.SubElement(xradius_s2, "scalar")
                            xradius_v2.text = str(e.xRadius['array'][1.0])
                        if 'value' in e.yRadius:
                            yradius = etree.SubElement(properties, "radius_b", unit="m", accuracy="10%", source="US")
                            yradius_v = etree.SubElement(yradius, "scalar")
                            yradius_v.text = str(e.yRadius['value'])
                        if 'array' in e.xRadius:
                            yradius = etree.SubElement(properties, "radius_b_array", unit="m", accuracy="10%", source="US")
                            yradius_s1 = etree.SubElement(yradius, "value", s="0.0")
                            yradius_v1 = etree.SubElement(yradius_s1, "scalar")
                            yradius_v1.text = str(e.yRadius['array'][0.0])
                            yradius_s2 = etree.SubElement(yradius, "value", s="1.0")
                            yradius_v2 = etree.SubElement(yradius_s2, "scalar")
                            yradius_v2.text = str(e.yRadius['array'][1.0])
                    else:
                        if 'value' in e.Radius:
                            radius = etree.SubElement(properties, "radius", unit="m", accuracy="10%", source="US")
                            radius_v = etree.SubElement(radius, "scalar")
                            radius_v.text = str(e.Radius['value'])
                        if 'array' in e.Radius:
                            radius = etree.SubElement(properties, "radius_array", unit="m", accuracy="10%", source="US")
                            radius_s1 = etree.SubElement(radius, "value", s="0.0")
                            radius_v1 = etree.SubElement(radius_s1, "scalar")
                            radius_v1.text = str(e.Radius['array'][0.0])
                            radius_s2 = etree.SubElement(radius, "value", s="1.0")
                            radius_v2 = etree.SubElement(radius_s2, "scalar")
                            radius_v2.text = str(e.Radius['array'][1.0])
                    if 'value' in e.WallThickness:
                        wt = etree.SubElement(properties, "wall_thickness", unit="m", accuracy="10%", source="US")
                        wt_v = etree.SubElement(wt, "scalar")
                        wt_v.text = str(e.WallThickness['value'])
                    if 'expression' in e.WallThickness:
                        wt = etree.SubElement(properties, "wall_thickness")
                        wt_v = etree.SubElement(wt, "expression")
                        wt_v.text = str(e.WallThickness['expression'])
                    if 'value' in e.YoungModulus:
                        ym = etree.SubElement(properties, "young_modulus", unit="Pa", accuracy="10%", source="US")
                        ym_v = etree.SubElement(ym, "scalar")
                        ym_v.text = str(e.YoungModulus['value'])
                    if 'expression' in e.YoungModulus:
                        ym = etree.SubElement(properties, "young_modulus")
                        ym_v = etree.SubElement(ym, "expression")
                        ym_v.text = str(e.YoungModulus['expression'])
                    if  e.Compliance is not None:
                        com = etree.SubElement(properties, "Compliance", unit="m3/Pa")
                        com_v = etree.SubElement(com, "scalar")
                        com_v.text = str(e.Compliance)
                    
        indent(root)
        xmlgraph.write (self.NetworkGraph.xmlgraphpath)  
            
        path = self.NetworkGraph.xmlgraphpath+'.csv' 
        ofile  = open(path, "wb")
        csv_writer = writer(ofile, delimiter=",", quoting=csv.QUOTE_ALL)
        csv_writer.writerow(["Name","Side", "Length", "Radius s=0", "Radius s=1","xRadius s=0", "xRadius s=1","yRadius s=0", "yRadius s=1", "Compliance", "YoungModulus"])
        csv_writer.writerow(["","", "cm", "mm", "mm","mm", "mm","mm", "mm", "mm2/kPa", "Pa"])
        for edg in edges_list:    
            for e in self.NetworkGraph.Edges.itervalues():
                if e.Id == str(edg):
                    try:
                        if 'value' in e.Radius:
                            e.Radius_0 = e.Radius['value']
                            e.Radius_1 = e.Radius['value']
                        else:
                            e.Radius_0 = e.Radius['array'][0.0]
                            e.Radius_1 = e.Radius['array'][1.0]
                        e.xRadius_0 = e.yRadius_0 = e.xRadius_1 = e.yRadius_1 = 0.0
                    except KeyError:
                        if 'value' in e.xRadius:
                            e.xRadius_0 = e.xRadius['value']
                            e.xRadius_1 = e.xRadius['value']
                        else:
                            try:
                                e.xRadius_0 = e.xRadius['array'][0.0]
                                e.xRadius_1 = e.xRadius['array'][1.0]
                            except:
                                e.xRadius_0 = 0
                                e.xRadius_1 = 0
                        if 'value' in e.yRadius:
                            e.yRadius_0 = e.yRadius['value']
                            e.yRadius_1 = e.yRadius['value']
                        else:
                            try:
                                e.yRadius_0 = e.yRadius['array'][0.0]
                                e.yRadius_1 = e.yRadius['array'][1.0]
                            except:
                                e.yRadius_0 = 0
                                e.yRadius_1 = 0
                        e.Radius_0 = e.Radius_1 = 0.0
                        
                    if e.Compliance is not None:
                        C = e.Compliance*1e9
                    else:
                        C = ''
                    if 'value' in e.YoungModulus:
                        ym = e.YoungModulus['value']
                    else:
                        ym = ''
                        
                    csv_writer.writerow([e.Name, e.Side, e.Length['value']*1e2, e.Radius_0*1e3, e.Radius_1*1e3,e.xRadius_0*1e3, e.xRadius_1*1e3,e.yRadius_0*1e3, e.yRadius_1*1e3, C, ym])
        csv_writer.writerow([])
        csv_writer.writerow([])
        csv_writer.writerow(["idpat", "gender", "age", "arm", "fistula type", "height", "weight", "bsa", "pressure", "cardiac output", "cardiac frequency", "brachial flow", "radial flow", "ulnar flow", "hematocrit", "plasma concentration","dynamic_viscosity", "blood_density","hypertension", "diabetes"])
        csv_writer.writerow(["", "", "" , "", "", "cm", "kg", "m2", "mmHg", "mL/min", "Hz", "mL/min", "mL/min", "mL/min", "%", "g/dL", "cP", "Kg/m3", "", ""])
        
        try:
            gender_s = self.SimulationContext.Context['gender']
            if gender_s == 0:
                gender = "female"
            if gender_s == 1:
                gender = "male"
        except KeyError:
            gender = "None"
        try:
            age = self.SimulationContext.Context['age']
        except KeyError:
            age = "None"
        try:
            arm_s = self.SimulationContext.Context['arm']
            if arm_s == 0:
                arm = "Left"
            if arm_s == 1:
                arm = "Right"
        except KeyError:
            arm = "None" 
        try:
            ftype_s = self.SimulationContext.Context['ftype']
            if ftype_s == 0:
                ftype = "Lower Radio-Cephalic EndToEnd"
            if ftype_s == 1:
                ftype = "Lower Radio-Cephalic EndToSide"
            if ftype_s == 2:
                ftype = "Lower Radio-Cephalic SideToSide"
            if ftype_s == 3:
                ftype = "Upper Brachio-Cephalic EndToSide"
            if ftype_s == 4:
                ftype = "Upper Brachio-Cephalic SideToSide"
            if ftype_s == 5:
                ftype = "Upper Brachio-Basilic EndToSide"
            if ftype_s == 6:
                ftype = "Upper Brachio-Basilic SideToSide"
            if ftype_s == 7:
                ftype = "Pre-Surgery"
        except KeyError:
            ftype = "None" 
        try:
            heigth = self.SimulationContext.Context['height']
        except KeyError:
            heigth = "None" 
        try:
            weigth = self.SimulationContext.Context['weight']
        except KeyError:
            weigth = "None" 
        try:
            bsa = self.SimulationContext.Context['bsa']
        except KeyError:
            bsa = "None"
        try:
            meanP = self.SimulationContext.Context['mean_pressure']
        except KeyError:
            meanP = "None"
        try:
            Co = self.SimulationContext.Context['cardiac_output']
        except KeyError:
            Co = "None"
        try:
            Cf = 1.0/(self.SimulationContext.Context['period'])
        except KeyError:
            Cf = "None"
        try:
            bflow = self.SimulationContext.Context['brachial_flow']
        except KeyError:
            bflow = "None"
        try:
            rflow = self.SimulationContext.Context['radial_flow']
        except KeyError:
            rflow = "None"
        try:
            uflow = self.SimulationContext.Context['ulnar_flow']
        except KeyError:
            uflow = "None"
        try:
            ht = self.SimulationContext.Context['ht']
        except KeyError:
            ht = "None"
        try:
            cp = self.SimulationContext.Context['cp']
        except KeyError:
            cp = "None"
        try:
            eta = self.SimulationContext.Context['dynamic_viscosity']*1e3
        except KeyError:
            eta = "None"
        try:
            bd = self.SimulationContext.Context['blood_density']
        except KeyError:
            bd = "None"
        try:
            hyp_s = self.SimulationContext.Context['hyp']
            if hyp_s == 0:
                hyp = "No"
            if hyp_s == 1:
                hyp = "Yes" 
        except KeyError:
            hyp = "None"
        try:
            dia_s = self.SimulationContext.Context['diab']
            if dia_s == 0:
                dia = "No"
            if dia_s == 1:
                dia = "Yes" 
        except KeyError:
            dia = "None"
    
        csv_writer.writerow(['id_'+self.Idpat, gender, age, arm, ftype, heigth, weigth, bsa, meanP, Co, Cf, bflow, rflow, uflow, ht, cp, eta, bd, hyp, dia])
        

def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i       