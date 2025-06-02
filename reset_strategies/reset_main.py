if __name__=='__main__':
    import os, sys
    import time
    from datetime import datetime, date
    import pdb 
    # set the working directory to be where this script is located
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    os.chdir(script_dir)
    
    ###
    ## load custom modules
    ###
    import reset
    import zone_requests
    from g36 import G36
    from core_v1 import CORE
    from email_utils import send_email
    
    ###
    ## loading the mapping dictionary (processed) data
    ###
    from mapping_data import *
    from rand_dates import *
    
    folder_dir = os.path.abspath(os.path.join(script_dir, "..", 'bacnet_csvs_test2'))
    core_version = 'v1'
    max_off_time = 1
    
    # trim and respond logic params
    # AHU5:26 zones, AHU6:44 zones, AHU7: 58 zones
    # ignored cooling requests
    num_ignore_clg_ahu5, num_ignore_clg_ahu6, num_ignore_clg_ahu7 = 26*3/10, 41*3/10, 58*3/10
    # ignored heating requests
    num_ignore_htg_ahu5, num_ignore_htg_ahu6, num_ignore_htg_ahu7 = 26*3/10, 41*3/10, 58*3/10
    
    sp_default = 58 # default setpoint if control algo doesn't work
    sp_trim = 0.2
    sp_res  = -0.3
    sp_res_max = -1.0
    sat_min = 55
    sat_max = 65
                
    # pick algorithm
    if date.today() in rand_dates_Baseline:
        algo = 0 # baseline
    elif date.today() in rand_dates_G36:
        algo = 1 # G36
    elif date.today() in rand_dates_CORE:
        algo = 2 # CORE
    else:
        raise ValueError("Today is not in any of the rand rates")
    
    # zone list (zones_5, zones_6, zones_7) extracted by extract_dev_ID.py
    zones_and_ahus = [(zones_5, 'AHU_5', num_ignore_clg_ahu5, num_ignore_htg_ahu5), (zones_6, 'AHU_6', num_ignore_clg_ahu6, num_ignore_htg_ahu6), (zones_7, 'AHU_7', num_ignore_clg_ahu7, num_ignore_htg_ahu7)]
    
    # alert emails
    email_list = ['TJayarathne@trccompanies.com', 'yan.wang@berkeley.edu', 'jbursill@deltacontrols.com']
        
    for zones, ahu, num_ignore_clg, num_ignore_htg in zones_and_ahus:    
        try:
            # instantiate temp requests objects
            clg_requests = zone_requests.Clg_Request(verbose=False, folder_dir=folder_dir, zone_dev_map=devID_zoneID, zone_names=zones,                                                 
                                                    flow='Airflow', flow_min='Minimum Airflow Setpoint', flow_max='Maximum Airflow Setpoint', 
                                                    clg_setpoint='Cooling Setpoint', htg_setpoint='Heating Setpoint', room_temp='Space Temperature', 
                                                    low_temp_cutoff = 72.0, high_temp_cutoff = 75.0)
            
            htg_requests = zone_requests.Htg_Request(verbose=False, folder_dir=folder_dir, zone_dev_map=devID_zoneID, zone_names=zones, important=importance_htg_zones,                                                 
                                                    flow='Airflow', flow_min='Minimum Airflow Setpoint', flow_max='Maximum Airflow Setpoint', 
                                                    clg_setpoint='Cooling Setpoint', htg_setpoint='Heating Setpoint', room_temp='Space Temperature', 
                                                    low_temp_cutoff = 72.0, high_temp_cutoff = 75.0)
                                                            
            # instantiate the reset object
            temperature_reset = reset.Reset(SPmin=sat_min, SPmax=sat_max, num_ignore_clg=num_ignore_clg, num_ignore_htg=num_ignore_htg, SPtrim=sp_trim, SPres=sp_res, SPres_max=sp_res_max)
            # G36 and CORE calculations will run whatever the date
            # but will only overwrite the csv depending on the algo sequence number
            
            ###
            ## G36 control
            ###
            # SP limits based on oat
            sp_min_at_lo_oat = 55
            sp_max_at_lo_oat = 65
            sp_min_at_hi_oat = 55
            sp_max_at_hi_oat = 55
            lo_oat = 60
            hi_oat = 70
            
            # dehumd requests
            dehumd_limits = (55, 60, 65, 58) # lo_oa_dwpt, hi_oa_dwpt, spmax_at_lo_oat_dwpt, spmax_at_hi_oat_dwpt
            dehumid = True
            g36_control = G36(algo=algo, max_off_time=max_off_time, folder_dir=folder_dir, ahu_dev_map=devID_ahuID, zone_requests=clg_requests, reset=temperature_reset, num_ignore=num_ignore_clg, 
                              ahu_name=ahu, SP0=sp_default, SPtrim=sp_trim, SPres=sp_res, SPres_max=sp_res_max, lo_oat=lo_oat, hi_oat=hi_oat,
                              SPmin_at_lo_oat=sp_min_at_lo_oat, SPmax_at_lo_oat=sp_max_at_lo_oat, SPmin_at_hi_oat=sp_min_at_hi_oat, SPmax_at_hi_oat = sp_max_at_hi_oat,
                              )
                              
            g36_sat = g36_control.get_new_satsp_humd(55, 60, 65, 58)
            
            ###
            ## CORE control
            ###
            diff_sat = [-0.5, 0, 0.5]
            
            core_control = CORE(algo=algo, core_version=core_version, max_off_time=max_off_time, dehumid=dehumid, dehumd_limits=dehumd_limits, g36_sat=g36_sat, folder_dir=folder_dir, zone_names=zones, ahu_name=ahu,        
                                zone_dev_map=devID_zoneID, vdf_dev_map=devID_vfdID, pump_dev_map=devID_pumpID, ahu_dev_map=devID_ahuID,
                                zone_requests=(clg_requests, htg_requests), reset=temperature_reset, num_ignore_clg=num_ignore_clg, num_ignore_htg=num_ignore_htg, diff_sat=diff_sat,                   
                                )                     
            
            core_control.get_new_satsp()
            
            if algo == 0:
                print('### Baseline control used ###')
            
            # log time to a text file            
            log_dir = os.path.abspath(os.path.join(folder_dir, 'log', ahu +'_log_time.txt'))
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_dir, "w") as file:
                file.write(f"last run for {ahu}:{now}")
            
            # zone temp and SAT monitoring
            bad_zones = core_control.find_bad_zones()
            if bad_zones:
                bad_zones_comb = '\r\n'.join(bad_zones)
                print('Find issues with zone temps or SATs')
                send_email(email_list, bad_zones_comb, '[Abnormal zone temp or SAT warnings]')
                
        except Exception as e:
            print(e)
            log_dir = os.path.abspath(os.path.join(folder_dir, 'log', ahu +'_log_time.txt'))
            
            # get the last good run time
            with open(log_dir, "r") as file:
                last_time_str = file.read().split(':', 1)[-1]
                last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
                time_elapsed = (datetime.now() - last_time).total_seconds()
            
            # send warning emails if down time is over 1 hour
            if time_elapsed > 3600:
                send_email(email_list, f'ISSUES WITH CORE APP IN {ahu} OF FORDHAM BLDG', '[CORE SAT Reset Issue]')
                
    # move algo values into AV_3050090.csv
    filtered_rows  = []
    
    # filtered data from AV_3050090
    add_data = np.genfromtxt(os.path.join(folder_dir, 'AV_3050090.csv'), delimiter=',', dtype=str, encoding='utf-8')[:26]
    add_data[1:, 2] = np.arange(1, len(add_data))
    filtered_rows.append(add_data[1:])
    
    for _, value in devID_ahuID.items():
        out_csv = os.path.join(folder_dir, f'AV_{value}_out.csv')
        data = np.genfromtxt(out_csv, delimiter=',', dtype=str, encoding='utf-8')
        
        # Extract rows where the "instance" column contains '99999'
        rows = data[data[:, 2] == '9999999', :]
                        
        if rows.size > 0:
            filtered_rows.append(rows)
    
        # Combine filtered data with the header
        if filtered_rows:
            header = ('device','object-type','instance', 'Object_Name', 'Present_Value', 'Units')          
            filtered_data = np.vstack([header] + filtered_rows)        
            filtered_data[len(add_data):, 2] = np.arange(10001, 10001 + len(filtered_data) - len(add_data))
            filtered_data[:, -1] = ''
            
            # Save to a new CSV file
            output_path =  os.path.join(folder_dir, 'AV_3050090_out.csv')
            np.savetxt(output_path, filtered_data, delimiter=",", fmt="%s")
        
        else:
            print("No matching rows found")
        
