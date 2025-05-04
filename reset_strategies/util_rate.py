from datetime import datetime, timedelta

def electricity_price(datetime_obj):
    co2_cost = 267  # 267 $/ton CO2
    co2_elec_cost = (289/907185) * co2_cost  # 289g CO2e/kWh for electricity, 1 ton=907185g
    month_rate = {1: {2025:0.081+co2_elec_cost,},  2: {2025:0.066+co2_elec_cost,},  3: {2025:0.074+co2_elec_cost,},
                  4: {2025:0.069+co2_elec_cost,},  5: {2025:0.074+co2_elec_cost,},  6: {2025:0.119+co2_elec_cost,},
                  7: {2025:0.127+co2_elec_cost,},  8: {2025:0.124+co2_elec_cost,},  9: {2025:0.136+co2_elec_cost,},
                 10: {2025:0.106+co2_elec_cost,}, 11: {2025:0.075+co2_elec_cost,}, 12: {2025:1.013+co2_elec_cost,},
                 }
     
    dt = datetime_obj
    energy_charge = month_rate[dt.month][dt.year]
    
    return energy_charge

def steam_price(datetime_obj):
    ult_steam = 51.972/1000  # $/lb
    co2_cost = 267  # 267 $/ton CO2
    co2_steam_cost = (53.6/1000) /907.185 * co2_cost  # 53.6 kg CO2e/mlbs for steam
    
    month_rate = {1: {2025: ult_steam+co2_steam_cost,},  2: {2025: ult_steam+co2_steam_cost,},  3: {2025: ult_steam+co2_steam_cost,},
                  4: {2025: ult_steam+co2_steam_cost,},  5: {2025: ult_steam+co2_steam_cost,},  6: {2025: ult_steam+co2_steam_cost,},
                  7: {2025: ult_steam+co2_steam_cost,},  8: {2025: ult_steam+co2_steam_cost,},  9: {2025: ult_steam+co2_steam_cost,},
                 10: {2025: ult_steam+co2_steam_cost,}, 11: {2025: ult_steam+co2_steam_cost,}, 12: {2025: ult_steam+co2_steam_cost,},
                 }
     
    dt = datetime_obj
    energy_charge = month_rate[dt.month][dt.year]
    
    return energy_charge


if __name__=='__main__':
    dt = datetime.now()
    elec_pr = electricity_price(dt)
    steam_pr = steam_price(dt)
    
    print ("""
          The electricity cost now is: $%f
          """%(elec_pr))
          
    print ("""
          The steam cost now is: $%f
          """%(steam_pr))
