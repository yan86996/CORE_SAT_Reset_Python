import os, sys, time, shutil, re
from datetime import datetime
import numpy as np
from pprint import pprint

class Requests:
  """ This superclass calculates the number of requests
  for each zone
  """
  
  def __init__(self, verbose=False, ignore=[], important=[], folder_dir = None,
               zone_names=None, zone_dev_map = None, room_temp=None, clg_setpoint=None,    
               flow=None, flow_min=None, flow_max=None, damper=None,
	           lim_dt_errs = 20,  fdd=False, low_temp_cutoff=None, high_temp_cutoff=None):
               
    self.rR = 0 # raw requests
    self.R = 0 # importance weighted requests
    self.ignore = ignore
    self.important = important
    self.zone_dev_map = zone_dev_map
    self.zd = {} # dict object representing all of the necessary zone data
    self.missingPartial = [] # list of names of zones that are missing some required data
    self.missingEssential = [] # list of names of zones that are missing some required data
    self.verbose = verbose
    self.folder_dir = folder_dir
    self.zone_names = zone_names
    self.room_temp = room_temp
    self.clg_setpoint = clg_setpoint
    self.flow = flow
    self.flow_max = flow_max
    self.flow_min = flow_min
    self.damper = damper
    self.fdd = fdd
    self.low_temp_cutoff = low_temp_cutoff
    self.high_temp_cutoff = high_temp_cutoff
    self.lim_dt_errs = lim_dt_errs
    
  def update(self):
    # method to be overridden depending on data
    # required to calculate the requests
    raise NotImplementedError

  def handleAtypicalZones(self):
    # ignore any ignored zones
    for z in sorted(self.ignore):
      if z in self.zd:
        del self.zd[z]        
    # ignore any zones missing essential data      
    for z in sorted(self.missingEssential):
      if z in self.zd:
        del self.zd[z]  
    
  def calcTotalRequests(self):
    # Sum up the total number of requests (and also weighted by importance)
    self.rR = 0
    self.R = 0
    for z in self.zd:
      if 'requests' in self.zd[z]:
        self.rR += self.zd[z]['requests']
        if 'importance' in self.zd[z]:
          self.R += self.zd[z]['requests'] * float(self.zd[z]['importance'])
        else:
          self.R += self.zd[z]['requests']

    rv = {
      'raw_requests': self.rR, 
      'weighted_requests': self.R, 
      'ignored_zones': self.ignore, 
      'partial_zones': self.missingPartial
    }

    if self.verbose:
      print('\n================= Requests summary ================ ')
      print('Total raw requests: ' + str(self.rR))
      print('Total importance-weighted requests: ' + str(self.R))
      if len(self.ignore):
        print('Ignored zones (user selected): ')
        pprint(self.ignore)
      if len(self.missingEssential):   
        print('Ignored zones (due to missing essential data): ')
        pprint(self.missingEssential)    
      if len(self.missingPartial):  
        print('Partial request results only (due to missing data, or a failed point): ')
        pprint(self.missingPartial)

    return rv

class Pressure(Requests):
  """ This class calculates the number of requests
  for a duct static pressure reset strategy according
  to the Tailor Engineering Sequence of Operations.
  """

  def __init__(self, *args, **kwargs):
    super(Pressure, self).__init__(*args, **kwargs)

  def update(self):
    self.missingPartial = []
    self.missingEssential = []

    # clear existing zone data from previous update
    for z in self.zd:
      if 'damper' in self.zd[z]:
        del self.zd[z]['damper']
      if 'flow' in self.zd[z]:
        del self.zd[z]['flow']
      if 'flow_max' in self.zd[z]:
        del self.zd[z]['flow_max']      

    for zone_name in self.zone_names:
        self.zd[zone_name] = {}
        
        # from AV_XXXX.csv
        div_ID = self.zone_dev_map[zone_name]
        zone_csv_AV = os.path.join(self.folder_dir, f'AV_{div_ID}.csv')
        zone_data_AV = np.genfromtxt(zone_csv_AV, delimiter=',', dtype=None, names=True, encoding='utf-8')
        
        # min airflow
        min_flow = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], self.flow_min) >= 0][0]
        self.zd[zone_name]['min_flow'] = min_flow
        # max airflow
        max_flow = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], self.flow_max) >= 0][0]
        self.zd[zone_name]['max_flow'] = max_flow  
        
        # from AI_XXXX.csv
        zone_csv_AI = os.path.join(self.folder_dir, f'AI_{div_ID}.csv')
        zone_data_AI = np.genfromtxt(zone_csv_AI, delimiter=',', dtype=None, names=True, encoding='utf-8') 
        
        # airflow
        airflow = zone_data_AI['Present_Value'][np.char.find(zone_data_AI['Object_Name'], self.flow) >= 0][0]
        self.zd[zone_name]['flow'] = airflow
    
    print('\n======= for pressure requests =======\n' )
    print(self.zd)

    # calculate requests
    for z in sorted(self.zd):
      if 'damper' in self.zd[z]:
        if self.zd[z]['damper'] < 95:
          self.zd[z]['requests'] = 0
        if self.zd[z]['damper'] >= 95:
          self.zd[z]['requests'] = 1
          if 'flow' in self.zd[z] and 'flow_max' in self.zd[z]:
            if self.zd[z]['flow'] <= self.zd[z]['flow_max']*0.7:
              self.zd[z]['requests'] = 2    
            if self.zd[z]['flow'] <= self.zd[z]['flow_max']*0.5:
              self.zd[z]['requests'] = 3
            if self.zd[z]['flow'] <= self.zd[z]['flow_max']*0.25 and self.fdd:
              self.zd[z]['requests'] = 0
              self.missingPartial.append(z)
          else:
            self.missingPartial.append(z)
      else:
        self.missingEssential.append(z)

    self.handleAtypicalZones()

    if self.verbose:
      self.displayDetails()

    return self.calcTotalRequests()

  def displayDetails(self):
    # Print the results for each zone if requested
    print('\n================= Details for zones with almost fully open dampers ================ ')
    for z in sorted(self.zd):
      if self.zd[z]['damper'] >= 95:
        print(str(z))
        pprint(self.zd[z])


class Temperature(Requests):

  def __init__(self, *args, **kwargs):
    super(Temperature, self).__init__(*args, **kwargs)

  def update(self):
    self.missingPartial = []
    self.missingEssential = []
    self.h = 0
 
    # clear existing zone data from previous update
    for z in self.zd:
      if 'cooling_loop' in self.zd[z]:
        del self.zd[z]['cooling_loop']
      if 'room_temp' in self.zd[z]:
        del self.zd[z]['room_temp']
      if 'clg_setpoint' in self.zd[z]:
        del self.zd[z]['clg_setpoint']

    for zone_name in self.zone_names:
        self.zd[zone_name] = {}
        # get zone data
        div_ID = self.zone_dev_map[zone_name]
        zone_csv = os.path.join(self.folder_dir, f'AV_{div_ID}.csv')
        zone_data = np.genfromtxt(zone_csv, delimiter=',', dtype=None, names=True, encoding='utf-8')
        
        # min airflow
        min_flow = zone_data['Present_Value'][np.char.find(zone_data['Object_Name'], self.flow_min) >= 0][0]
        self.zd[zone_name]['min_flow'] = min_flow

        # max airflow
        max_flow = zone_data['Present_Value'][np.char.find(zone_data['Object_Name'], self.flow_max) >= 0][0]
        self.zd[zone_name]['max_flow'] = max_flow  

        # room temp
        self.zd[zone_name]['room_temp'] = zone_data['Present_Value'][np.char.find(zone_data['Object_Name'], self.room_temp) >= 0][0] 

        # cooling setpoint
        self.zd[zone_name]['clg_setpoint'] = zone_data['Present_Value'][np.char.find(zone_data['Object_Name'], self.clg_setpoint) >= 0][0] 
        
        # from AI_XXXX.csv
        zone_csv_AI = os.path.join(self.folder_dir, f'AI_{div_ID}.csv')
        zone_data_AI = np.genfromtxt(zone_csv_AI, delimiter=',', dtype=None, names=True, encoding='utf-8') 
        
        # airflow
        airflow = zone_data_AI['Present_Value'][np.char.find(zone_data_AI['Object_Name'], self.flow) >= 0][0]
        self.zd[zone_name]['flow'] = airflow
        
        # cooling loop
        self.zd[zone_name]['cooling_loop'] = (self.zd[zone_name]['flow'] - min_flow)/(max_flow - min_flow)
     
    # print('\n======= for cooling requests =======\n' )
    # print(self.zd)

    # count cooling zones           
    self.c = 0
    # calculate cooling requests
    for z in sorted(self.zd):
      if 'cooling_loop' in self.zd[z]:
        if self.zd[z]['room_temp'] > self.zd[z]['clg_setpoint']:
          self.c += 1   
        if self.zd[z]['cooling_loop'] < .95:
          self.zd[z]['requests'] = 0
        if self.zd[z]['cooling_loop'] >= .95:
          self.zd[z]['requests'] = 1
          
        if self.zd[z]['room_temp'] >= self.zd[z]['clg_setpoint'] + 3.0:
          self.zd[z]['requests'] = 2    
        if self.zd[z]['room_temp'] >= self.zd[z]['clg_setpoint'] + 5.0:
          self.zd[z]['requests'] = 3
          
        if self.low_temp_cutoff:
          if self.zd[z]['clg_setpoint'] <= self.low_temp_cutoff:
            #ignore requests from zone with a setpoint below a self.low_temp_cutoff
            self.zd[z]['requests'] = 0
          else:
            self.missingPartial.append(z)
      else:
        self.missingEssential.append(z)

    self.handleAtypicalZones()
    
    if self.verbose:
      self.displayDetails()

    rv = self.calcTotalRequests()
    rv['cooling_zones'] = self.c
    
    return rv

  def displayDetails(self):
    # Print the results for each zone if requested
    print('\n================= Details for zones with cooling loop almost at maximum ================ ')
    for z in sorted(self.zd):
      if 'cooling_loop' in self.zd[z]:
        if self.zd[z]['cooling_loop'] >= 95:
          print(str(z))
          pprint(self.zd[z])
