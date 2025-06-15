import os, csv, sys, glob
from datetime import datetime
import numpy as np
import time
# import zone_requests, reset

class G36:
    def __init__(self, algo=None, max_off_time=None, folder_dir=None, oat_name=None, oarh_name=None, zone_requests=None, reset=None, ahu_dev_map=None, 
                 num_ignore=None, important=None, ahu_name=None, SP0=None, SPtrim=None, SPres=None, SPres_max=None, 
                 lo_oat=None, hi_oat=None, SPmin_at_lo_oat=None, SPmax_at_lo_oat=None, SPmin_at_hi_oat=None, SPmax_at_hi_oat=None, 
                 ):
        self.algo = algo
        self.max_off_time = max_off_time
        self.folder_dir = folder_dir
        self.ahu_name = ahu_name
        self.SPmin_at_lo_oat = SPmin_at_lo_oat
        self.SPmax_at_lo_oat = SPmax_at_lo_oat
        self.SPmin_at_hi_oat = SPmin_at_hi_oat
        self.SPmax_at_hi_oat = SPmax_at_hi_oat
        # self.SP0 = SP0 # default setpoint if control algo doesn't work
        self.lo_oat = lo_oat
        self.hi_oat = hi_oat
        self.clg_requests = zone_requests
        self.reset = reset # reset is an instantiated reset object
        self.num_ignore = num_ignore
        self.SPtrim = SPtrim
        self.SPres = SPres
        self.SPres_max = SPres_max
        self.important = important
        
        # get AHU data from AV_XX.csv
        ahu_div_ID = ahu_dev_map[ahu_name]
        self.ahu_div_ID = ahu_div_ID
        ahu_csv_AV = os.path.join(folder_dir, f'AV_{ahu_div_ID}.csv')
        ahu_data_AV = np.genfromtxt(ahu_csv_AV, delimiter=',', dtype=None, names=True, encoding='utf-8')
        self.ahu_data_AV = ahu_data_AV
        self.ahu_data_AV_header = ahu_data_AV.dtype.names
    
        # current sat setpoint
        self.cur_sat = ahu_data_AV['Present_Value'][np.char.find(ahu_data_AV['Object_Name'], 'Supply Air Setpoint') >= 0][0]
        
        # current oat
        self.current_oat = ahu_data_AV['Present_Value'][np.char.find(ahu_data_AV['Object_Name'], 'Outside Air Temperature') >= 0][0]
        
        # outdoor RH
        self.current_oarh = ahu_data_AV['Present_Value'][np.char.find(ahu_data_AV['Object_Name'], 'Outside Air Humidity') >= 0][0]
      
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
                    
        last_G36_row = None
        with open(lastest_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['g36 finished'] != '-1':
                    last_G36_row = row

        # G36
        last_G36_SAT = last_G36_row['G36 satsp ' + self.ahu_name]
        last_G36_time = last_G36_row['TimeStamp']
        dt_G36 = datetime.strptime(last_G36_time, '%Y-%m-%d %H:%M')
        time_G36_lapesd = (now - dt_G36).total_seconds()/3600
        
        return last_G36_SAT, time_G36_lapesd  
    
    def get_new_satsp(self):
        try:
            self.clg_requests.update()
            # update setpoint temp limits based on outside air temperature        
            # calculate the new supply air temp setpoint with the new setpoint limits
            
            # min SAT setpoint
            self.reset.SPmin = self.calc_sp_limit(self.current_oat, self.lo_oat, self.hi_oat, self.SPmin_at_lo_oat, self.SPmin_at_hi_oat)                            
            
            # max SAT setpoint        
            self.reset.SPmax = self.calc_sp_limit(self.current_oat, self.lo_oat, self.hi_oat, self.SPmax_at_lo_oat, self.SPmax_at_hi_oat)

            # use trim and respond without outside air based SAT setpoint limits
            new_sp = self.reset.get_new_sp_clg(self.clg_requests.R_clg , self.cur_sat)

        except Exception as e:      
            if self.algo == 1:
                print(e)
                
            try: 
                last_G36_SAT, time_G36_lapesd = self.get_last_good_SAT()
                if time_G36_lapesd < self.max_off_time:
                    new_sp = last_G36_SAT
                    
                    if self.algo == 1:
                        print('******* G36 failed to run, and the last good SAT value was used *******')
                else:
                    if self.algo == 1:
                        print('******* G36 failed to run for more than an hour *******')  
                    # default to the baseline control
                    new_sp = np.nan
                
            except Exception as e:
                if self.algo == 1:
                    print(e)
                    print('******* G36 failed to run, and no good SAT value can be found *******') 
                # default to the baseline control
                new_sp = np.nan
                    
        return new_sp
    
    def get_new_satsp_humd(self, lo_oa_dwpt, hi_oa_dwpt, spmax_at_lo_oat_dwpt, spmax_at_hi_oat_dwpt):
        try:
            self.clg_requests.update()
            # update setpoint temp limits based on outside air temperature
            # min SAT setpoint
            self.reset.SPmin = self.calc_sp_limit(self.current_oat, self.lo_oat, self.hi_oat, self.SPmin_at_lo_oat, self.SPmin_at_hi_oat)                                    
            
            # max SAT setpoint
            reset_SPmax = self.calc_sp_limit(self.current_oat, self.lo_oat, self.hi_oat, self.SPmax_at_lo_oat, self.SPmax_at_hi_oat)                           
            oa_dpwt = self.cal_dew_point_temperature(self.current_oat, self.current_oarh)
            humd_SPmax = self.calc_sp_limit(oa_dpwt, lo_oa_dwpt, hi_oa_dwpt, spmax_at_lo_oat_dwpt, spmax_at_hi_oat_dwpt)              
            
            # if dehumidification requires a step-change of over 0.5F
            humd_SPmax_adjust = max(self.cur_sat - 0.5, humd_SPmax)
            
            self.reset.SPmax = min(reset_SPmax, humd_SPmax_adjust)
            
            # use trim and respond without outside air based SAT setpoint limits
            new_sp = self.reset.get_new_sp_clg(self.clg_requests.R_clg , self.cur_sat)

        except Exception as e:
            print(e)            
            try: 
                last_G36_SAT, time_G36_lapesd = self.get_last_good_SAT()
                
                if time_G36_lapesd < self.max_off_time:
                    new_sp = last_G36_SAT
                    print('******* G36 failed to run, and the last good SAT value was used *******')
                else:
                    print('******* G36 failed to run for more than an hour *******')
                    # defalt to the baseline control
                    new_sp = np.nan
                
            except Exception as e:
                print(e)
                print('******* G36 failed to run, and no good SAT value can be found *******')
                # defalt to the baseline control
                new_sp = np.nan
        
        return new_sp

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
  
    def save_data_bydate(self, data2save, header, folder_dir, ahu_name):
        # get the current date to name the file
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = os.path.join(self.folder_dir, 'log', self.ahu_name, f"G36_{self.ahu_name}_{date_str}.csv" )
        
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
                            
    def log_data(self, newdata, ahu_data_AV, new_ahu_data_AV):
        var_in_csv = newdata[3]
        if not any(var_in_csv in item for item in ahu_data_AV['Object_Name']):
            new_nparry = np.array([newdata], dtype=new_ahu_data_AV.dtype)                                                         
            new_ahu_data_AV = np.append(new_ahu_data_AV, new_nparry)
            
        else:
            idx_find = [np.char.find(ahu_data_AV['Object_Name'], var_in_csv)>=0][0]
            new_ahu_data_AV['Present_Value'][idx_find] = newdata[-2]
        
        return new_ahu_data_AV
