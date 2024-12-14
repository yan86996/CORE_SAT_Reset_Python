if __name__=='__main__':
    import os, sys
    import time
    from datetime import datetime, date
    # set the working directory to be where this script is located
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    os.chdir(script_dir)
    
    # load custom modules
    import reset
    import zone_requests
    from g36 import G36
    from core_v0 import CORE
    # loading the mapping dictionary from the file
    from mapping_data import *
    from rand_dates import *
    
    # initialization
    folder_dir = os.path.abspath(os.path.join(script_dir, "..", 'bacnet_csvs_test1'))
    zones_5, zones_6, zones_7 = ['3-3', '3-4', '3-5'], ['3-22', '3-23', '3-24'], ['3-1', '3-2', '3-8', '3-9', '3-10']
    ahu_5, ahu_6, ahu_7 = 'AHU_5', 'AHU_6', 'AHU_7'
    zones_and_ahus = [(zones_5, ahu_5), (zones_6, ahu_6), (zones_7, ahu_7)]

    damper = 'Damper Position'
    flow = 'Airflow'
    flow_min = 'Minimum Airflow Setpoint'
    flow_max = 'Maximum Airflow Setpoint'
    room_temp = 'Space Temperature'
    clg_setpoint = 'Cooling Setpoint'
    core_version = 'v0'

    # trim and response rates (F)
    num_ignore = 2
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

    
    for zones, ahu in [(zones_5, ahu_5)]:
        # instantiate temp requests objects
        temperature_requests = zone_requests.Temperature(verbose=False, folder_dir = folder_dir, zone_dev_map = devID_zoneID, zone_names=zones,                                                 
                                                         flow=flow, flow_min=flow_min, flow_max=flow_max, clg_setpoint=clg_setpoint,
                                                         room_temp=room_temp, low_temp_cutoff = 72.0, high_temp_cutoff = 75.0)
                                                        
        # instantiate the reset object
        temperature_reset = reset.Reset(SPmin=sat_min, SPmax=sat_max, num_ignore=num_ignore, SPtrim=sp_trim, SPres=sp_res, SPres_max=sp_res_max)

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
        
        g36_control = G36(algo=algo, folder_dir=folder_dir, ahu_dev_map=devID_ahuID, zone_requests=temperature_requests, reset=temperature_reset, num_ignore=num_ignore, 
                          ahu_name=ahu, SP0=sp_default, SPtrim=sp_trim, SPres=sp_res, SPres_max=sp_res_max, lo_oat=lo_oat, hi_oat=hi_oat,
                          SPmin_at_lo_oat=sp_min_at_lo_oat, SPmax_at_lo_oat=sp_max_at_lo_oat, SPmin_at_hi_oat=sp_min_at_hi_oat, SPmax_at_hi_oat = sp_max_at_hi_oat,
                          )
                          
        g36_sat = g36_control.get_new_satsp()
        # g36_sat = g36_control.get_new_satsp_humd(55, 60, 65, 58)
        
        ###    
        ## CORE control
        ###
        diff_sat = [-0.5, 0, 0.5]
        # lo_oa_dwpt, hi_oa_dwpt, spmax_at_lo_oat_dwpt, spmax_at_hi_oat_dwpt
        dehumd_limits = (55, 60, 65, 58)
        dehumid = True
        
        core_control = CORE(algo=algo, core_version=core_version, dehumid=dehumid, dehumd_limits=dehumd_limits, g36_sat=g36_sat, 
                            folder_dir=folder_dir, zone_names=zones,  ahu_name=ahu, zone_dev_map=devID_zoneID, vdf_dev_map=devID_vfdID,
                            flow=flow, flow_min=flow_min, flow_max=flow_max, zone_requests=temperature_requests, reset=temperature_reset, 
                            ahu_dev_map=devID_ahuID, num_ignore=num_ignore, diff_sat=diff_sat, SP0=sp_default, SPtrim=sp_trim, SPres=sp_res, SPres_max=sp_res_max,                    
                            )
      
        core_sat = core_control.get_new_satsp()
        
