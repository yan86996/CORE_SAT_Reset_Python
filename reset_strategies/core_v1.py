import os, sys, glob
import datetime as dt
import csv
import time
from datetime import datetime
import numpy as np
from util_rate import electricity_price, steam_price
import pdb 
#######
### Changes to V1 
### Add Heating Request to AHU power estimation
#######

class CORE:
    def __init__(self, algo=None, core_version=None, max_off_time=None, dehumid=None, folder_dir=None, dehumd_limits=None, g36_sat=None, zone_dev_map=None, zone_names=None, 
                 ahu_name=None, vdf_dev_map=None, ahu_dev_map=None, pump_dev_map=None, zone_requests=None, reset=None, num_ignore_clg=None, num_ignore_htg=None, diff_sat=None,                              
                 ):
        self.algo = algo
        self.core_version = core_version
        self.dehumid = dehumid
        self.g36_sat = g36_sat
        self.folder_dir = folder_dir
        self.vdf_dev_map = vdf_dev_map
        self.pump_dev_map = pump_dev_map
        self.max_off_time = max_off_time
        # hw pump power
        self.hw_pumps_power = []
        # cw pump power
        self.cw_pumps_power = []
        # sat changes
        self.diff_sat = np.asarray(diff_sat)
        
        # log data2save for each timestamp
        self.ts_data = []
        self.ts_header = []
        
        # cooling requests
        self.clg_requests = zone_requests[0]        
        
        # heating requests
        self.htg_requests = zone_requests[1]
        
        # reset is an instantiated reset object
        self.reset = reset
        
        # min/max sat
        self.min_sat_sp = self.reset.SPmin
        self.max_sat_sp = self.reset.SPmax
        
        self.num_ignore_clg = num_ignore_clg
        self.num_ignore_htg = num_ignore_htg
        
        self.vavs = zone_names
        self.flow_min = 'Minimum Airflow Setpoint'
        self.flow_max = 'Maximum Airflow Setpoint'
        self.zone_dev_map = zone_dev_map
        self.satsp_name = 'Supply Air Setpoint'
        self.dehumd_limits = dehumd_limits
              
        # get AHU data
        self.ahu_name = ahu_name
        self.ahu_dev_ID = ahu_dev_map[ahu_name]
        
        # init estimations
        self.chw_coils_hist = 0
        self.estimations = {}
        self.rhv_coils_hist = {}
        
    def read_ahu_csvs(self):
        # from AV_XXXX.csv
        try:
            ahu_csv_AV = os.path.join(self.folder_dir, f'AV_{self.ahu_dev_ID}.csv')
            ahu_data_AV = np.genfromtxt(ahu_csv_AV, delimiter=',', dtype=None, names=True, encoding='utf-8')
            
            self.ahu_data_AV = ahu_data_AV
            self.ahu_data_AV_header = ahu_data_AV.dtype.names
            
            # cur sat setpoint
            self.cur_satsp = ahu_data_AV['Present_Value'][np.char.find(ahu_data_AV['Object_Name'], self.satsp_name) >= 0][0]
            self.ts_data.append(self.cur_satsp) # log
            self.ts_header.append('cur SAT setpoint') # log
            
            # cur rat setpoint
            cur_ratsp = ahu_data_AV['Present_Value'][np.char.find(ahu_data_AV['Object_Name'], 'Return Air Setpoint') >= 0][0]
            self.ts_data.append(cur_ratsp) # log
            self.ts_header.append('cur RAT setpoint') # log 
            
            # cur preheat temperature
            self.preheat_temp = ahu_data_AV['Present_Value'][np.char.find(ahu_data_AV['Object_Name'], 'Preheat Temperature') >= 0][0]
            self.ts_data.append(self.preheat_temp) # log
            self.ts_header.append('Preheat Temperature') # log
            
            # cur preheat temperature Setpoint
            self.preheat_setpoint = ahu_data_AV['Present_Value'][np.char.find(ahu_data_AV['Object_Name'], 'Preheat Setpoint') >= 0][0]
            self.ts_data.append(self.preheat_setpoint) # log
            self.ts_header.append('Preheat Setpoint') # log
            
            # cur oat
            self.cur_oat = ahu_data_AV['Present_Value'][np.char.find(ahu_data_AV['Object_Name'], 'Outside Air Temperature') >= 0][0]
            self.ts_data.append(self.cur_oat) # log
            self.ts_header.append('outdoor temp') # log   
            
            # cur oa rh
            cur_oarh = ahu_data_AV['Present_Value'][np.char.find(ahu_data_AV['Object_Name'], 'Outside Air Humidity') >= 0][0]
            self.ts_data.append(cur_oarh) # log
            self.ts_header.append('outdoor air RH') # log
            
            # cal oa dewpoint
            self.cur_oa_dpwt = self.cal_dew_point_temperature(self.cur_oat, cur_oarh)
            self.ts_data.append(self.cur_oa_dpwt) # log
            self.ts_header.append('calculated outdoor air dewpoint') # log
            
        except Exception as e:
            print(e)
            print(f'Failed to find AV_{self.ahu_dev_ID}.csv')
       
        # from AI_XXXX.csv
        try:
            ahu_csv_AI = os.path.join(self.folder_dir, f'AI_{self.ahu_dev_ID}.csv')
            ahu_data_AI = np.genfromtxt(ahu_csv_AI, delimiter=',', dtype=None, names=True, encoding='utf-8')
            
            # cur sat
            self.cur_sat = ahu_data_AI['Present_Value'][np.char.find(ahu_data_AI['Object_Name'], 'Supply Air Temperature') >= 0][0] 
            self.ts_data.append(self.cur_sat) # log
            self.ts_header.append('cur SAT') # log
                  
            # mat
            self.mat = ahu_data_AI['Present_Value'][np.char.find(ahu_data_AI['Object_Name'], 'Mixed Air Temperature') >= 0][0]
            self.ts_data.append(self.mat) # log 
            self.ts_header.append('MAT') # log
            
            # rat
            rat = ahu_data_AI['Present_Value'][np.char.find(ahu_data_AI['Object_Name'], 'Return Air Temperature') >= 0][0]
            self.ts_data.append(rat) # log
            self.ts_header.append('RAT') # log
            
            # supply air RH
            sa_rh = ahu_data_AI['Present_Value'][np.char.find(ahu_data_AI['Object_Name'], 'Supply Air Humidity') >= 0][0]       
            self.ts_data.append(sa_rh) # log
            self.ts_header.append('supply air RH') # log
            
            # mixed air RH
            ma_rh = ahu_data_AI['Present_Value'][np.char.find(ahu_data_AI['Object_Name'], 'Mixed Air Humidity') >= 0][0]       
            self.ts_data.append(ma_rh) # log
            self.ts_header.append('mixed air RH') # log
            
            # return air RH
            ra_rh = ahu_data_AI['Present_Value'][np.char.find(ahu_data_AI['Object_Name'], 'Return Air Humidity') >= 0][0]       
            self.ts_data.append(ra_rh) # log
            self.ts_header.append('return air RH') # log
            
        except Exception as e:
            print(e)
            print(f'Failed to find AI_{self.ahu_dev_ID}.csv')
            
        # from AO_XXXX.csv
        # clg coil valve
        try:
            ahu_csv_AO = os.path.join(self.folder_dir, f'AO_{self.ahu_dev_ID}.csv')
            ahu_data_AO = np.genfromtxt(ahu_csv_AO, delimiter=',', dtype=None, names=True, encoding='utf-8')
            
            # clg coil valve 
            self.ccv = ahu_data_AO['Present_Value'][np.char.find(ahu_data_AO['Object_Name'], 'Chilled Water Control Valve') >= 0][0]
            self.ts_data.append(self.ccv) # log 
            self.ts_header.append('chilled water control valve') # log
            
            # htg coil valve 
            self.hcv = ahu_data_AO['Present_Value'][np.char.find(ahu_data_AO['Object_Name'], 'Steam Coil 1 Control Valve') >= 0][0]
            self.ts_data.append(self.hcv) # log 
            self.ts_header.append('steam coil 1 control valve') # log
            
            # htg coil valve 2
            self.hcv2 = ahu_data_AO['Present_Value'][np.char.find(ahu_data_AO['Object_Name'], 'Steam Coil 2 Control Valve') >= 0][0]
            self.ts_data.append(self.hcv2) # log 
            self.ts_header.append('steam coil 2 control valve') # log
            
            # oa damper
            self.oa_damper = ahu_data_AO['Present_Value'][np.char.find(ahu_data_AO['Object_Name'], 'Outside Air Damper') >= 0][0]
            self.ts_data.append(self.oa_damper) # log
            self.ts_header.append('outside air damper') # log
            
            # vfd %
            vfds = ahu_data_AO['Object_Name'][np.char.find(ahu_data_AO['Object_Name'], 'VFD Speed') >= 0]
            for vfd in vfds:
                vfd_name = vfd.replace('140W62nd - ', '')
                vdf_speed = ahu_data_AO['Present_Value'][np.char.find(ahu_data_AO['Object_Name'], vfd_name) >= 0][0]
                self.ts_data.append(vdf_speed) # log
                self.ts_header.append(vfd_name + '(%)') # log
                
        except Exception as e:
            print(e)
            print(f'Failed to find AO_{self.ahu_dev_ID}.csv')
    
    def read_ahu_mode(self):
        # from MV_XXXX.csv
        try:
            ahu_csv_MV = os.path.join(self.folder_dir, f'MV_{self.ahu_dev_ID}.csv')
            ahu_data_MV = np.genfromtxt(ahu_csv_MV, delimiter=',', dtype=None, names=True, encoding='utf-8')
            
            # ahu status
            self.ahu_status = ahu_data_MV['Present_Value'][np.char.find(ahu_data_MV['Object_Name'], 'Unit Status') >= 0][0] 
            self.ts_data.append(self.ahu_status) # log
            self.ts_header.append('ahu status') # log
            
            # ahu mode
            self.ahu_mode = ahu_data_MV['Present_Value'][np.char.find(ahu_data_MV['Object_Name'], 'Unit Mode') >= 0][0] 
            self.ts_data.append(self.ahu_mode) # log
            self.ts_header.append('ahu mode') # log
        
        except Exception as e:
            print(e)
            print(f'Failed to find MV_{self.ahu_dev_ID}.csv')
            self.ts_data.append(np.nan) # log
            self.ts_header.append('ahu mode') # log
            
    def read_vfd_power_csvs(self):
        # vfd power (TO CHANGE)
        vfd_dev_ID = self.vdf_dev_map[self.ahu_name] 
        vfd_sf_power = 0
        vfd_rf_power = 0
        
        for key, value in vfd_dev_ID.items():
            csv_AV = os.path.join(self.folder_dir, 'AV_3050090.csv')
            # get supply fan(s)
            if 'SF' in key.upper():
                try:
                    sf_data_AV = np.genfromtxt(csv_AV, delimiter=',', dtype=None, names=True, encoding='utf-8')
                    
                    # power
                    sf_power = sf_data_AV['Present_Value'][np.char.find(sf_data_AV['Object_Name'], value+'_POWER') >= 0][0]
                    vfd_sf_power += sf_power
                    self.ts_data.append(sf_power) # log
                    self.ts_header.append(self.ahu_name + ' ' + key + ' power(kW) ') # log
                    
                    # speed rpm
                    sf_speed = sf_data_AV['Present_Value'][np.char.find(sf_data_AV['Object_Name'], value+'_SPEED') >= 0][0]
                    self.ts_data.append(sf_speed) # log
                    self.ts_header.append(self.ahu_name + ' ' + key + ' speed(RPM) ') # log
                    
                except Exception as e:
                    print(e)
            
            # get return fan(s)
            if 'RF' in key.upper():
                try:
                    rf_data_AV = np.genfromtxt(csv_AV, delimiter=',', dtype=None, names=True, encoding='utf-8')
                    
                    # power
                    rf_power = rf_data_AV['Present_Value'][np.char.find(rf_data_AV['Object_Name'], value+'_POWER') >= 0][0]
                    
                    if self.ahu_name == 'AHU_6':
                        rf_power *= 2.5 
                    
                    vfd_rf_power += rf_power

                    self.ts_data.append(rf_power) # log
                    self.ts_header.append(self.ahu_name + ' ' + key + ' power(kW) ') # log
                    
                    # speed rpm
                    rf_speed = rf_data_AV['Present_Value'][np.char.find(sf_data_AV['Object_Name'], value+'_SPEED') >= 0][0]
                    self.ts_data.append(rf_speed) # log
                    self.ts_header.append(self.ahu_name + ' ' + key + ' speed(RPM) ') # log
       
                except Exception as e:
                    print(e)
                    
        self.vfd_sf_power = vfd_sf_power  # KW
        self.vfd_rf_power = vfd_rf_power  # KW
        
    def read_hist_vars_csvs(self):    
       # check if logging var in AV_3050090.csv
        log_AV_csv = os.path.join(self.folder_dir, 'AV_3050090.csv')
                
        if os.path.isfile(log_AV_csv):
            log_data_AV = np.genfromtxt(log_AV_csv, delimiter=',', dtype=None, names=True, encoding='utf-8')          
            
            # check if chw_coils_hist already exists
            if ('chw_coils_hist_'+ self.ahu_name) not in log_data_AV['Object_Name']:
                self.chw_coils_hist = 0
                self.ts_data.append(-2) # log 
            else:
                self.chw_coils_hist = log_data_AV['Present_Value'][np.char.find(log_data_AV['Object_Name'], 'chw_coils_hist_'+ self.ahu_name) >= 0][0]
                self.ts_data.append(self.chw_coils_hist) # log 
            
            self.ts_header.append('chw_coils_hist from AV_3050090') # log
                        
            # check if clg_coil_clo_temp_chg already exists
            if ('clg_coil_clo_temp_chg_'+self.ahu_name) not in log_data_AV['Object_Name']:
                self.estimations['clg_coil_clo_temp_chg_'+self.ahu_name] = 2
                self.ts_data.append(-2) # log 
            else:
                self.estimations['clg_coil_clo_temp_chg_'+self.ahu_name] = log_data_AV['Present_Value'][np.char.find(log_data_AV['Object_Name'], 'clg_coil_clo_temp_chg_'+ self.ahu_name) >= 0][0]
                self.ts_data.append(self.estimations['clg_coil_clo_temp_chg_'+self.ahu_name]) # log 
            
            self.ts_header.append('clg_coil_clo_temp_chg from AV_3050090') # log
                                        
        else:
            # update clg coil hist and temp_change_when_closed
            self.chw_coils_hist = 0
            self.ts_data.append(-1) # log 
            self.ts_header.append('chw_coils_hist from AV_3050090') # log
            
            self.estimations['clg_coil_clo_temp_chg_'+self.ahu_name] = 2
            self.ts_data.append(-1) # log 
            self.ts_header.append('clg_coil_clo_temp_chg from AV_3050090') # log
            
            print('NO clg_coil_clo_temp_chg from AV_3050090, and default values used')
        
    def read_pump_power_csvs(self):
        for key, value in self.pump_dev_map.items():
            try:
                pump_csv = os.path.join(self.folder_dir, 'AV_3050090.csv')        
                pump_data_AV = np.genfromtxt(pump_csv, delimiter=',', dtype=None, names=True, encoding='utf-8')
                pump_power = pump_data_AV['Present_Value'][np.char.find(pump_data_AV['Object_Name'], value) >= 0][0]
            
            except Exception as e:
                print(e)
                print(f'******* Failed to read pump power csvs for {self.ahu_name} *******')
                pump_power = np.nan
            
            self.ts_data.append(pump_power) # log 
            self.ts_header.append(key + ' power(kW)') # log
                
            if value in ['HWP_1_POWER', 'HWP_2_POWER']:
                self.hw_pumps_power.append(pump_power)
            
            if value in ['CWP_1_POWER', 'CWP_2_POWER', 'CWP_3_POWER', 'CWP_4_POWER', 'CWP_5_POWER', ]:
                self.cw_pumps_power.append(pump_power)
        
    def get_last_good_SAT(self):
        folder_path = os.path.join(self.folder_dir, 'log', self.ahu_name)
        csv_files = glob.glob(os.path.join(folder_path, '*.csv'))
        # sort files by modification time (most recent first)
        csv_files.sort(key=os.path.getmtime, reverse=True)
        
        now = datetime.now()
        if now.hour > 1:
            lastest_file = csv_files[0]
        else:
            try:
                lastest_file = csv_files[1] # get yesteday's csv        
            except Exception as e:
                print(e)
                print('no csv from yesteday')
                    
        last_CORE_row = None
        with open(lastest_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:                
                if row['core finished'] != '-1':
                    last_CORE_row = row
        
        # CORE
        last_CORE_SAT = last_CORE_row['CORE satsp']
        last_CORE_time = last_CORE_row['TimeStamp']
        dt_CORE = datetime.strptime(last_CORE_time, '%Y-%m-%d %H:%M')
        time_CORE_lapesd = (now - dt_CORE).total_seconds()/3600
            
        return last_CORE_SAT, time_CORE_lapesd
        
    ######
    ### zone temp montioring 
    ######
    def find_bad_zones(self, zone_temp_dev, zone_temp_lo, zone_temp_hi, sat_lo, sat_hi):
        # bad zones: (2 degrees wider than htg/clg setpoint) or (below 65 or above 78F)
        bad_zones = []     
        # loop through each zone vav box
        for vav in self.vavs:
            div_ID = self.zone_dev_map[vav]
            
            # from AV_XXXX.csv
            try:
                zone_csv_AV = os.path.join(self.folder_dir, f'AV_{div_ID}.csv')
                zone_data_AV = np.genfromtxt(zone_csv_AV, delimiter=',', dtype=None, names=True, encoding='utf-8')
            except Exception as e:
                print(e)
                print(f'Failed to find AV_{div_ID}.csv') 
                
            # heating setpoint
            htg_sp = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'Heating Setpoint') >= 0][0]
            
            # cooling setpoint
            clg_sp = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'Cooling Setpoint') >= 0][0]             
            
            # room temp
            room_temp = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'Space Temperature') >= 0][0]        
            
            # vav status from controller
            vav_status = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'VAV Status Value') >= 0][0]  

            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            # zone temp monitoring
            # 5F (default) wider than the htg - clg setpoint range
            if (room_temp < htg_sp - zone_temp_dev) or (room_temp > clg_sp + zone_temp_dev):
                bad_zones.append(f'look into {vav}: zone temp is {room_temp}F at {now}, {zone_temp_dev}F wider than the heating {htg_sp}F - cooling {clg_sp}F setpoint range')
            # below zone_temp_lo (such as 65) or above zone_temp_lo (such as 78F)
            elif (room_temp <zone_temp_lo) or (room_temp > zone_temp_hi):
                bad_zones.append(f'look into {vav}: zone temp is {room_temp}F at {now}, below {zone_temp_lo}F or above {zone_temp_hi}F')             
                    
        # sat or sat setpoint not in 55-65F
        if (self.cur_sat < sat_lo) or (self.cur_sat > sat_hi):
            bad_zones.append(f'the SAT OF {self.ahu_name} at {now} is {self.cur_sat}, not within {sat_lo}-{sat_hi}F')
        
        if (self.cur_satsp < sat_lo) or (self.cur_satsp > sat_hi):
            bad_zones.append(f'the SAT setpoint OF {self.ahu_name} at {now} is {self.cur_sat}, not within {sat_lo}-{sat_hi}F')
            
        return bad_zones

    def get_new_satsp(self):
        # get the last good SAT values and time
        try:
            last_CORE_SAT, time_CORE_lapesd = self.get_last_good_SAT()
        except Exception as e:
            print(e)
            print(f'******* Cannot get the last good SAT values for {self.ahu_name} *******')
        
        # reset SAT
        try:
            # read AHU data
            try:
                self.read_ahu_csvs()
            except Exception as e:
                print(e)
                print(f'Cannot read AHU data for {self.ahu_name}')
                sys.exit(1)
            
            self.ts_data.append(self.min_sat_sp) # log
            self.ts_header.append('min SAT') # log
            self.ts_data.append(self.reset.SPmax) # log
            self.ts_header.append('max SAT') # log
                        
            # update cooling requests
            self.clg_requests.update()
            self.ts_data.append(self.clg_requests.R_clg) # log
            self.ts_header.append('number of cooling requests') # log
            
            # update heating requests
            self.htg_requests.update()
            self.ts_data.append(self.htg_requests.R_htg) # log
            self.ts_header.append('number of heating requests') # log
            
            # G36 algo finished
            if self.g36_sat == np.nan:
                g36_finish = -1
                # default to the baseline control
                if self.algo == 1:
                    self.algo = 0
                    print('******* Default to baseline control *******')
                
            else:
                g36_finish = 1
                
            self.ts_data.append(g36_finish) # log 
            self.ts_header.append('g36 finished') # log
            
            new_ahu_data_AV = self.ahu_data_AV.copy()
            
            # write G36 new sat setpoint
            if self.algo == 1:
                algo_finish = g36_finish
                idx_find = [np.char.find(self.ahu_data_AV['Object_Name'], self.satsp_name)>=0][0]
                new_ahu_data_AV['Present_Value'][idx_find] = self.g36_sat
                print(f'# G36 picked for today: the new SAT setpoint for {self.ahu_name} is {round(self.g36_sat,2)}°F')
               
            ### logging data before running CORE
            # algo num
            algo_array = ('3050090', 'analog-value', '9999999', 'algo to choose for ' + self.ahu_name, self.algo,'/')
            new_ahu_data_AV = self.log_data(algo_array, self.ahu_data_AV, new_ahu_data_AV)
            self.ts_data.append(self.algo) # log 
            self.ts_header.append('algo number') # log
            
            # G36 SAT setpoint
            g36_satsp_array = ('3050090', 'analog-value', '9999999', 'G36 satsp ' + self.ahu_name, self.g36_sat,'°F')
            new_ahu_data_AV = self.log_data(g36_satsp_array, self.ahu_data_AV, new_ahu_data_AV)
            
            # write to AV_.csv before running CORE calculations
            overwrite_csv = os.path.join(self.folder_dir, f'AV_{self.ahu_dev_ID}_out.csv')
            with open(overwrite_csv, "w", encoding='utf-8') as f:
                np.savetxt(f, new_ahu_data_AV, header=','.join(self.ahu_data_AV_header), delimiter=",", fmt='%s')
                
            # read VFD data
            try:
                self.read_vfd_power_csvs()
            except Exception as e:
                print(e)
                print(f'******* Cannot run CORE calculations due to failure to read VFD data for {self.ahu_name} *******')
                sys.exit(1)
                
            # read hist vars
            self.read_hist_vars_csvs()
            
            # read and log HW and CHW pump power data
            self.read_pump_power_csvs()
            
            # read ahu mode data
            self.read_ahu_mode()
            
            #  initialize cost estimates
            self.estimations['chw_cost_delta_G36'] = np.full(3, np.nan)
            self.estimations['rhv_cost_delta_G36'] = np.full(3, np.nan)
            self.estimations['fan_cost_delta_G36'] = np.full(3, np.nan)
            self.estimations['tot_cost_delta_G36'] = np.full(3, np.nan)
            self.estimations['diff_zone_tot_afr_G36'] = np.full(3, np.nan)
            
            self.estimations['chw_cost_delta'] = np.full(3, np.nan)
            self.estimations['rhv_cost_delta'] = np.full(3, np.nan)
            self.estimations['fan_cost_delta'] = np.full(3, np.nan)
            self.estimations['tot_cost_delta'] = np.full(3, np.nan)
            self.estimations['diff_zone_tot_afr'] = np.full(3, np.nan)
            
            # util rate
            elec_pr = electricity_price(datetime.now())              
            steam_pr = steam_price(datetime.now()) 
            
            # humidity constrain
            humd_SPmax = np.nan
                
            # run CORE calculations
            try:
                # estimate power consumption values under different setpoints for CORE
                # calculate the feasible range of diff_sat
                candidate_sat = self.diff_sat + self.cur_satsp
                # sat setpoint range check
                candidate_sat = np.where(candidate_sat > self.max_sat_sp, self.max_sat_sp, candidate_sat)
                candidate_sat = np.where(candidate_sat < self.min_sat_sp, self.min_sat_sp, candidate_sat)
                diff_sat = candidate_sat - self.cur_satsp

                # heating request
                if self.htg_requests.R_htg > self.num_ignore_htg:                 
                    # use trim and respond without outside air based SAT setpoint limits
                    new_core_sat = self.reset.get_new_sp_htg(self.htg_requests.R_htg, self.cur_satsp)
                    core_finish = 2
                    print(f'###### SAT reset to {round(new_core_sat,2)} for {self.ahu_name} for heating requests ######')
                    
                    self.estimate_power(self.cur_satsp, diff_sat)
                    
                    # ΔPchw_lower, 0, ΔPchw_higher = self.estimations['chw_power_delta']
                    # ΔPc_lower,   0, ΔPc_higher = self.estimations['chw_power_delta']/0.7
                    # ΔCcool_lower, 0, ΔCcool_higher = self.estimations['chw_cost_delta']
                    self.estimations['chw_cost_delta'] = self.estimations['chw_power_delta']/12000 *18 *steam_pr # 0.7 COP = 18 lbs/ ton of clg
                    
                    # ΔPfan_lower, 0, ΔPfan_higher = self.estimations['fan_power_delta']
                    # ΔCfan_lower, 0, ΔCfan_higher = self.estimations['fan_cost_delta']
                    self.estimations['fan_cost_delta'] = self.estimations['fan_power_delta'] * elec_pr
                    
                    # ΔPhhw_lower, 0, ΔPhhw_higher = self.estimations['rhv_power_delta']
                    # ΔPh_lower, 0, ΔPh_higher = self.estimations['rhv_power_delta']/0.9
                    # ΔCheat_lower, 0, ΔCheat_higher = self.estimations['rhv_cost_delta']
                    
                    self.estimations['rhv_cost_delta'] = self.estimations['rhv_power_delta']/0.9 /950 *steam_pr  # steam (950 BTU/lb)
                    
                    # ΔC_lower, 0, ΔC_higher = self.estimations['tot_cost_delta']
                    self.estimations['tot_cost_delta'] = self.estimations['chw_cost_delta'] + self.estimations['rhv_cost_delta'] + self.estimations['fan_cost_delta']       
                    
                else:
                    if self.dehumid:
                        lo_oa_dwpt, hi_oa_dwpt, spmax_at_lo_oat_dwpt, spmax_at_hi_oat_dwpt = self.dehumd_limits
                        humd_SPmax = self.calc_sp_limit(self.cur_oa_dpwt, lo_oa_dwpt, hi_oa_dwpt, spmax_at_lo_oat_dwpt, spmax_at_hi_oat_dwpt)
                        
                        # if dehumidification requires a step-change of over 1F
                        humd_SPmax_adjust = max(self.cur_satsp - 1, humd_SPmax)
                            
                        self.max_sat_sp = min(self.max_sat_sp, humd_SPmax_adjust)
                        self.reset.SPmax = self.max_sat_sp
                    
                        # sat setpoint range check considering dehumidificaiton
                        candidate_sat = np.where(candidate_sat > self.max_sat_sp, self.max_sat_sp, candidate_sat)
                        diff_sat = candidate_sat - self.cur_satsp
                    
                    # estimate power consumption values under different setpoints for CORE
                    self.estimate_power(self.cur_satsp, diff_sat)
                    
                    # ΔPchw_lower, 0, ΔPchw_higher = self.estimations['chw_power_delta']
                    # ΔPc_lower,   0, ΔPc_higher = self.estimations['chw_power_delta']/0.7
                    # ΔCcool_lower, 0, ΔCcool_higher = self.estimations['chw_cost_delta']
                    self.estimations['chw_cost_delta'] = self.estimations['chw_power_delta']/12000 *18 *steam_pr # 0.7 COP = 18 lbs/ ton of clg
                                        
                    # ΔPfan_lower, 0, ΔPfan_higher = self.estimations['fan_power_delta']
                    # ΔCfan_lower, 0, ΔCfan_higher = self.estimations['fan_cost_delta']
                    self.estimations['fan_cost_delta'] = self.estimations['fan_power_delta'] * elec_pr
                    
                    # ΔPhhw_lower, 0, ΔPhhw_higher = self.estimations['rhv_power_delta']
                    # ΔPh_lower, 0, ΔPh_higher = self.estimations['rhv_power_delta']/0.9
                    # ΔCheat_lower, 0, ΔCheat_higher = self.estimations['rhv_cost_delta']               
                    self.estimations['rhv_cost_delta'] = self.estimations['rhv_power_delta']/0.9 /950 *steam_pr  # steam (950 BTU/lb)
                    
                    # ΔC_lower, 0, ΔC_higher = self.estimations['tot_cost_delta']
                    self.estimations['tot_cost_delta'] = self.estimations['chw_cost_delta'] + self.estimations['rhv_cost_delta'] + self.estimations['fan_cost_delta']
                    
                    # cooling request
                    if self.clg_requests.R_clg > self.num_ignore_clg:
                        # use trim and respond without outside air based SAT setpoint limits
                        new_core_sat = self.reset.get_new_sp_clg(self.clg_requests.R_clg, self.cur_satsp)
                        core_finish = 3
                        print(f'###### SAT reset to {round(new_core_sat,2)} for {self.ahu_name} for cooling requests ######')
                        
                    # no comfort present
                    # run CORE algorithm
                    else:
                        print(f'###### No comofort request, CORE runs for {self.ahu_name} ######')                                      
                        idx_opt = np.argmin(self.estimations['tot_cost_delta'])                   
                        new_core_sat = self.cur_satsp + diff_sat[idx_opt]
                        
                        core_finish = 1
                
                # print(f"ΔPfan_lower : {self.estimations['fan_power_delta'][0]}")
                # print(f"ΔPfan_higher : {self.estimations['fan_power_delta'][-1]}")
                # print(f"ΔCfan_lower : {self.estimations['fan_cost_delta'][0]}")
                # print(f"ΔCfan_higher : {self.estimations['fan_cost_delta'][-1]}")
                
                # print(f"ΔPchw_lower : {self.estimations['chw_power_delta'][0]}")
                # print(f"ΔPchw_higher : {self.estimations['chw_power_delta'][-1]}")
                # print(f"ΔPc_lower : {self.estimations['chw_power_delta'][0]/0.7}")
                # print(f"ΔPc_higher : {self.estimations['chw_power_delta'][-1]/0.7}")
                # print(f"ΔCcool_lower : {self.estimations['chw_cost_delta'][0]}")
                # print(f"ΔCcool_higher : {self.estimations['chw_cost_delta'][-1]}")        
                
                # print(f"ΔPhhw_lower : {self.estimations['rhv_power_delta'][0]}")
                # print(f"ΔPhhw_higher : {self.estimations['rhv_power_delta'][-1]}")
                # print(f"ΔPh_lower : {self.estimations['rhv_power_delta'][0]/0.9}")
                # print(f"ΔPh_higher : {self.estimations['rhv_power_delta'][-1]/0.9}")
                # print(f"ΔCheat_lower : {self.estimations['rhv_cost_delta'][0]}")
                # print(f"ΔCheat_higher : {self.estimations['rhv_cost_delta'][-1]}")
                
                # print(f"ΔC_lower : {self.estimations['tot_cost_delta'][0]}")
                # print(f"ΔC_higher : {self.estimations['tot_cost_delta'][-1]}")
                    
                self.ts_data.append(humd_SPmax) # log
                self.ts_header.append('humd_SPmax') # log
                
                ## NOT USED FOR CORE 
                # calculate the feasible range of diff_sat for G36
                candidate_sat_g36 = self.diff_sat + self.g36_sat
                # if dehumidification requires a step-change of over 0.5F
                humd_SPmax_adjust_g36 = min(65, max(self.g36_sat - 1, humd_SPmax))
                # sat setpoint range check
                candidate_sat_g36 = np.where(candidate_sat_g36 > humd_SPmax_adjust_g36, humd_SPmax_adjust_g36, candidate_sat_g36)
                candidate_sat_g36 = np.where(candidate_sat_g36 < 55, 55, candidate_sat_g36)
                diff_sat_g36 = candidate_sat_g36 - self.g36_sat
                # estimate power consumption values under different setpoints for G36
                self.estimate_power_G36(self.g36_sat, diff_sat_g36)
                # update cost estimation for G36 but NOT used for SAT selection
                self.estimations['chw_cost_delta_G36'] = self.estimations['chw_power_delta_G36']/12000 *18 *steam_pr # 0.7 COP = 18 lbs/ ton of clg
                self.estimations['rhv_cost_delta_G36'] = self.estimations['rhv_power_delta_G36']/0.9 /950 *steam_pr  # steam (950 BTU/lb)
                self.estimations['fan_cost_delta_G36'] = self.estimations['fan_power_delta_G36'] * elec_pr
                self.estimations['tot_cost_delta_G36'] = self.estimations['chw_cost_delta_G36'] + self.estimations['rhv_cost_delta_G36'] + self.estimations['fan_cost_delta_G36']

            except Exception as e:
                print(e)
                if time_CORE_lapesd < self.max_off_time:
                    new_core_sat = last_CORE_SAT
                    print('******* CORE failed to run, and the last good SAT value was used *******')           
                else:
                    print('******* CORE failed to run for more than an hour *******')
                    new_core_sat = np.nan
                    # defalt to the baseline control
                    if self.algo == 2:
                        self.algo = 0
                    print('******* Default to baseline control *******')
                    
                core_finish = -1
            
            self.ts_data.append(new_core_sat) # log
            self.ts_header.append('new CORE SAT setpoint') # log
            self.ts_data.append(core_finish) # log
            self.ts_header.append('core finished') # log
                        
            ## write SAT setpoint back
            idx_find = [np.char.find(new_ahu_data_AV['Object_Name'], self.satsp_name)>=0][0]
            
            # write G36 new sat setpoint
            if self.algo == 1:
                algo_finish = g36_finish
                new_ahu_data_AV['Present_Value'][idx_find] = self.g36_sat
                print(f'# G36 picked for today: the new sat setpoint for {self.ahu_name} is {round(self.g36_sat,2)}°F')
                      
            # write CORE new sat setpoint 
            elif self.algo == 2:
                algo_finish = core_finish
                if algo_finish > 0:
                    algo_finish = 1
                new_ahu_data_AV['Present_Value'][idx_find] = new_core_sat
                print(f'# CORE picked for today: the new sat setpoint for {self.ahu_name} is {round(new_core_sat,2)}°F')         
            
            # default control used 
            else:
                algo_finish = np.nan
                print('# baseline control used')
                            
            # CORE/G36 finished
            algo_finish_array = ('3050090', 'analog-value', '9999999', 'picked algo finished for ' + self.ahu_name, algo_finish,'/')
            new_ahu_data_AV = self.log_data(algo_finish_array, self.ahu_data_AV, new_ahu_data_AV)
            self.ts_data.append(algo_finish) # log 
            self.ts_header.append('picked algo finished') # log
                            
            # CORE SAT setpoint
            core_satsp_array = ('3050090', 'analog-value', '9999999', 'CORE satsp ' + self.ahu_name, new_core_sat,'°F')
            new_ahu_data_AV = self.log_data(core_satsp_array, self.ahu_data_AV, new_ahu_data_AV)
            
            # AHU clg coil temp change 
            new_clgcoil_tempchg_data = ('3050090', 'analog-value', '9999999', 'clg_coil_clo_temp_chg_' + self.ahu_name, 
                                        self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name], '°F')
            new_ahu_data_AV = self.log_data(new_clgcoil_tempchg_data, self.ahu_data_AV, new_ahu_data_AV)
            
            # AHU clg coil hist
            new_clgcoil_hist = ('3050090', 'analog-value', '9999999', 'chw_coils_hist_' + self.ahu_name, self.chw_coils_hist, '/')
            new_ahu_data_AV = self.log_data(new_clgcoil_hist, self.ahu_data_AV, new_ahu_data_AV)
            
            # vav reheat coil
            # for vav in self.vavs:
            #     # reheat coil temp change
            #     new_rhv_tempchg_data = ('3050090', 'analog-value', '9999999', 'rhv_clo_temp_chg_' + vav, self.estimations['rhv_clo_temp_chg_' + vav], '°F')                                             
            #     new_ahu_data_AV = self.log_data(new_rhv_tempchg_data, self.ahu_data_AV, new_ahu_data_AV)            
            #     self.ts_data.append(self.estimations['rhv_clo_temp_chg_' + vav]) # log 
            #     self.ts_header.append('rhv_clo_temp_chg_' + vav) # log
                
            #     # reheat coil hist
            #     new_rhv_hist_data = ('3050090', 'analog-value', '9999999', 'rhv_coils_hist_' + vav, self.rhv_coils_hist['rhv_coils_hist_'+vav], '/')                  
            #     new_ahu_data_AV = self.log_data(new_rhv_hist_data, self.ahu_data_AV, new_ahu_data_AV)
            #     self.ts_data.append(self.rhv_coils_hist['rhv_coils_hist_'+vav]) # log 
            #     self.ts_header.append('rhv_coils_hist_' + vav) # log
            
            # write to AV_.csv
            overwrite_csv = os.path.join(self.folder_dir, f'AV_{self.ahu_dev_ID}_out.csv')
            with open(overwrite_csv, "w", encoding='utf-8') as f:
                np.savetxt(f, new_ahu_data_AV, header=','.join(self.ahu_data_AV_header), delimiter=",", fmt='%s')
            
            ###
            ## save time-series vars on a daily basis
            ###
            # CORE cal values
            core_cal_list = [candidate_sat, 
                             self.estimations['tot_cost_delta'],     self.estimations['chw_cost_delta'],     self.estimations['rhv_cost_delta'],     self.estimations['fan_cost_delta'],    self.estimations['diff_zone_tot_afr'],                              
                             self.estimations['tot_cost_delta_G36'], self.estimations['chw_cost_delta_G36'], self.estimations['rhv_cost_delta_G36'], self.estimations['fan_cost_delta_G36'],                                                                       
                            ]
            
            core_cal_list = np.concatenate([arr.flatten() for arr in core_cal_list]).tolist() 
            core_cal_list = [self.g36_sat, new_core_sat, self.core_version, 
                             self.estimations['clg_coil_clo_temp_chg_'+self.ahu_name], self.chw_coils_hist] + core_cal_list   
            
            core_cal_header = ['G36 satsp', 'CORE satsp', 'core_version',
                               'clg_coil_clo_temp_chg_'+self.ahu_name, 'chw_coils_hist_'+self.ahu_name,
                               # CORE scenario deltas
                               'candidate_sat_lo',     'candidate_sat',     'candidate_sat_hi', 
                               'tot_cost_delta_lo',    'tot_cost_delta',    'tot_cost_delta_hi',
                               'chw_cost_delta_lo',    'chw_cost_delta',    'chw_cost_delta_hi',
                               'rhv_cost_delta_lo',    'rhv_cost_delta',    'rhv_cost_delta_hi',
                               'fan_cost_delta_lo',    'fan_cost_delta',    'fan_cost_delta_hi',
                               'diff_zone_tot_afr_lo', 'diff_zone_tot_afr', 'diff_zone_tot_afr_hi',
                               # G36 scenario deltas
                               'tot_cost_delta_lo_G36',    'tot_cost_delta_G36',    'tot_cost_delta_hi_G36',
                               'chw_cost_delta_lo_G36',    'chw_cost_delta_G36',    'chw_cost_delta_hi_G36',
                               'rhv_cost_delta_lo_G36',    'rhv_cost_delta_G36',    'rhv_cost_delta_hi_G36',
                               'fan_cost_delta_lo_G36',    'fan_cost_delta_G36',    'fan_cost_delta_hi_G36',
                              ] 
    
            # combine all vars to save
            data2save = core_cal_list + self.ts_data
            header = core_cal_header + self.ts_header
            
            self.save_data_bydate(data2save, header, self.folder_dir, self.ahu_name)
                                
        except Exception as e:
            print(e)
            print('******* Failed to run CORE *******')
        
        print('-' * 80)
    
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
            try:
                zone_csv_AI = os.path.join(self.folder_dir, f'AI_{div_ID}.csv')
            except Exception as e:
                print(e)
                print(f'Failed to find AI_{div_ID}.csv')
            
            zone_data_AI = np.genfromtxt(zone_csv_AI, delimiter=',', dtype=None, names=True, encoding='utf-8')

            # discharge air temperature
            if any(np.char.find(zone_data_AI['Object_Name'], 'Supply Air Temperature') >= 0) :
                zone_dat = zone_data_AI['Present_Value'][np.char.find(zone_data_AI['Object_Name'], 'Supply Air Temperature') >= 0][0]
                if zone_dat < 0:
                    zone_dat = self.cur_sat
            else:
                zone_dat = self.cur_sat
                
            self.ts_data.append(zone_dat) # log
            self.ts_header.append(vav +' DAT') # log
            
            # airflow
            zone_afr = zone_data_AI['Present_Value'][np.char.find(zone_data_AI['Object_Name'], 'Airflow') >= 0][0]
            self.ts_data.append(zone_afr) # log
            self.ts_header.append(vav +' airflow rate') # log
            
            # total zone afr update
            afr += zone_afr       
            
            # from AV_XXXX.csv
            try:
                zone_csv_AV = os.path.join(self.folder_dir, f'AV_{div_ID}.csv')
                zone_data_AV = np.genfromtxt(zone_csv_AV, delimiter=',', dtype=None, names=True, encoding='utf-8')
            except Exception as e:
                print(e)
                print(f'Failed to find AV_{div_ID}.csv') 
            
            # min airflow
            try:
                afr_min = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], self.flow_min)>= 0][0]
            except Exception as e:
                print(e)
                print(f'Failed to find min airflow data in AV_{div_ID}.csv')
                
            self.ts_data.append(afr_min) # log 
            self.ts_header.append(vav +' min air flow rate') # log       
            
            # max airflow
            afr_max = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], self.flow_max) >= 0][0]         
            self.ts_data.append(afr_max) # log 
            self.ts_header.append(vav +' max air flow rate') # log
            
            # cooling loop 
            clg = (zone_afr - afr_min)/(afr_max - afr_min) * 100
            
            # heating setpoint
            htg_sp = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'Heating Setpoint') >= 0][0]
            self.ts_data.append(htg_sp) # log 
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
            
            # airflow setpoint
            zone_afr_sp = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'Airflow Setpoint') >= 0][0]
            self.ts_data.append(zone_afr_sp) # log
            self.ts_header.append(vav +' airflow setpoint') # log
            
            # damper position
            zone_afr_sp = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'Damper Position') >= 0][0]
            self.ts_data.append(zone_afr_sp) # log
            self.ts_header.append(vav +' damper position') # log
            
            # calculate AFR difference under different SAT setpoints
            vav_status = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'VAV Status Value') >= 0][0]  
            diff_zone_afr = self.calc_diff_zone_afr(vav_status, reheat_pos, cur_sat_sp, diff_sat, zone_afr, htg_sp, clg_sp, room_temp, afr_min, afr_max, clg)
            self.estimations['diff_zone_tot_afr'] += diff_zone_afr
            new_zone_afr = zone_afr + diff_zone_afr
            
            # VAV boxes with reheat
            # update coil temp change when closed
            # and heat flow estimate
            if reheat_pos == 0:
                self.estimations['rhv_power_delta_' + vav] = np.zeros(len(diff_sat))
                self.estimations['rhv_power_' + vav] = 0
                # self.ts_data += [0, 0, 0] # log
                
                # ### for debugging and tracking purposes only
                # if self.rhv_coils_hist['rhv_coils_hist_'+vav] > 0:
                #     self.estimations['rhv_clo_temp_chg_' + vav] = ((zone_dat - self.cur_sat)*0.01) + (0.99*self.estimations['rhv_clo_temp_chg_' + vav])
                # self.rhv_coils_hist['rhv_coils_hist_'+vav] += 1
                
            else:
                self.estimations['rhv_power_delta_' + vav] = self.calc_heat_flow(new_zone_afr, -diff_sat)
                
                # check HW supply using pump data
                if not any(x > 0 for x in self.hw_pumps_power):
                    self.estimations['rhv_power_delta_' + vav] = np.zeros(len(diff_sat))
                    
                self.estimations['rhv_power_delta'] += self.estimations['rhv_power_delta_' + vav]

            # ΔPrh_lower, 0, ΔPrh_higher = self.estimations['rhv_power_delta_' + vav]
            # print(f"ΔPrh_lower {vav}: {self.estimations['rhv_power_delta_' + vav][0]}")
            # print(f"ΔPrh_higher {vav}: {self.estimations['rhv_power_delta_' + vav][-1]}")
            
            #     ### for debugging and tracking purposes only
            #     self.rhv_coils_hist['rhv_coils_hist_'+vav] = 0
            #     delta_T = zone_dat - self.estimations['rhv_clo_temp_chg_' + vav] - (cur_sat_sp + diff_sat)
            #     diff_rhv_power = self.calc_heat_flow(new_zone_afr, delta_T)
            #     self.ts_data += np.concatenate([arr.flatten() for arr in diff_rhv_power]).tolist() # log                
            # self.ts_header += [vav+' rhv power for lo SAT (BTU/h)', vav+' rhv power for cur SAT (BTU/h)', vav+' rhv power for hi SAT (BTU/h)', ] # log
        
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
        
        self.estimations['fan_power_delta'] += fan_power_delta
        
        # Chilled water temp change and power for each AHU under different SAT setpoints
        # estimate the inherent temperature change between in & out temperature    
        if self.ccv == 0: 
            print('Cooling Coil Closed. Reset Cooling Power to 0')
            # valve closed during look-back window
            if self.hcv == 0 and self.chw_coils_hist > 0:
                # update coil closed temp change and return heat flow estimate of zero
                
                # k-value for ΔTc calculation : 0.01
                # ΔTc : {self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name]
                self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name] = ((self.cur_sat - self.mat)*0.01) + (0.99*self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name])        
                # update trend/hist values
                self.chw_coils_hist += 1
                
            self.estimations['chw_power_delta'] = np.zeros(len(diff_sat))
            self.ts_data += [0, 0, 0] # log 
        
        elif self.ccv == np.nan and (not any(x > 0 for x in self.cw_pumps_power)): 
            print('Cooling Coil Value is NaN and all Chilled Water Pump Power are 0. Reset Cooling Power to 0')
            # valve closed during look-back window
            if self.hcv == 0 and self.chw_coils_hist > 0:                
                # k-value for ΔTc calculation : 0.01
                # ΔTc : {self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name]
                self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name] = ((self.cur_sat - self.mat)*0.01) + (0.99*self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name])        
                # update trend/hist values
                self.chw_coils_hist += 1
                
            self.estimations['chw_power_delta'] = np.zeros(len(diff_sat))
            self.ts_data += [0, 0, 0] # log 
            
        else:
            # return heat flow estimate for each candidate sat
            # include predicted change in total airflow at each sat       
            # cur temp difference based on cur sat
            
            # ΔTc : self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name]
            curr_ahu_temp = cur_sat_sp - self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name] - self.mat
            curr_chw_power = np.maximum(0.0, -self.calc_heat_flow(afr, curr_ahu_temp))
            
            diff_ahu_temp = cur_sat_sp + diff_sat - self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name] - self.mat
            
            # clg coil power
            diff_chw_power = np.maximum(0.0, -self.calc_heat_flow(afr + diff_afr, diff_ahu_temp))           
            self.ts_data += np.concatenate([arr.flatten() for arr in diff_chw_power]).tolist() # log 
            
            # update trend/hist values
            self.chw_coils_hist = 0
            self.estimations['chw_power_delta'] = diff_chw_power - curr_chw_power
            
        self.ts_header += [' chw power for lo SAT (BTU/h)', ' chw power for cur SAT (BTU/h)', ' chw power for hi SAT (BTU/h)', ] # log
        self.estimations['diff_sat'] = diff_sat
        
        # print(f"k-value for ΔTc calculation:{0.01}")
        # print(f"ΔTc : {self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name]}")
        
    def estimate_power_G36(self, cur_sat_sp, diff_sat):
        # difference from estimate_power: not updating the hist vars
        num = len(diff_sat)
        self.estimations['chw_power_delta_G36']   = np.zeros(num)
        self.estimations['rhv_power_delta_G36']   = np.zeros(num)
        self.estimations['fan_power_delta_G36']   = np.zeros(num)
        self.estimations['diff_zone_tot_afr_G36'] = np.zeros(num)
                
        # init total zone airflow rate (afr)
        afr = 0
        
        # loop through each zone vav box
        for vav in self.vavs:
            div_ID = self.zone_dev_map[vav]
            
            # from AI_XXXX.csv
            zone_csv_AI = os.path.join(self.folder_dir, f'AI_{div_ID}.csv')     
            zone_data_AI = np.genfromtxt(zone_csv_AI, delimiter=',', dtype=None, names=True, encoding='utf-8')
            # discharge air temperature
            if any(np.char.find(zone_data_AI['Object_Name'], 'Supply Air Temperature') >= 0) :
                zone_dat = zone_data_AI['Present_Value'][np.char.find(zone_data_AI['Object_Name'], 'Supply Air Temperature') >= 0][0]
                if zone_dat < 0:
                    zone_dat = self.cur_sat
            else:
                zone_dat = self.cur_sat
            
            # airflow
            zone_afr = zone_data_AI['Present_Value'][np.char.find(zone_data_AI['Object_Name'], 'Airflow') >= 0][0]
            # total zone afr update
            afr += zone_afr       
            # from AV_XXXX.csv
            zone_csv_AV = os.path.join(self.folder_dir, f'AV_{div_ID}.csv')
            zone_data_AV = np.genfromtxt(zone_csv_AV, delimiter=',', dtype=None, names=True, encoding='utf-8')  
            # min airflow
            afr_min = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], self.flow_min)>= 0][0]
            # max airflow
            afr_max = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], self.flow_max) >= 0][0]      
            # cooling loop 
            clg = (zone_afr - afr_min)/(afr_max - afr_min) * 100
            # heating setpoint
            htg_sp = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'Heating Setpoint') >= 0][0]           
            # cooling setpoint
            clg_sp = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'Cooling Setpoint') >= 0][0]             
            # room temp
            room_temp = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'Space Temperature') >= 0][0]        
            # reheat
            reheat_pos = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'Reheat Valve Position') >= 0][0]
            # calculate AFR difference under different SAT setpoints
            vav_status = zone_data_AV['Present_Value'][np.char.find(zone_data_AV['Object_Name'], 'VAV Status Value') >= 0][0]
            diff_zone_afr = self.calc_diff_zone_afr(vav_status, reheat_pos, cur_sat_sp, diff_sat, zone_afr, htg_sp, clg_sp, room_temp, afr_min, afr_max, clg)
            self.estimations['diff_zone_tot_afr_G36'] += diff_zone_afr
            new_zone_afr = zone_afr + diff_zone_afr
            
            # VAV boxes with reheat
            if reheat_pos == 0:
                self.estimations['rhv_power_delta_G36'] += np.zeros(len(diff_sat))                
            else:
                self.estimations['rhv_power_delta_G36'] += self.calc_heat_flow(new_zone_afr, -diff_sat)
        
        diff_afr = self.estimations['diff_zone_tot_afr_G36']
        afr_ratio = (afr + diff_afr)/afr
        
        ### fan power based on vfd percent out and motor rating
        cur_power = self.vfd_sf_power + self.vfd_rf_power
        diff_fan_power = cur_power * (afr_ratio ** 2.5) # fan laws
        
        self.ts_data += np.concatenate([arr.flatten() for arr in diff_fan_power]).tolist() # log 
        self.ts_header += ['fan power for lo G36 SAT ', 'fan power for cur G36 SAT', ' fan power for hi G36 SAT', ] # log
    
        fan_power_delta = diff_fan_power - cur_power
        self.estimations['fan_power_delta_G36'] += fan_power_delta
            
        # Chilled water temp change and power for each AHU under different SAT setpoints
        if (self.ccv == 0) and (self.hcv == 0): 
            # valve closed during look-back window
            self.estimations['chw_power_delta_G36'] = np.zeros(len(diff_sat))
            self.ts_data += [0, 0, 0]
        else:
            # return heat flow estimate for each candidate sat
            curr_ahu_temp = cur_sat_sp - self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name] - self.mat
            curr_chw_power = np.maximum(0.0, -self.calc_heat_flow(afr, curr_ahu_temp))
            diff_ahu_temp = cur_sat_sp + diff_sat - self.estimations['clg_coil_clo_temp_chg_' + self.ahu_name] - self.mat
            
            # clg coil power
            diff_chw_power = np.maximum(0.0, -self.calc_heat_flow(afr + diff_afr, diff_ahu_temp))           
            self.ts_data += np.concatenate([arr.flatten() for arr in diff_chw_power]).tolist() # log 
            
            # update trend/hist values
            self.chw_coils_hist = 0
            self.estimations['chw_power_delta_G36'] = diff_chw_power - curr_chw_power
        
        self.ts_header += [' chw power for lo G36 SAT (BTU/h)', ' chw power for cur G36 SAT (BTU/h)', ' chw power for hi G36SAT (BTU/h)', ] # log
    
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
        # CFM * delta_fahrenheit * 1.08
        return volumetric_flow * delta_temperature * 1.08  # [Unit: BTU/hr]
    
    # get new air flow rate for different SATs
    def calc_diff_zone_afr(self, vav_status, reheat_pos, cur_sat, diff_sat, afr, htg_sp, clg_sp, room_temp, afr_min, afr_max, clg):
        
        
        # rely on VAV box state value from controller to determine VAV box state if present
        if vav_status in [1,2,3]: # 1-deadband, 2-cooling, 3-heating
            # Non-cooling zones or minimum-flow zones
            if (vav_status in [1,2]):
                diff_zone_afr = np.zeros(len(diff_sat))

            # Cooling zones
            else:
                afr = np.minimum(np.maximum(afr, afr_min), afr_max)

                new_zone_afr = []
                for x in diff_sat:
                    denom = (clg_sp - (cur_sat + x) - 2)
                    if denom == 0:
                        value = afr
                    else:
                        value = afr * (clg_sp - cur_sat - 2) / denom
                    new_zone_afr.append(value)

                new_zone_afr = np.minimum(np.maximum(new_zone_afr, afr_min), afr_max)

                if 0.1 < clg < 99.9:
                    diff_zone_afr = new_zone_afr - afr
                else:
                    diff_zone_afr = np.minimum(afr, new_zone_afr) - afr

        else:
            # If vav box state variable does not match one of three expected states,
            # estimate state based on reheat valve position and airflow
            ## heating or deadband 
            if (reheat_pos > 20) or (clg < 0.1):
                diff_zone_afr = np.zeros(len(diff_sat))

            # cooling 
            else:
                afr = np.minimum(np.maximum(afr, afr_min), afr_max)

                new_zone_afr = []
                for x in diff_sat:
                    denom = (clg_sp - (cur_sat + x) - 2)
                    if denom == 0:
                        value = afr * (clg_sp - cur_sat - 1.99) / (clg_sp - (cur_sat + x) - 1.99)
                    else:
                        value = afr * (clg_sp - cur_sat - 2) / denom
                    new_zone_afr.append(value)

                new_zone_afr = np.minimum(np.maximum(new_zone_afr, afr_min), afr_max)

                if 0.1 < clg < 99.9:
                    diff_zone_afr = new_zone_afr - afr
                else:
                    if room_temp > clg_sp:
                        diff_zone_afr = np.zeros(len(diff_sat))
                    else:
                        diff_zone_afr = np.minimum(afr, new_zone_afr) - afr

        if np.any(np.isnan(diff_zone_afr)):
            print('issue encountered in calc_diff_zone_afr()')
            print('diff_zone_afr:%s' % diff_zone_afr)
            print(
                'cur_sat=%s, diff_sat=%s, afr=%s, vav_status=%s, '
                'room_temp=%s, htg_sp=%s, clg_sp=%s, afr_min=%s, afr_max=%s, clg=%s'
                % (cur_sat, diff_sat, afr, vav_status,
                   room_temp, htg_sp, clg_sp, afr_min, afr_max, clg)
            )
            diff_zone_afr = np.zeros(len(diff_sat))

        return diff_zone_afr
    
    # def calc_diff_zone_afr(self, reheat_pos, cur_sat, diff_sat, afr, htg_sp, clg_sp, room_temp, afr_min, afr_max, clg):      
    #     # heating or deadband
    #     # CHECK REHEAT POS RANGE/VALUE
    #     if (reheat_pos > 20) or (htg_sp <= room_temp <= clg_sp) or (clg < 0.1): ##else statement to remove the room temp condition
    #         diff_zone_afr = np.zeros(len(diff_sat))
            
    #     # cooling
    #     else:
    #         afr = np.minimum(np.maximum(afr, afr_min), afr_max)

    #         ### actual deltaT vs assumed deltaT to be checked later
    #         new_zone_afr = []
    #         for x in diff_sat:
    #             if (clg_sp - (cur_sat + x) - 2) == 0:
    #                 value = afr * (clg_sp - cur_sat - 1.99) / (clg_sp - (cur_sat + x) - 1.99)
    #             else:
    #                 value = afr * (clg_sp - cur_sat - 2) / (clg_sp - (cur_sat + x) - 2)
                    
    #             new_zone_afr.append(value)
                        
    #         new_zone_afr = np.minimum(np.maximum(new_zone_afr, afr_min), afr_max)
            
    #         if 0.1 < clg < 99.9:
    #             diff_zone_afr = new_zone_afr - afr
                
    #         else:
    #             if room_temp > clg_sp:
    #                 # zone way past capacity, afr will not change regardless of sat
    #                 diff_zone_afr = np.zeros(len(diff_sat))
    #             else:
    #                 # zone at capacity, afr can only decrease, no further increase possible
    #                 diff_zone_afr = np.minimum(afr, new_zone_afr) - afr
            
    #     if np.any(np.isnan(diff_zone_afr)):
    #         print('issue encountered in calc_diff_zone_afr()')
    #         print('new_zone_afr:%s'%new_zone_afr)
    #         print('diff_zone_afr:%s'%diff_zone_afr)
    #         print('cur_sat=%s, diff_sat=%s, afr=%s, cur_clg_sp=%s, room_temp=%s, afr_min=%s, afr_max=%s, clg=%s'%(cur_sat, diff_sat, afr, clg_sp, room_temp, afr_min, afr_max, clg))
    #         diff_zone_afr = np.zeros(len(diff_sat))
        
    #     return diff_zone_afr
    
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
        # calculate the sat sp 
        if current_oat <=lo_oat:        
            rv = val_at_lo_oat
        elif current_oat >= hi_oat:
            rv = val_at_hi_oat
        else:
            # linearly interpolate
            val_range = val_at_hi_oat-val_at_lo_oat
            oat_range = hi_oat - lo_oat
            rv = val_at_lo_oat + val_range * (current_oat-lo_oat)/ oat_range
            
        return rv
