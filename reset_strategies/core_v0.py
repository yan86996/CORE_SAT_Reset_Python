import os, sys
import datetime as dt
import csv
import time
from datetime import datetime
import numpy as np
import util_rate
# import zone_requests, reset

class CORE:
    def __init__(self, algo=None, core_version=None, dehumid=None, folder_dir=None,  dehumd_limits=None, g36_sat=None, 
                 vdf_dev_map=None, zone_names=None, ahu_name=None, zone_dev_map=None, flow=None, flow_min=None, flow_max=None, zone_requests=None, reset=None,          
                 ahu_dev_map=None,num_ignore=None, diff_sat=None, important=None, SP0=None, SPtrim=None, SPres=None, SPres_max=None,                    
                 ):
        self.algo = algo
        self.core_version = core_version
        self.dehumid = dehumid
        self.g36_sat = g36_sat
        self.folder_dir = folder_dir
        self.SP0 = SP0 # default setpoint if control algo doesn't work
        
        # log data2save for each timestamp
        self.ts_data = []
        self.ts_header = []
        
        # zone_requests is an instantiated temp request object
        self.requests = zone_requests 
        self.ts_data.append(self.requests.R) # log
        self.ts_header.append('number of zone requests') # log
        
        # reset is an instantiated reset object
        self.reset = reset    
        # min/max sat
        self.min_sat_sp = self.reset.SPmin
        self.max_sat_sp = self.reset.SPmax
        self.ts_data.append(self.min_sat_sp) # log
        self.ts_header.append('min SAT') # log
        self.ts_data.append(self.max_sat_sp) # log
        self.ts_header.append('max SAT') # log
        
        self.num_ignore = num_ignore
        self.SPtrim = SPtrim
        self.SPres = SPres
        self.SPres_max = SPres_max
        self.important = important
        self.vavs = zone_names
        self.flow = flow
        self.flow_min = flow_min
        self.flow_max = flow_max
        self.zone_dev_map = zone_dev_map
        self.satsp_name = 'Supply Air Setpoint'
        self.dehumd_limits = dehumd_limits
              
        # get AHU data
        self.ahu_name = ahu_name
        ahu_dev_ID = ahu_dev_map[ahu_name]
        self.ahu_dev_ID = ahu_dev_ID
        
        # from AV_XXXX.csv
        ahu_csv_AV = os.path.join(self.folder_dir, f'AV_{ahu_dev_ID}.csv')
        ahu_data_AV = np.genfromtxt(ahu_csv_AV, delimiter=',', dtype=None, names=True, encoding='utf-8')
        self.ahu_data_AV = ahu_data_AV
        self.ahu_data_AV_header = ahu_data_AV.dtype.names
        
        # cur sat setpoint
        self.cur_satsp = ahu_data_AV['Present_Value'][np.char.find(ahu_data_AV['Object_Name'], self.satsp_name) >= 0][0]
        self.ts_data.append(self.cur_satsp) # log 
        self.ts_header.append('current SAT setpoint') # log 
       
        # cur oat
        self.cur_oat = ahu_data_AV['Present_Value'][np.char.find(ahu_data_AV['Object_Name'], 'Outside Air Temperature') >= 0][0]
        self.ts_data.append(self.cur_oat) # log 
        self.ts_header.append('current outdoor temp') # log        
        
        # cur oa rh
        cur_oarh = ahu_data_AV['Present_Value'][np.char.find(ahu_data_AV['Object_Name'], 'Outside Air Humidity') >= 0][0]
        self.ts_data.append(cur_oarh) # log 
        self.ts_header.append('current outdoor air RH') # log
        
        # cal oa dewpoint
        self.cur_oa_dpwt = self.cal_dew_point_temperature(self.cur_oat, cur_oarh)
        self.ts_data.append(self.cur_oa_dpwt) # log 
        self.ts_header.append('calculated outdoor air dewpoint') # log  

        # from AI_XXXX.csv
        ahu_csv_AI = os.path.join(self.folder_dir, f'AI_{ahu_dev_ID}.csv')
        ahu_data_AI = np.genfromtxt(ahu_csv_AI, delimiter=',', dtype=None, names=True, encoding='utf-8')
        
        # cur sat
        self.cur_sat = ahu_data_AI['Present_Value'][np.char.find(ahu_data_AI['Object_Name'], 'Supply Air Temperature') >= 0][0]       
        self.ts_data.append(self.cur_sat) # log
        self.ts_header.append('current SAT') # log
              
        # mat
        self.mat = ahu_data_AI['Present_Value'][np.char.find(ahu_data_AI['Object_Name'], 'Mixed Air Temperature') >= 0][0]
        self.ts_data.append(self.mat) # log 
        self.ts_header.append('current MAT') # log
        
        # supply air RH
        sa_rh = ahu_data_AI['Present_Value'][np.char.find(ahu_data_AI['Object_Name'], 'Supply Air Humidity') >= 0][0]       
        self.ts_data.append(sa_rh) # log 
        self.ts_header.append('supply air RH') # log
        
        # from AO_XXXX.csv
        # clg coil valve 
        ahu_csv_AO = os.path.join(self.folder_dir, f'AO_{ahu_dev_ID}.csv')
        ahu_data_AO = np.genfromtxt(ahu_csv_AO, delimiter=',', dtype=None, names=True, encoding='utf-8')
        self.ccv = ahu_data_AO['Present_Value'][np.char.find(ahu_data_AO['Object_Name'], 'Chilled Water Control Valve') >= 0][0]
        self.ts_data.append(self.ccv) # log 
        self.ts_header.append('chilled water control valve') # log
        
        # htg coil valve 
        self.hcv = ahu_data_AO['Present_Value'][np.char.find(ahu_data_AO['Object_Name'], 'Steam Coil 1 Control Valve') >= 0][0]
        self.ts_data.append(self.hcv) # log 
        self.ts_header.append('steam coil 1 control valve') # log
        
        # oa damper
        self.oa_damper = ahu_data_AO['Present_Value'][np.char.find(ahu_data_AO['Object_Name'], 'Outside Air Damper') >= 0][0]
        self.ts_data.append(self.oa_damper) # log 
        self.ts_header.append('outside air damper') # log
               
        # sat changes
        self.diff_sat = np.asarray(diff_sat)
        
        # vfd power (TO CHANGE)
        vfd_dev_ID = vdf_dev_map[ahu_name] 
        vfd_sf_power = 0
        vfd_rf_power = 0
        
        for key, value in vfd_dev_ID.items():
            # get supply fan(s)
            if 'SF' in key.upper():
                sf_csv_AV = os.path.join(self.folder_dir, f'AV_{value}.csv')
                sf_data_AV = np.genfromtxt(sf_csv_AV, delimiter=',', dtype=None, names=True, encoding='utf-8')
                sf_power = sf_data_AV['Present_Value'][np.char.find(sf_data_AV['Object_Name'], 'POWER') >= 0][0]
                vfd_sf_power += sf_power
                self.ts_data.append(sf_power) # log 
                self.ts_header.append(key + ' power ' + ahu_name) # log
            
            # get return fan(s)
            if 'RF' in key.upper():                 
                rf_csv_AV = os.path.join(self.folder_dir, f'AV_{value}.csv') 
                rf_data_AV = np.genfromtxt(rf_csv_AV, delimiter=',', dtype=None, names=True, encoding='utf-8')
                rf_power = rf_data_AV['Present_Value'][np.char.find(rf_data_AV['Object_Name'], 'POWER') >= 0][0]
                vfd_rf_power += rf_power
                self.ts_data.append(rf_power) # log 
                self.ts_header.append(key + ' power '+ ahu_name) # log
                
        self.vfd_sf_power = vfd_sf_power  # KW
        self.vfd_rf_power = vfd_rf_power  # KW
        
        # Chilled efficiency
        self.chw_eff = 0.8
             
        # init estimations
        self.rhv_coils_hist = {}
        self.estimations = {}
        
       # check if logging var in AV_9999999.csv
        log_AV_csv = os.path.join(self.folder_dir, 'AV_9999999.csv')
        
        if os.path.isfile(log_AV_csv):
            log_data_AV = np.genfromtxt(log_AV_csv, delimiter=',', dtype=None, names=True, encoding='utf-8')          
            
            # check if chw_coils_hist already exists
            if ('chw_coils_hist_'+ ahu_name) not in log_data_AV['Object_Name']:
                self.chw_coils_hist = 0
            else:
                self.chw_coils_hist = log_data_AV['Present_Value'][np.char.find(log_data_AV['Object_Name'], 'chw_coils_hist_'+ ahu_name) >= 0][0]
            
            # check if clg_coil_clo_temp_chg already exists
            if ('clg_coil_clo_temp_chg_'+self.ahu_name) not in log_data_AV['Object_Name']:
                self.estimations['clg_coil_clo_temp_chg_'+self.ahu_name] = 2
            else:
                self.estimations['clg_coil_clo_temp_chg_'+self.ahu_name] = log_data_AV['Present_Value'][np.char.find(log_data_AV['Object_Name'], 'clg_coil_clo_temp_chg_'+ ahu_name) >= 0][0]

            # if rhv_coils_hist already exists
            for vav in self.vavs:
                if ('rhv_coils_hist_' + vav) not in log_data_AV['Object_Name']:
                    self.rhv_coils_hist['rhv_coils_hist_' + vav]= 0
                    self.estimations['rhv_clo_temp_chg_' + vav] = 2
                else:
                    self.rhv_coils_hist['rhv_coils_hist_' + vav] = log_data_AV['Present_Value'][np.char.find(log_data_AV['Object_Name'], 'rhv_coils_hist_'+ vav) >= 0][0]
                    self.estimations['rhv_clo_temp_chg_' + vav] = log_data_AV['Present_Value'][np.char.find(log_data_AV['Object_Name'], 'rhv_clo_temp_chg_'+ vav) >= 0][0]
                      
        else: 
            # update clg coil hist and temp_change_when_closed
            self.chw_coils_hist = 0
            self.estimations['clg_coil_clo_temp_chg_'+self.ahu_name] = 2
            
            # reheat coil hist exists for all vavs
            for vav in self.vavs:
                self.rhv_coils_hist['rhv_coils_hist_' + vav] = 0
                self.estimations['rhv_clo_temp_chg_' + vav] = 2
                     
        # Reheat (TO CHANGE)
        self.hw_price = 0.2
    
    def get_new_satsp(self):
        # calculate the feasible range of diff_sat
        candidate_sat = self.diff_sat + self.cur_satsp
        
        if self.dehumid == True:
            lo_oa_dwpt, hi_oa_dwpt, spmax_at_lo_oat_dwpt, spmax_at_hi_oat_dwpt = self.dehumd_limits
            humd_SPmax = self.calc_sp_limit(self.cur_oa_dpwt, lo_oa_dwpt, hi_oa_dwpt, spmax_at_lo_oat_dwpt, spmax_at_hi_oat_dwpt)              
            self.max_sat_sp = min(self.max_sat_sp, humd_SPmax)
            self.reset.SPmax = self.max_sat_sp
            
        # sat setpoint range check
        candidate_sat = np.where(candidate_sat > self.max_sat_sp, self.max_sat_sp, candidate_sat)
        candidate_sat = np.where(candidate_sat < self.min_sat_sp, self.min_sat_sp, candidate_sat)  
        diff_sat = candidate_sat - self.cur_satsp
        
        # estimate power consumption values under different setpoints    
        self.estimate_power(self.cur_satsp, diff_sat)
        
        # estimate costs under different setpoints
        datetime_obj = datetime.fromtimestamp(int(time.time()))
        elec_price   = util_rate.price(datetime_obj, 2)
        self.estimations['chw_cost_delta'] = elec_price    * self.estimations['chw_power_delta'] / self.chw_eff
        self.estimations['rhv_cost_delta'] = self.hw_price * self.estimations['rhv_power_delta']
        self.estimations['fan_cost_delta'] = elec_price    * self.estimations['fan_power_delta']
        self.estimations['tot_cost_delta'] = self.estimations['chw_cost_delta'] + self.estimations['rhv_cost_delta'] + self.estimations['fan_cost_delta']
        
        idx_opt = np.argmin(self.estimations['tot_cost_delta'])
        
        # new sat setpoint
        if self.requests.R > self.num_ignore:
            # comfort constraint present
            # use trim and respond without outside air based SAT setpoint limits
            new_core_sat = self.reset.get_new_setpoint(self.requests.R, self.cur_sat)
        else:
            # no comfort constraint present
            new_core_sat = self.cur_satsp + diff_sat[idx_opt]
        
        self.ts_data.append(new_core_sat) # log 
        self.ts_header.append('new CORE SAT setpoint') # log
        
        ###
        ## write SAT setpoint back 
        ###
        new_ahu_data_AV = self.ahu_data_AV.copy()
        idx_find = [np.char.find(self.ahu_data_AV['Object_Name'], self.satsp_name)>=0][0]
        
        # write G36 new sat setpoint if algo == 1
        if self.algo == 1:
            new_ahu_data_AV['Present_Value'][idx_find] = self.g36_sat
            print(f'# G36 control used: the new sat setpoint for {self.ahu_name} is {round(new_core_sat,2)}')    

        # write CORE new sat setpoint if algo == 2
        elif self.algo == 2:
            new_ahu_data_AV['Present_Value'][idx_find] = new_core_sat
            print(f'# CORE control used: the new sat setpoint for {self.ahu_name} is {round(new_core_sat,2)}')         
        
        
        
        ###### 
        ### logging data points including trending variables
        ###### 
        # algo num
        algo_array = ('9999999', 'algo number', '9999999', 'algo to choose for' + self.ahu_name, self.algo,'/')
        new_ahu_data_AV = self.log_data(algo_array, self.ahu_data_AV, new_ahu_data_AV) 
        
        # G36 SAT setpoint
        g36_satsp_array = ('9999999', 'logging', '9999999', 'G36 satsp ' + self.ahu_name, self.g36_sat,'°F')
        new_ahu_data_AV = self.log_data(g36_satsp_array, self.ahu_data_AV, new_ahu_data_AV) 
        
        # CORE SAT setpoint
        core_satsp_array = ('9999999', 'logging', '9999999', 'CORE satsp ' + self.ahu_name, new_core_sat,'°F')
        new_ahu_data_AV = self.log_data(core_satsp_array, self.ahu_data_AV, new_ahu_data_AV) 
        
        # AHU clg coil temp change 
        new_clgcoil_tempchg_data = ('9999999', 'trend', '9999999', 'clg_coil_clo_temp_chg_' + self.ahu_name, 
                                    self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name], '°F')
        new_ahu_data_AV = self.log_data(new_clgcoil_tempchg_data, self.ahu_data_AV, new_ahu_data_AV)
        
        # AHU clg coil hist
        new_clgcoil_tempchg_data = ('9999999', 'hist', '9999999', 'chw_coils_hist_' + self.ahu_name, 
                                    self.estimations['chw_coils_hist_' + self.ahu_name], '/')
        new_ahu_data_AV = self.log_data(new_clgcoil_tempchg_data, self.ahu_data_AV, new_ahu_data_AV)
        
        # vav reheat coil
        for vav in self.vavs:
            # reheat coil temp change 
            new_rhv_tempchg_data = ('9999999', 'trend', '9999999', 'rhv_clo_temp_chg_' + vav, self.estimations['rhv_clo_temp_chg_' + vav], '°F')                                                  
            new_ahu_data_AV = self.log_data(new_rhv_tempchg_data, self.ahu_data_AV, new_ahu_data_AV)
            
            # reheat coil hist 
            new_rhv_hist_data = ('9999999', 'hist', '9999999', 'rhv_coils_hist_' + vav, self.rhv_coils_hist['rhv_coils_hist_'+vav], '/')                                              
            
            new_ahu_data_AV = self.log_data(new_rhv_hist_data, self.ahu_data_AV, new_ahu_data_AV)
        
        # write to AV_.csv
        overwrite_csv = os.path.join(self.folder_dir, f'AV_{self.ahu_dev_ID}_out.csv')
        with open(overwrite_csv, "w", encoding='utf-8') as f:
            np.savetxt(f, new_ahu_data_AV, header=','.join(self.ahu_data_AV_header), delimiter=",", fmt='%s')
             
        ###
        ## save time-series vars on a daily basis
        ###
        # CORE cal values
        core_cal_list = [candidate_sat, self.estimations['tot_cost_delta'], self.estimations['chw_cost_delta'],
                         self.estimations['rhv_cost_delta'], self.estimations['fan_cost_delta'], self.estimations['diff_zone_tot_afr']]
        
        core_cal_list = np.concatenate([arr.flatten() for arr in core_cal_list]).tolist() 
        core_cal_list = [self.algo, self.g36_sat, new_core_sat,
                         self.core_version, self.estimations['clg_coil_clo_temp_chg_'+self.ahu_name], self.chw_coils_hist] + core_cal_list   
        
        core_cal_header = ['algo_num', 'G36 satsp '+self.ahu_name, 'CORE satsp '+self.ahu_name,
                           'core_version',   ' clg_coil_clo_temp_chg_'+self.ahu_name, 'chw_coils_hist_'+self.ahu_name,  
                           'candidate_sat_lo',     'candidate_sat',     'candidate_sat_hi', 
                           'tot_cost_delta_lo',    'tot_cost_delta',    'tot_cost_delta_hi',
                           'chw_cost_delta_lo',    'chw_cost_delta',    'chw_cost_delta_hi',
                           'rhv_cost_delta_lo',    'rhv_cost_delta',    'rhv_cost_delta_hi',
                           'fan_cost_delta_lo',    'fan_cost_delta',    'fan_cost_delta_hi',
                           'diff_zone_tot_afr_lo', 'diff_zone_tot_afr', 'diff_zone_tot_afr_hi',
                           ]

        # combine all vars to save 
        data2save = core_cal_list + self.ts_data
        header = core_cal_header + self.ts_header

        self.save_data_bydate(data2save, header, self.folder_dir, self.ahu_name)
        
    ######
    ### Zone level calculations for reheat power and airflow under different SAT setpoints
    ######
    def estimate_power(self, cur_sat_sp, diff_sat):
        num = len(diff_sat)
        self.estimations['chw_power_delta']   = np.zeros(num)
        self.estimations['rhv_power_delta']   = np.zeros(num)
        self.estimations['fan_power_delta']   = np.zeros(num)
        self.estimations['diff_zone_tot_afr'] = np.zeros(num)
                
        # init total zone airflow rate (afr)
        afr = 0
        
        # loop through each zone vav box
        for vav in self.vavs:
            div_ID = self.zone_dev_map[vav]
                        
            # from AI_XXXX.csv
            zone_csv_AI = os.path.join(self.folder_dir, f'AI_{div_ID}.csv')
            zone_data_AI = np.genfromtxt(zone_csv_AI, delimiter=',', dtype=None, names=True, encoding='utf-8') 
            
            # discharge air temperature
            zone_dat = zone_data_AI['Present_Value'][np.char.find(zone_data_AI['Object_Name'], 'Supply Air Temperature') >= 0][0]
            self.ts_data.append(zone_dat) # log
            self.ts_header.append(vav +' DAT') # log
            
            # airflow
            zone_afr = zone_data_AI['Present_Value'][np.char.find(zone_data_AI['Object_Name'], self.flow) >= 0][0]
            self.ts_data.append(zone_afr) # log
            self.ts_header.append(vav +' air flow rate') # log
            
            # total zone afr update
            afr += zone_afr       
            
            # from AV_XXXX.csv
            zone_csv_AV = os.path.join(self.folder_dir, f'AV_{div_ID}.csv')
            zone_data_AV = np.genfromtxt(zone_csv_AV, delimiter=',', dtype=None, names=True, encoding='utf-8')          

            # min airflow
            afr_min = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], self.flow_min) >= 0][0]
            self.ts_data.append(afr_min) # log 
            self.ts_header.append(vav +' min air flow rate') # log       
            
            # max airflow
            afr_max = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], self.flow_max) >= 0][0]         
            self.ts_data.append(afr_max) # log 
            self.ts_header.append(vav +' max air flow rate') # log
            
            # cooling loop 
            clg = (zone_afr - afr_min)/(afr_max - afr_min) * 100
            
            # heating setpoint
            hg_sp = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'Heating Setpoint') >= 0][0]
            self.ts_data.append(hg_sp) # log 
            self.ts_header.append(vav +' heating setpoint') # log
            
            # cooling setpoint
            clg_sp = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'Cooling Setpoint') >= 0][0]             
            self.ts_data.append(clg_sp) # log 
            self.ts_header.append(vav +' cooling setpoint') # log
            
            # room temp
            room_temp = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'Space Temperature') >= 0][0]        
            self.ts_data.append(room_temp) # log 
            self.ts_header.append(vav +' room temp') # log
            
            # reheat
            reheat_pos = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'Reheat Valve Position') >= 0][0]
            self.ts_data.append(reheat_pos) # log 
            self.ts_header.append(vav +' reheat valve position') # log
            
            # calculate AFR difference under different SAT setpoints
            diff_zone_afr = self.calc_diff_zone_afr(reheat_pos, cur_sat_sp, diff_sat, zone_afr, hg_sp, clg_sp, room_temp, afr_min, afr_max, clg)
            self.estimations['diff_zone_tot_afr'] += diff_zone_afr
            new_zone_afr = zone_afr + diff_zone_afr
            
            # VAV boxes with reheat
            # update coil temp change when closed
            # and heat flow estimate
            if reheat_pos == 0:
                self.estimations['rhv_power_delta_' + vav] = np.zeros(len(diff_sat))
                self.estimations['rhv_power_' + vav] = 0
                self.ts_data += [0, 0, 0] # log
                
                ### for debugging and tracking purposes only
                if self.rhv_coils_hist['rhv_coils_hist_'+vav] > 0:
                    self.estimations['rhv_clo_temp_chg_' + vav] = ((zone_dat - self.cur_sat)*0.01) + (0.99*self.estimations['rhv_clo_temp_chg_' + vav])
                     
            else:
                self.estimations['rhv_power_delta_' + vav] = self.calc_heat_flow(new_zone_afr, -diff_sat)  
                self.estimations['rhv_power_delta'] += self.estimations['rhv_power_delta_' + vav]
               
                ### for debugging and tracking purposes only
                delta_T = zone_dat - self.estimations['rhv_clo_temp_chg_' + vav] - (cur_sat_sp + diff_sat)
                diff_rhv_power = self.calc_heat_flow(new_zone_afr, delta_T)
                self.ts_data += np.concatenate([arr.flatten() for arr in diff_rhv_power]).tolist() # log 
            
            self.ts_header += [vav+' rhv power for lo SAT', vav+' rhv power for cur SAT', vav+' rhv power for hi SAT', ] # log                                  
                                             
        diff_afr = self.estimations['diff_zone_tot_afr']
        afr_ratio = (afr + diff_afr)/afr
        
        ### fan power based on vfd percent out and motor rating
        # for each candidate sat (based on fan power law)
        # supply + return fans 
        cur_power = self.vfd_sf_power + self.vfd_rf_power
        diff_fan_power = cur_power * (afr_ratio ** 2.5) # fan laws
        
        self.ts_data += np.concatenate([arr.flatten() for arr in diff_fan_power]).tolist() # log 
        self.ts_header += ['fan power for lo SAT', 'fan power for cur SAT', ' fan power for hi SAT', ] # log
        
        fan_power_delta = diff_fan_power - cur_power
        
        self.estimations['fan_power_delta_' + self.ahu_name] = fan_power_delta
        self.estimations['fan_power_delta'] += fan_power_delta
            
        # Chilled water temp change and power for each AHU under different SAT setpoints
        # estimate the inherent temperature change between in & out temperature    
        if self.ccv == 0: 
            # valve closed during look-back window
            if self.chw_coils_hist > 0:
                # update coil closed temp cahnge and return heat flow estimate of zero
                self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name] = ((self.cur_sat - self.mat)*0.01) + (0.99*self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name])
            
            # update trend/hist values
            self.estimations['chw_coils_hist_' + self.ahu_name]  = 1
            self.estimations['chw_power_delta_' + self.ahu_name] = np.zeros(len(diff_sat))
            
            self.ts_data += [0, 0, 0] # log 
            self.ts_header += [' chw power for lo SAT', ' chw power for cur SAT', ' chw power for hi SAT', ] # log
            
        else:
            # return heat flow estimate for each candidate sat
            # include predicted change in total airflow at each sat       
            # cur temp difference based on cur sat
            curr_ahu_temp = cur_sat_sp - self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name] - self.mat
            curr_chw_power = np.maximum(0.0, -self.calc_heat_flow(afr, curr_ahu_temp))
            
            diff_ahu_temp = cur_sat_sp + diff_sat - self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name] - self.mat
            
            # clg coil power
            diff_chw_power = np.maximum(0.0, -self.calc_heat_flow(afr + diff_afr, diff_ahu_temp))           
            self.ts_data += np.concatenate([arr.flatten() for arr in diff_chw_power]).tolist() # log 
            self.ts_header += [' chw power for lo SAT', ' chw power for cur SAT', ' chw power for hi SAT', ] # log
            
            # update trend/hist values
            self.estimations['chw_coils_hist_' + self.ahu_name] = 1
            self.estimations['chw_power_delta'] = diff_chw_power - curr_chw_power

        self.estimations['diff_sat'] = diff_sat
    
    def log_data(self, newdata, ahu_data_AV, new_ahu_data_AV):
        var_in_csv = newdata[3]
        if not any(var_in_csv in item for item in ahu_data_AV['Object_Name']):
            new_nparry = np.array([newdata], dtype=new_ahu_data_AV.dtype)                                                         
            new_ahu_data_AV = np.append(new_ahu_data_AV, new_nparry)
            
        else:
            idx_find = [np.char.find(ahu_data_AV['Object_Name'], var_in_csv)>=0][0]
            new_ahu_data_AV['Present_Value'][idx_find] = newdata[-2]
        
        return new_ahu_data_AV
        
    def calc_heat_flow(self, volumetric_flow,delta_temperature):
        rho = 1.2005 # density of air @ 20degC [Unit: kg/m^3]
        c = 1005 # specific heat capacity of air @ 20degC 
        return volumetric_flow * delta_temperature * c * rho / 1.8 / 2118.88 / 1000  # [Unit: kW] 
    
    # get new air flow rate for different SATs
    def calc_diff_zone_afr(self, reheat_pos, cur_sat, diff_sat, afr, hg_sp, clg_sp, room_temp, afr_min, afr_max, clg):      
        # heating or deadband
        # CHECK REHEAT POS RANGE/VALUE 
        if (reheat_pos > 20) or (hg_sp <= room_temp <= clg_sp) or (clg < 0.1):
            diff_zone_afr = np.zeros(len(diff_sat)) 
            
        # cooling
        else:
            afr = np.minimum(np.maximum(afr, afr_min), afr_max)
            
            ### actual deltaT vs assumed deltaT to be checked later
            new_zone_afr = afr * (clg_sp - cur_sat - 2) / (clg_sp - (cur_sat + diff_sat) - 2)
            new_zone_afr = np.minimum(np.maximum(new_zone_afr, afr_min), afr_max)

            if 0.1 < clg < 99.9:
                diff_zone_afr = new_zone_afr - afr
                
            elif 99.9 <= clg <= 100:
                if room_temp > clg_sp:
                    # zone way past capacity, afr will not change regardless of sat
                    diff_zone_afr = np.zeros(len(diff_sat))
                else:
                    # zone at capacity, afr can only decrease, no further increase possible
                    diff_zone_afr = np.minimum(afr, new_zone_afr) - afr
            
        if np.any(np.isnan(diff_zone_afr)):
            print('issue encountered in calc_diff_zone_afr()')
            print('new_zone_afr:%s'%new_zone_afr)
            print('diff_zone_afr:%s'%diff_zone_afr)
            print('cur_sat=%s, diff_sat=%s, afr=%s, cur_temp_sp=%s, room_temp=%s, afr_min=%s, afr_max=%s, clg=%s'%(cur_sat, diff_sat, afr, clg_sp, room_temp, afr_min, afr_max, clg))
            diff_zone_afr = np.zeros(len(diff_sat))
        
        return diff_zone_afr  
    
    def save_data_bydate(self, data2save, header, folder_dir, ahu_name):
        # get the current date to name the file
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = os.path.join(self.folder_dir, 'log', self.ahu_name, f"CORE{self.core_version}_{self.ahu_name}_{date_str}.csv" )
        
        # create the CSV file if it doesn't exist
        if not os.path.exists(filename):
            # create nested folders
            os.makedirs(os.path.join(self.folder_dir, 'log', self.ahu_name), exist_ok=True)
            with open(filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                header.insert(0, 'TimeStamp')
                writer.writerow(header)
    
        # save data with the current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        with open(filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            data2save.insert(0, timestamp)
            writer.writerow(data2save)
    
    def cal_dew_point_temperature(self, T_F, RH):
        # constants for the August-Roche-Magnus approximation
        a = 17.625
        b = 243.04
        # convert temperature from Fahrenheit to Celsius
        T_C = (T_F - 32) / 1.8
        # calculate the dew point temperature in Celsius
        alpha = np.log(RH / 100.0) + (a * T_C) / (b + T_C)
        T_dew_C = (b * alpha) / (a - alpha)
        # convert dew point temperature back to Fahrenheit
        T_dew_F = T_dew_C * 1.8 + 32
        
        return T_dew_F
    
    def calc_sp_limit(self, current_oat, lo_oat, hi_oat, val_at_lo_oat, val_at_hi_oat):
      # calculate the 
      if current_oat <=lo_oat:        
        rv = val_at_lo_oat
      elif current_oat >= hi_oat:
        rv = val_at_hi_oat
      else:
        # linearly interpolate
        val_range = val_at_hi_oat-val_at_lo_oat
        oat_range = hi_oat-lo_oat
        rv = val_at_lo_oat +  val_range *(current_oat-lo_oat)/oat_range
        
      return rv      
